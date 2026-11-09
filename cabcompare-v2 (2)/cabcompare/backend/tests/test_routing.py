import unittest
from urllib.parse import parse_qs, urlparse

from cabcompare.backend.services import routing


def fake_fetch(url):
    if "nominatim" in url:
        return [{"lat": "12.9716", "lon": "77.5946"}]
    return {"routes": [{"distance": 8000, "duration": 1200}]}


class RoutingTests(unittest.TestCase):
    def setUp(self):
        routing._sleep = lambda _s: None

    def test_geocodes_text_then_routes(self):
        found = routing.osm_route_metrics("MG Road", None, "Indiranagar", None, fetch=fake_fetch)
        self.assertEqual(found["metrics"]["distance_km"], 8.0)
        self.assertEqual(found["metrics"]["duration_minutes"], 25)  # 20 min x 1.25 traffic allowance

    def test_place_suggestions_include_labels_and_coordinates(self):
        found = routing.place_suggestions("MG Road", fetch=lambda _url: [{
            "osm_type": "node", "osm_id": 1, "display_name": "MG Road, Bengaluru, India",
            "lat": "12.9", "lon": "77.6",
        }])
        self.assertEqual(found, [{
            "id": "node:1", "main": "MG Road", "secondary": "Bengaluru, India",
            "text": "MG Road, Bengaluru, India", "lat": 12.9, "lng": 77.6,
        }])

    def test_place_suggestions_correct_banglore_and_bias_to_pickup(self):
        requests = []

        def fetch(url):
            requests.append(url)
            return [{
                "osm_type": "node", "osm_id": 3,
                "display_name": "Kempegowda Bus Station, Bengaluru, India",
                "lat": "12.9779", "lon": "77.5724",
            }]

        results = routing.place_suggestions(
            "majestic banglore",
            near={"lat": 12.9438, "lng": 77.5681},
            fetch=fetch,
        )
        params = parse_qs(urlparse(requests[0]).query)
        self.assertEqual(params["q"], ["majestic Bangalore"])
        self.assertEqual(params["viewbox"], ["77.0681,13.4438,78.0681,12.4438"])
        self.assertIn("Bengaluru", results[0]["text"])

    def test_place_suggestion_labels_fit_route_input_limit(self):
        long_label = "BMS College of Engineering, Hanumanthnagar, Basavanagudi, Bengaluru, " + "administrative area, " * 12 + "India"
        found = routing.place_suggestions("BMS College", fetch=lambda _url: [{
            "osm_type": "way", "osm_id": 2, "display_name": long_label,
            "lat": "12.9", "lon": "77.6",
        }])
        self.assertLessEqual(len(found[0]["text"]), 160)
        self.assertTrue(found[0]["text"].startswith("BMS College of Engineering, Hanumanthnagar"))
        self.assertTrue(found[0]["text"].endswith("..."))
        self.assertEqual(found[0]["lat"], 12.9)
        self.assertEqual(found[0]["lng"], 77.6)

    def test_uses_given_coordinates_without_geocoding(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return fake_fetch(url)
        pickup = {"lat": 12.9, "lng": 77.6}
        routing.osm_route_metrics("x", pickup, "y", {"lat": 12.95, "lng": 77.65}, fetch=fetch)
        self.assertEqual(len(calls), 1)

    def test_failures_return_none(self):
        def broken(url):
            raise OSError("network down")
        self.assertIsNone(routing.osm_route_metrics("A", None, "B", None, fetch=broken))
        self.assertIsNone(routing.osm_route_metrics("A", None, "B", None, fetch=lambda u: []))


if __name__ == "__main__":
    unittest.main()
