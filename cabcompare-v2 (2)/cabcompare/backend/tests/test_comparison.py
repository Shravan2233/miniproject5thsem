import unittest

from cabcompare.backend.services.comparison import InvalidRoute, compare_rides


RIDES = [
    {"id": "uber-auto", "provider": "Uber", "ride_type": "auto", "fare": 120, "currency": "INR", "fare_status": "demo", "availability_status": "available", "pickup_eta_minutes": 7, "trip_duration_minutes": 20},
    {"id": "rapido-bike", "provider": "Rapido", "ride_type": "bike", "fare": 65, "currency": "INR", "fare_status": "demo", "availability_status": "available", "pickup_eta_minutes": 3, "trip_duration_minutes": 24},
    {"id": "ola-auto", "provider": "Ola", "ride_type": "auto", "fare": 100, "currency": "INR", "fare_status": "demo", "availability_status": "available", "pickup_eta_minutes": 10, "trip_duration_minutes": 19},
]


class ComparisonTests(unittest.TestCase):
    def test_sorts_by_fare_and_marks_lowest_comparable_result(self):
        result = compare_rides("Central Station", "City Mall", RIDES)
        self.assertEqual([ride["fare"] for ride in result["rides"]], [65, 100, 120])
        self.assertEqual([ride["id"] for ride in result["rides"] if ride["is_lowest"]], ["rapido-bike"])
        self.assertEqual(result["fare_source"], "demo")

    def test_filters_categories_and_sorts_by_pickup(self):
        result = compare_rides("A", "B", RIDES, category="auto", sort="pickup")
        self.assertEqual([ride["id"] for ride in result["rides"]], ["uber-auto", "ola-auto"])

    def test_does_not_claim_lowest_across_different_fare_sources(self):
        rides = [dict(RIDES[0]), dict(RIDES[1])]
        rides[1]["fare_status"] = "estimated"
        result = compare_rides("A", "B", rides)
        self.assertFalse(any(ride["is_lowest"] for ride in result["rides"]))

    def test_rejects_empty_or_identical_locations(self):
        with self.assertRaises(InvalidRoute):
            compare_rides(" ", "B", RIDES)
        with self.assertRaises(InvalidRoute):
            compare_rides("Same", "same", RIDES)


if __name__ == "__main__":
    unittest.main()