import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from cabcompare.backend.app import create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("cabcompare.backend.app.osm_route_metrics", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        points_patcher = patch("cabcompare.backend.app.osm_route_points", return_value=None)
        points_patcher.start()
        self.addCleanup(points_patcher.stop)
        self.client = create_app().test_client()

    def test_health_reports_live_fares_unavailable(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["fare_mode"], "unavailable")

    def test_place_search_returns_openstreetmap_suggestions(self):
        suggestions = [{
            "id": "node:1", "main": "MG Road", "secondary": "Bengaluru, India",
            "text": "MG Road, Bengaluru, India", "lat": 12.9, "lng": 77.6,
        }]
        with patch("cabcompare.backend.app.place_suggestions", return_value=suggestions) as search:
            response = self.client.get("/api/places/search?q=MG%20Road&near_lat=12.9&near_lng=77.6")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["places"], suggestions)
        search.assert_called_once_with("MG Road", near={"lat": 12.9, "lng": 77.6})

    def test_place_search_rejects_short_query(self):
        response = self.client.get("/api/places/search?q=MG")
        self.assertEqual(response.status_code, 400)

    def test_place_search_requires_valid_context_coordinates(self):
        response = self.client.get("/api/places/search?q=Majestic&near_lat=12.9")
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/api/places/search?q=Majestic&near_lat=999&near_lng=77.6")
        self.assertEqual(response.status_code, 400)

    def test_compare_requires_valid_route(self):
        response = self.client.post("/api/rides/compare", json={"pickup": "", "destination": "B"})
        self.assertEqual(response.status_code, 400)

    def test_compare_never_returns_fabricated_fares(self):
        response = self.client.post("/api/rides/compare", json={"pickup": "A", "destination": "B"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["fare_source"], "UNAVAILABLE")
        self.assertEqual(len(response.json["rides"]), 4)
        self.assertTrue(all(ride["fare_status"] == "UNAVAILABLE" for ride in response.json["rides"]))
        self.assertTrue(all(ride["fare_classification"] == "UNAVAILABLE" for ride in response.json["rides"]))
        self.assertTrue(all(ride["fare"] is None for ride in response.json["rides"]))
        self.assertTrue(all(ride["availability_status"] == "unknown" for ride in response.json["rides"]))
        self.assertEqual(
            response.json["notice"],
            "Live fare currently unavailable. Open the provider to check the current price.",
        )

    def test_booking_links_are_https_on_provider_domains(self):
        response = self.client.post("/api/rides/compare", json={
            "pickup": "Indiranagar", "destination": "MG Road",
            "pickup_coords": {"lat": 12.9784, "lng": 77.6408},
            "destination_coords": {"lat": 12.9756, "lng": 77.6066},
        })
        self.assertEqual(response.status_code, 200)
        hosts = {"Uber": "m.uber.com", "Ola": "book.olacabs.com", "Rapido": "www.rapido.bike", "Namma Yatri": "nammayatri.in"}
        for ride in response.json["rides"]:
            self.assertTrue(ride["booking_url"].startswith("https://" + hosts[ride["provider"]]))
        uber = next(r for r in response.json["rides"] if r["provider"] == "Uber")
        uber_params = parse_qs(urlparse(uber["booking_url"]).query)
        self.assertEqual(urlparse(uber["booking_url"]).path, "/looking")
        self.assertEqual(json.loads(uber_params["pickup"][0]), {
            "latitude": 12.9784, "longitude": 77.6408,
            "addressLine1": "Indiranagar",
            "addressLine2": "Indiranagar",
        })
        self.assertEqual(json.loads(uber_params["drop[0]"][0]), {
            "latitude": 12.9756, "longitude": 77.6066,
            "addressLine1": "MG Road",
            "addressLine2": "MG Road",
        })
        self.assertFalse(uber["booking"]["prefilled"])
        self.assertEqual(uber["booking"]["location_transfer"], "url_generated_unverified")
        self.assertIn("UBER_CLIENT_ID is not configured", uber["booking"]["message"])
        self.assertIn("replace the names with nearby provider locations", uber["booking"]["message"])
        ola = next(r for r in response.json["rides"] if r["provider"] == "Ola")
        ola_params = parse_qs(urlparse(ola["booking_url"]).query)
        self.assertEqual(ola_params["lat"][0], "12.978400")
        self.assertEqual(ola_params["lng"][0], "77.640800")
        self.assertEqual(ola_params["drop_lat"][0], "12.975600")
        self.assertEqual(ola_params["drop_lng"][0], "77.606600")
        self.assertEqual(ola_params["pickup_name"][0], "Indiranagar")
        self.assertEqual(ola_params["drop_name"][0], "MG Road")
        self.assertTrue(ola["booking"]["prefilled"])
        self.assertEqual(ola["booking"]["location_transfer"], "web_prefill_tested_mobile_unverified")
        self.assertEqual(ola["booking"]["affiliate_attribution"], "not_configured")
        self.assertIsNone(ola["booking"]["mobile_url"])
        self.assertIn("XAPP token is not configured", ola["booking"]["message"])
        rapido = next(r for r in response.json["rides"] if r["provider"] == "Rapido")
        self.assertFalse(rapido["booking"]["prefilled"])
        self.assertFalse(rapido["booking"]["locations_in_url"])
        namma_yatri = next(r for r in response.json["rides"] if r["provider"] == "Namma Yatri")
        self.assertFalse(namma_yatri["booking"]["prefilled"])
        self.assertFalse(namma_yatri["booking"]["locations_in_url"])

    def test_booking_links_keep_typed_location_text(self):
        pickup = "  Indiranagar  100 Feet Road, Bengaluru  "
        destination = " MG Road, Bengaluru "
        response = self.client.post("/api/rides/compare", json={
            "pickup": pickup, "destination": destination,
            "pickup_coords": {"lat": 12.9784, "lng": 77.6408},
            "destination_coords": {"lat": 12.9756, "lng": 77.6066},
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["route"]["pickup"], pickup.strip())
        self.assertEqual(response.json["route"]["destination"], destination.strip())

        uber = next(r for r in response.json["rides"] if r["provider"] == "Uber")
        uber_params = parse_qs(urlparse(uber["booking_url"]).query)
        self.assertEqual(
            json.loads(uber_params["pickup"][0])["addressLine2"],
            pickup.strip(),
        )
        self.assertEqual(
            json.loads(uber_params["drop[0]"][0])["addressLine2"],
            destination.strip(),
        )
        self.assertFalse(uber["booking"]["prefilled"])
        self.assertEqual(uber["booking"]["location_transfer"], "url_generated_unverified")

        ola = next(r for r in response.json["rides"] if r["provider"] == "Ola")
        ola_params = parse_qs(urlparse(ola["booking_url"]).query)
        self.assertEqual(ola_params["pickup_name"][0], pickup.strip())
        self.assertEqual(ola_params["drop_name"][0], destination.strip())
        self.assertTrue(ola["booking"]["prefilled"])
        self.assertEqual(ola["booking"]["location_transfer"], "web_prefill_tested_mobile_unverified")

    def test_booking_links_keep_selected_coordinates_in_the_correct_direction(self):
        response = self.client.post("/api/rides/compare", json={
            "pickup": "MG Road Metro Station, Bengaluru",
            "destination": "Indiranagar Metro Station, Bengaluru",
            "pickup_coords": {"lat": 12.9756, "lng": 77.6066},
            "destination_coords": {"lat": 12.9784, "lng": 77.6408},
        })
        self.assertEqual(response.status_code, 200)
        uber = next(ride for ride in response.json["rides"] if ride["provider"] == "Uber")
        uber_params = parse_qs(urlparse(uber["booking_url"]).query)
        self.assertEqual(json.loads(uber_params["pickup"][0])["latitude"], 12.9756)
        self.assertEqual(json.loads(uber_params["pickup"][0])["longitude"], 77.6066)
        self.assertEqual(json.loads(uber_params["drop[0]"][0])["latitude"], 12.9784)
        self.assertEqual(json.loads(uber_params["drop[0]"][0])["longitude"], 77.6408)
        self.assertEqual(json.loads(uber_params["pickup"][0])["addressLine1"], "MG Road Metro Station")
        self.assertEqual(json.loads(uber_params["pickup"][0])["addressLine2"], "MG Road Metro Station, Bengaluru")
        self.assertEqual(json.loads(uber_params["drop[0]"][0])["addressLine1"], "Indiranagar Metro Station")
        self.assertEqual(json.loads(uber_params["drop[0]"][0])["addressLine2"], "Indiranagar Metro Station, Bengaluru")

        ola = next(ride for ride in response.json["rides"] if ride["provider"] == "Ola")
        ola_params = parse_qs(urlparse(ola["booking_url"]).query)
        self.assertEqual(ola_params["lat"][0], "12.975600")
        self.assertEqual(ola_params["lng"][0], "77.606600")
        self.assertEqual(ola_params["drop_lat"][0], "12.978400")
        self.assertEqual(ola_params["drop_lng"][0], "77.640800")
        self.assertEqual(ola_params["pickup_name"][0], "MG Road Metro Station, Bengaluru")
        self.assertEqual(ola_params["drop_name"][0], "Indiranagar Metro Station, Bengaluru")

    def test_ola_app_link_requires_partner_token(self):
        with patch.dict("os.environ", {"OLA_XAPP_TOKEN": "approved-partner-token"}):
            response = self.client.post("/api/rides/compare", json={
                "pickup": "Indiranagar, Bengaluru",
                "destination": "MG Road, Bengaluru",
                "pickup_coords": {"lat": 12.9784, "lng": 77.6408},
                "destination_coords": {"lat": 12.9756, "lng": 77.6066},
                "route_metrics": {"distance_km": 5, "duration_minutes": 20},
            })
        self.assertEqual(response.status_code, 200)
        ola_rides = [r for r in response.json["rides"] if r["provider"] == "Ola"]
        for ride in ola_rides:
            self.assertEqual(urlparse(ride["booking_url"]).hostname, "book.olacabs.com")
            params = parse_qs(urlparse(ride["booking_url"]).query)
            self.assertEqual(params["utm_source"][0], "approved-partner-token")
            mobile_url = urlparse(ride["booking"]["mobile_url"])
            self.assertEqual(mobile_url.hostname, "olawebcdn.com")
            self.assertEqual(mobile_url.path, "/assets/ola-universal-link.html")
            mobile_params = parse_qs(mobile_url.query)
            self.assertEqual(mobile_params["utm_source"][0], "approved-partner-token")
            self.assertEqual(mobile_params["landing_page"][0], "bk")
            self.assertEqual(mobile_params["lat"][0], "12.978400")
            self.assertEqual(mobile_params["drop_lng"][0], "77.606600")
            self.assertEqual(mobile_params["address"][0], "Indiranagar, Bengaluru")
            self.assertEqual(mobile_params["drop_address"][0], "MG Road, Bengaluru")
            self.assertTrue(ride["booking"]["prefilled"])
            self.assertEqual(ride["booking"]["location_transfer"], "web_prefill_tested_universal_link_unverified")
            self.assertEqual(ride["booking"]["affiliate_attribution"], "configured")

    def test_uber_receives_typed_pickup_without_coordinates(self):
        response = self.client.post("/api/rides/compare", json={
            "pickup": "Indiranagar Metro, Bengaluru",
            "destination": "MG Road, Bengaluru",
        })
        self.assertEqual(response.status_code, 200)
        uber = next(r for r in response.json["rides"] if r["provider"] == "Uber")
        self.assertEqual(urlparse(uber["booking_url"]).path, "/looking")
        self.assertFalse(uber["booking"]["prefilled"])

    def test_uber_client_id_is_encoded_in_the_documented_link(self):
        with patch.dict("os.environ", {"UBER_CLIENT_ID": "client id&value"}):
            response = self.client.post("/api/rides/compare", json={
                "pickup": "Pickup, Bengaluru",
                "destination": "Destination, Bengaluru",
                "pickup_coords": {"lat": 12.9, "lng": 77.6},
                "destination_coords": {"lat": 12.95, "lng": 77.65},
            })
        uber = next(r for r in response.json["rides"] if r["provider"] == "Uber")
        params = parse_qs(urlparse(uber["booking_url"]).query)
        self.assertEqual(params["client_id"], ["client id&value"])
        self.assertEqual(json.loads(params["pickup"][0])["addressLine2"], "Pickup, Bengaluru")
        self.assertEqual(uber["booking"]["location_transfer"], "url_generated_unverified")

    def test_invalid_coordinates_are_rejected(self):
        response = self.client.post("/api/rides/compare", json={
            "pickup": "A", "destination": "B", "pickup_coords": {"lat": 999, "lng": 0}})
        self.assertEqual(response.status_code, 400)

    def test_route_metrics_do_not_become_provider_fares(self):
        response = self.client.post("/api/rides/compare", json={
            "pickup": "A",
            "destination": "B",
            "route_metrics": {"distance_km": 5, "duration_minutes": 15},
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["route_metrics"], {"distance_km": 5.0, "duration_minutes": 15.0})
        self.assertTrue(all(ride["fare"] is None for ride in response.json["rides"]))
        self.assertTrue(all(ride["fare_status"] == "UNAVAILABLE" for ride in response.json["rides"]))

    def test_invalid_route_metrics_are_rejected(self):
        for bad in ({"distance_km": -1, "duration_minutes": 5}, {"distance_km": 9999, "duration_minutes": 5}, {"x": 1}):
            r = self.client.post("/api/rides/compare", json={"pickup": "A", "destination": "B", "route_metrics": bad})
            self.assertEqual(r.status_code, 400)

    def test_provider_status_is_transparent(self):
        response = self.client.get("/api/providers")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(provider["status"] == "unavailable" for provider in response.json["providers"]))

    def test_cors_accepts_both_local_frontend_hosts(self):
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
            response = self.client.get("/api/health", headers={"Origin": origin})
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), origin)


if __name__ == "__main__":
    unittest.main()

class FreeRoutingTests(unittest.TestCase):
    def test_osm_lookup_is_used_when_browser_sends_no_metrics(self):
        found = {"metrics": {"distance_km": 9.4, "duration_minutes": 31},
                 "pickup": {"lat": 12.9, "lng": 77.6}, "destination": {"lat": 12.96, "lng": 77.7}}
        with patch("cabcompare.backend.app.osm_route_metrics", return_value=found):
            client = create_app().test_client()
            response = client.post("/api/rides/compare", json={"pickup": "A", "destination": "B"})
        self.assertEqual(response.json["fare_source"], "UNAVAILABLE")
        self.assertEqual(response.json["route_metrics"]["distance_km"], 9.4)
        uber = next(r for r in response.json["rides"] if r["provider"] == "Uber")
        params = parse_qs(urlparse(uber["booking_url"]).query)
        self.assertEqual(json.loads(params["drop[0]"][0])["latitude"], 12.96)
        self.assertTrue(all(ride["fare"] is None for ride in response.json["rides"]))

    def test_missing_link_coordinates_are_resolved_without_changing_client_metrics(self):
        found = {"metrics": {"distance_km": 10, "duration_minutes": 30},
                 "pickup": {"lat": 12.9, "lng": 77.6}, "destination": {"lat": 12.96, "lng": 77.7}}
        with patch("cabcompare.backend.app.osm_route_points", return_value={
            "pickup": found["pickup"], "destination": found["destination"],
        }) as lookup:
            client = create_app().test_client()
            response = client.post("/api/rides/compare", json={
                "pickup": "A", "destination": "B",
                "route_metrics": {"distance_km": 5, "duration_minutes": 15},
            })
        self.assertEqual(response.status_code, 200)
        lookup.assert_called_once_with("A", None, "B", None)
        self.assertEqual(response.json["route_metrics"], {"distance_km": 5.0, "duration_minutes": 15.0})
        uber = next(r for r in response.json["rides"] if r["provider"] == "Uber")
        params = parse_qs(urlparse(uber["booking_url"]).query)
        self.assertEqual(json.loads(params["pickup"][0])["latitude"], 12.9)
        self.assertEqual(json.loads(params["drop[0]"][0])["latitude"], 12.96)
        self.assertFalse(uber["booking"]["prefilled"])
