import unittest

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
