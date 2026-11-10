"""Free route lookup (no API key): OpenStreetMap Nominatim for addresses, OSRM for driving distance.

Used when the browser did not send route metrics (for example no Google Maps key).
Both are public community services with fair-use limits, which is fine for a student
project but not for production traffic. Any failure returns None; provider fares
remain unavailable rather than being synthesized from route distance.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from typing import Any, Callable

from .estimates import parse_metrics

USER_AGENT = "CabCompare/1.0 (student project)"
TRAFFIC_FACTOR = 1.25  # OSRM times ignore traffic; this is a rough city-traffic allowance
_sleep = time.sleep


def _get_json(url: str, timeout: int = 6) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def compact_place_label(label: str) -> str:
    if len(label) <= 160:
        return label
    parts = label.split(", ")
    compact = parts[0][:157]
    for part in parts[1:]:
        candidate = f"{compact}, {part}"
        if len(candidate) > 157:
            break
        compact = candidate
    return f"{compact.rstrip(', ')}..."


def normalize_place_query(text: str) -> str:
    return re.sub(r"\bbanglore\b", "Bangalore", text, flags=re.IGNORECASE)


def place_suggestions(
    text: str,
    near: dict[str, float] | None = None,
    fetch: Callable = _get_json,
) -> list[dict[str, Any]]:
    params = {
        "q": normalize_place_query(text),
        "format": "jsonv2",
        "addressdetails": "1",
        "countrycodes": "in",
        "limit": "5",
    }
    if near:
        params["viewbox"] = f"{near['lng'] - 0.5},{near['lat'] + 0.5},{near['lng'] + 0.5},{near['lat'] - 0.5}"
    found = fetch("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params))
    suggestions = []
    for item in found:
        label = item.get("display_name")
        if not label:
            continue
        label = compact_place_label(label)
        parts = label.split(", ")
        suggestions.append({
            "id": f"{item.get('osm_type', 'place')}:{item.get('osm_id', label)}",
            "main": parts[0],
            "secondary": ", ".join(parts[1:]),
            "text": label,
            "lat": float(item["lat"]),
            "lng": float(item["lon"]),
        })
    return suggestions[:5]


def geocode(text: str, near: dict[str, float] | None = None, fetch: Callable = _get_json) -> dict[str, float] | None:
    params = {"q": normalize_place_query(text), "format": "jsonv2", "limit": "1", "countrycodes": "in"}
    if near:
        params["viewbox"] = f"{near['lng'] - 0.5},{near['lat'] + 0.5},{near['lng'] + 0.5},{near['lat'] - 0.5}"
    found = fetch("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params))
    if not found:
        return None
    return {"lat": float(found[0]["lat"]), "lng": float(found[0]["lon"])}


def osm_route_points(pickup_text, pickup_coords, destination_text, destination_coords, fetch: Callable = _get_json):
    """Resolve missing pickup and destination coordinates, or return None."""
    try:
        origin = pickup_coords
        if origin is None:
            origin = geocode(pickup_text, fetch=fetch)
            if destination_coords is None:
                _sleep(1.1)  # Nominatim allows about one request per second
        destination = destination_coords or geocode(destination_text, near=origin, fetch=fetch)
        if not origin or not destination:
            return None
        return {"pickup": origin, "destination": destination}
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None


def osm_route_metrics(pickup_text, pickup_coords, destination_text, destination_coords, fetch: Callable = _get_json):
    """Return {'metrics', 'pickup', 'destination'} or None."""
    try:
        points = osm_route_points(
            pickup_text, pickup_coords, destination_text, destination_coords, fetch=fetch
        )
        if not points:
            return None
        origin, destination = points["pickup"], points["destination"]
        url = (f"https://router.project-osrm.org/route/v1/driving/{origin['lng']},{origin['lat']};"
               f"{destination['lng']},{destination['lat']}?overview=false")
        route = fetch(url)["routes"][0]
        metrics = parse_metrics({
            "distance_km": route["distance"] / 1000,
            "duration_minutes": route["duration"] / 60 * TRAFFIC_FACTOR,
        })
        return {"metrics": metrics, **points}
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None
