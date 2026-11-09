import unittest
from unittest.mock import patch

from cabcompare.backend.app import create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("cabcompare.backend.app.osm_route_metrics", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = create_app().test_client()

    def test_health_reports_demo_mode(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["fare_mode"], "demo")

    def test_compare_requires_valid_route(self):
        response = self.client.post("/api/rides/compare", json={"pickup": "", "destination": "B"})
        self.assertEqual(response.status_code, 400)

    def test_compare_marks_all_fares_as_demo(self):
        response = self.client.post("/api/rides/compare", json={"pickup": "A", "destination": "B"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["fare_source"], "demo")
        self.assertTrue(all(ride["fare_status"] == "demo" for ride in response.json["rides"]))

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
        self.assertIn("dropoff%5Blatitude%5D=12.975600", uber["booking_url"])
        self.assertTrue(uber["booking"]["prefilled"])
        rapido = next(r for r in response.json["rides"] if r["provider"] == "Rapido")
        self.assertFalse(rapido["booking"]["prefilled"])

    def test_invalid_coordinates_are_rejected(self):
        response = self.client.post("/api/rides/compare", json={
            "pickup": "A", "destination": "B", "pickup_coords": {"lat": 999, "lng": 0}})
        self.assertEqual(response.status_code, 400)

    def test_route_metrics_give_labelled_estimates_that_scale_with_distance(self):
        def fares(km):
            r = self.client.post("/api/rides/compare", json={"pickup": "A", "destination": "B",
                "route_metrics": {"distance_km": km, "duration_minutes": km * 3}})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json["fare_source"], "estimated")
            self.assertTrue(all(x["fare_status"] == "estimated" and x["fare_low"] < x["fare"] < x["fare_high"] for x in r.json["rides"]))
            return {(x["provider"], x["ride_type"]): x["fare"] for x in r.json["rides"]}
        short, long_ = fares(3), fares(12)
        self.assertTrue(all(long_[k] > short[k] for k in short))

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
        self.assertEqual(response.json["fare_source"], "estimated")
        self.assertEqual(response.json["route_metrics"]["distance_km"], 9.4)
        uber = next(r for r in response.json["rides"] if r["provider"] == "Uber")
        self.assertIn("dropoff%5Blatitude%5D=12.960000", uber["booking_url"])
