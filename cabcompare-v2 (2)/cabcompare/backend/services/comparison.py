from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


CATEGORIES = {"bike", "auto", "sedan", "premium"}
SORT_OPTIONS = {"cheapest", "pickup", "best_value"}


class InvalidRoute(ValueError):
    pass


def validate_route(pickup: Any, destination: Any) -> tuple[str, str]:
    if not isinstance(pickup, str) or not isinstance(destination, str):
        raise InvalidRoute("Pickup and destination must be text.")
    pickup = " ".join(pickup.split())
    destination = " ".join(destination.split())
    if not pickup or not destination:
        raise InvalidRoute("Enter both a pickup and destination.")
    if len(pickup) > 160 or len(destination) > 160:
        raise InvalidRoute("Locations must be 160 characters or fewer.")
    if pickup.casefold() == destination.casefold():
        raise InvalidRoute("Pickup and destination must be different.")
    return pickup, destination


def compare_rides(
    pickup: str,
    destination: str,
    rides: list[dict[str, Any]],
    category: str = "all",
    sort: str = "cheapest",
) -> dict[str, Any]:
    pickup, destination = validate_route(pickup, destination)
    if category != "all" and category not in CATEGORIES:
        raise ValueError("Unsupported ride category.")
    if sort not in SORT_OPTIONS:
        raise ValueError("Unsupported sort option.")

    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for ride in rides:
        if category != "all" and ride.get("ride_type") != category:
            continue
        key = (str(ride.get("provider", "")).casefold(), str(ride.get("ride_type", "")).casefold())
        if key[0] and key[1]:
            unique.setdefault(key, dict(ride))

    results = list(unique.values())
    comparable = [
        ride for ride in results
        if ride.get("availability_status") == "available"
        and isinstance(ride.get("fare"), (int, float))
        and ride["fare"] >= 0
        and ride.get("currency")
        and ride.get("fare_status") in {"demo", "estimated", "live"}
    ]
    lowest_id = None
    if comparable:
        currency = comparable[0]["currency"]
        status = comparable[0]["fare_status"]
        same_basis = [
            ride for ride in comparable
            if ride["currency"] == currency and ride["fare_status"] == status
        ]
        if len(same_basis) >= 2:
            lowest = min(same_basis, key=lambda ride: ride["fare"])
            lowest_id = lowest.get("id")

    if sort == "cheapest":
        results.sort(key=lambda ride: (ride.get("fare") is None, ride.get("fare") or float("inf")))
    elif sort == "pickup":
        results.sort(key=lambda ride: (ride.get("pickup_eta_minutes") is None, ride.get("pickup_eta_minutes") or float("inf")))
    else:
        results.sort(
            key=lambda ride: (
                ride.get("fare") is None or ride.get("trip_duration_minutes") is None,
                (ride.get("fare") or float("inf")) / max(ride.get("trip_duration_minutes") or 1, 1),
            )
        )

    for ride in results:
        ride["is_lowest"] = ride.get("id") == lowest_id if lowest_id else False

    return {
        "route": {"pickup": pickup, "destination": destination},
        "rides": results,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "fare_source": results[0].get("fare_status", "demo") if results else "demo",
    }