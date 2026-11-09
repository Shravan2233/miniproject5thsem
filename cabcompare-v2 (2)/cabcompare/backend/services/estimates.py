from __future__ import annotations

from typing import Any

from ..providers.rates import HIGH_FACTOR, LOW_FACTOR, RATE_CARDS

MAX_KM = 500
MAX_MINUTES = 24 * 60


def parse_metrics(value: Any) -> dict[str, float] | None:
    """Validate {'distance_km','duration_minutes'} from the client. None if absent."""
    if value is None:
        return None
    try:
        km = float(value["distance_km"])
        minutes = float(value["duration_minutes"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Route metrics must include distance_km and duration_minutes.")
    if not (0 < km <= MAX_KM) or not (0 < minutes <= MAX_MINUTES):
        raise ValueError("Route distance or duration is out of range.")
    return {"distance_km": round(km, 1), "duration_minutes": round(minutes)}


def estimate_rides(metrics: dict[str, float]) -> list[dict[str, Any]]:
    km, minutes = metrics["distance_km"], metrics["duration_minutes"]
    rides = []
    for provider, ride_type, base, free_km, per_km, per_min, min_fare, markup, speed in RATE_CARDS:
        trip_minutes = max(1, round(minutes * speed))
        raw = (base + per_km * max(km - free_km, 0) + per_min * trip_minutes) * markup
        fare = round(max(min_fare, raw))
        rides.append({
            "id": f"{provider.lower().replace(' ', '-')}-{ride_type}-est",
            "provider": provider, "ride_type": ride_type,
            "fare": fare, "fare_low": round(fare * LOW_FACTOR), "fare_high": round(fare * HIGH_FACTOR),
            "currency": "INR", "fare_status": "estimated",
            "pickup_eta_minutes": None, "trip_duration_minutes": trip_minutes, "distance_km": km,
            "availability_status": "available", "booking_url": None, "deep_link": None,
        })
    return rides
