import os

from flask import Flask, jsonify, request

from .providers import PROVIDERS
from .services.comparison import InvalidRoute, compare_rides
from .providers.demo import DEMO_RIDES
from .providers.links import booking_for
from .services.estimates import estimate_rides, parse_metrics
from .services.routing import osm_route_metrics


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
        return jsonify({"status": "ok", "fare_mode": "demo"})

    @app.get("/api/providers")
    def providers():
        return jsonify({"providers": PROVIDERS, "fare_mode": "demo"})

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
        if (metrics is None and isinstance(pickup_text, str) and isinstance(destination_text, str)
                and pickup_text.strip() and destination_text.strip()
                and pickup_text.strip().casefold() != destination_text.strip().casefold()):
            found = osm_route_metrics(pickup_text.strip(), pickup_coords, destination_text.strip(), destination_coords)
            if found:
                metrics = found["metrics"]
                pickup_coords = pickup_coords or found["pickup"]
                destination_coords = destination_coords or found["destination"]
        try:
            result = compare_rides(
                payload.get("pickup"),
                payload.get("destination"),
                estimate_rides(metrics) if metrics else DEMO_RIDES,
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
            booking = booking_for(ride["provider"], link_route)
            ride["booking"] = booking
            ride["booking_url"] = booking["url"] if booking else None
        if metrics:
            result["notice"] = "Estimated fares from route distance and approximate rate cards. The final fare is shown in the provider app."
        else:
            result["notice"] = "Demo fares only. No live provider prices or availability are connected."
        result["route_metrics"] = metrics
        return jsonify(result)

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "Request body is too large."}), 413

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)