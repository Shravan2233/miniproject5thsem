"""Free route lookup (no API key): OpenStreetMap Nominatim for addresses, OSRM for driving distance.

Used when the browser did not send route metrics (for example no Google Maps key).
Both are public community services with fair-use limits, which is fine for a student
project but not for production traffic. Any failure returns None and the app falls
back to sample fares.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any, Callable

from .estimates import parse_metrics

USER_AGENT = "RideWise/1.0 (student project)"
TRAFFIC_FACTOR = 1.25  # OSRM times ignore traffic; this is a rough city-traffic allowance
_sleep = time.sleep


def _get_json(url: str, timeout: int = 6) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def geocode(text: str, near: dict[str, float] | None = None, fetch: Callable = _get_json) -> dict[str, float] | None:
    params = {"q": text, "format": "jsonv2", "limit": "1", "countrycodes": "in"}
    if near:
        params["viewbox"] = f"{near['lng'] - 0.5},{near['lat'] + 0.5},{near['lng'] + 0.5},{near['lat'] - 0.5}"
    found = fetch("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params))
    if not found:
        return None
    return {"lat": float(found[0]["lat"]), "lng": float(found[0]["lon"])}


def osm_route_metrics(pickup_text, pickup_coords, destination_text, destination_coords, fetch: Callable = _get_json):
    """Return {'metrics', 'pickup', 'destination'} or None."""
    try:
        origin = pickup_coords
        if origin is None:
            origin = geocode(pickup_text, fetch=fetch)
            if destination_coords is None:
                _sleep(1.1)  # Nominatim allows about one request per second
        destination = destination_coords or geocode(destination_text, near=origin, fetch=fetch)
        if not origin or not destination:
            return None
        url = (f"https://router.project-osrm.org/route/v1/driving/{origin['lng']},{origin['lat']};"
               f"{destination['lng']},{destination['lat']}?overview=false")
        route = fetch(url)["routes"][0]
        metrics = parse_metrics({
            "distance_km": route["distance"] / 1000,
            "duration_minutes": route["duration"] / 60 * TRAFFIC_FACTOR,
        })
        return {"metrics": metrics, "pickup": origin, "destination": destination}
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None
