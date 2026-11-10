import os

from flask import Flask, jsonify, request

from .providers import PROVIDERS
from .services.comparison import InvalidRoute, compare_rides
from .providers.links import booking_for
from .services.estimates import parse_metrics
from .services.routing import osm_route_metrics, osm_route_points, place_suggestions


def parse_coords(value):
    """Return {'lat','lng'} from a request value, None if absent, ValueError if invalid."""
    if value is None:
        return None
    try:
        lat, lng = float(value["lat"]), float(value["lng"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Coordinates must look like {\"lat\": 12.97, \"lng\": 77.59}.")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("Coordinates are out of range.")
    return {"lat": lat, "lng": lng}


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    frontend_origins = {
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    }

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin in frontend_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "fare_mode": "unavailable"})

    @app.get("/api/providers")
    def providers():
        return jsonify({"providers": PROVIDERS, "fare_mode": "unavailable"})

    @app.get("/api/routes/popular")
    def popular_routes():
        return jsonify({
            "routes": [
                {"pickup": "Indiranagar, Bengaluru", "destination": "MG Road, Bengaluru"},
                {"pickup": "Bandra, Mumbai", "destination": "Lower Parel, Mumbai"},
                {"pickup": "Connaught Place, Delhi", "destination": "Hauz Khas, Delhi"},
            ],
            "source": "demo",
        })

    @app.get("/api/places/search")
    def search_places():
        query = request.args.get("q", "").strip()
        if len(query) < 3 or len(query) > 160:
            return jsonify({"error": "Search text must be between 3 and 160 characters."}), 400
        has_near_lat = "near_lat" in request.args
        has_near_lng = "near_lng" in request.args
        if has_near_lat != has_near_lng:
            return jsonify({"error": "Nearby search requires both coordinates."}), 400
        try:
            near = parse_coords({
                "lat": request.args["near_lat"],
                "lng": request.args["near_lng"],
            }) if has_near_lat else None
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        try:
            return jsonify({"places": place_suggestions(query, near=near)})
        except (OSError, ValueError, KeyError, TypeError):
            return jsonify({"error": "Place suggestions are temporarily unavailable."}), 502

    @app.post("/api/rides/compare")
    def compare():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Send pickup and destination as JSON."}), 400
        try:
            metrics = parse_metrics(payload.get("route_metrics"))
            pickup_coords = parse_coords(payload.get("pickup_coords"))
            destination_coords = parse_coords(payload.get("destination_coords"))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        pickup_text, destination_text = payload.get("pickup"), payload.get("destination")
        if (isinstance(pickup_text, str) and isinstance(destination_text, str)
                and pickup_text.strip() and destination_text.strip()
                and pickup_text.strip().casefold() != destination_text.strip().casefold()):
            if metrics is None:
                found = osm_route_metrics(pickup_text.strip(), pickup_coords, destination_text.strip(), destination_coords)
                if found:
                    metrics = found["metrics"]
                    pickup_coords = pickup_coords or found["pickup"]
                    destination_coords = destination_coords or found["destination"]
            elif pickup_coords is None or destination_coords is None:
                points = osm_route_points(pickup_text.strip(), pickup_coords, destination_text.strip(), destination_coords)
                if points:
                    pickup_coords = pickup_coords or points["pickup"]
                    destination_coords = destination_coords or points["destination"]
        try:
            result = compare_rides(
                payload.get("pickup"),
                payload.get("destination"),
                [
                    {
                        "id": f"{provider['id']}-{payload.get('category', 'all')}-unavailable",
                        "provider": provider["name"],
                        "ride_type": payload.get("category", "all")
                        if payload.get("category", "all") != "all"
                        else "unavailable",
                        "requested_category": payload.get("category")
                        if payload.get("category", "all") != "all"
                        else None,
                        "vehicle_category": None,
                        "fare": None,
                        "fare_low": None,
                        "fare_high": None,
                        "currency": "INR",
                        "fare_status": "UNAVAILABLE",
                        "fare_classification": "UNAVAILABLE",
                        "fare_message": (
                            "Live fare currently unavailable. Open the provider to check the current price."
                        ),
                        "pickup_eta_minutes": None,
                        "trip_duration_minutes": None,
                        "distance_km": None,
                        "availability_status": "unknown",
                    }
                    for provider in PROVIDERS
                ],
                category=payload.get("category", "all"),
                sort=payload.get("sort", "cheapest"),
            )
        except InvalidRoute as error:
            return jsonify({"error": str(error)}), 400
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        link_route = {
            "pickup": {"text": result["route"]["pickup"], **(pickup_coords or {})},
            "destination": {"text": result["route"]["destination"], **(destination_coords or {})},
        }
        for ride in result["rides"]:
            booking = booking_for(ride["provider"], link_route, ride["ride_type"])
            ride["booking"] = booking
            ride["booking_url"] = booking["url"] if booking else None
        result["notice"] = (
            "Live fare currently unavailable. Open the provider to check the current price."
        )
        result["route_metrics"] = metrics
        return jsonify(result)

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "Request body is too large."}), 413

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)