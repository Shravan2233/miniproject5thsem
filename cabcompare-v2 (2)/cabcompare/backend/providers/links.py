"""Build official provider booking URLs and report route-transfer limitations."""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlencode


def _has_coords(place: dict[str, Any]) -> bool:
    return place.get("lat") is not None and place.get("lng") is not None


def _uber_location(place: dict[str, Any]) -> str:
    parts = [part.strip() for part in place["text"].split(",") if part.strip()]
    location = {
        "latitude": place["lat"],
        "longitude": place["lng"],
        "addressLine1": parts[0] if parts else place["text"].strip(),
        "addressLine2": place["text"].strip(),
    }
    return json.dumps(location, separators=(",", ":"))


def uber_link(route: dict[str, Any], ride_type: str | None = None) -> dict[str, Any]:
    pickup, drop = route["pickup"], route["destination"]
    params: dict[str, str] = {}
    client_id = os.getenv("UBER_CLIENT_ID")
    if client_id:
        params["client_id"] = client_id
    has_route = _has_coords(pickup) and _has_coords(drop)
    if has_route:
        params["pickup"] = _uber_location(pickup)
        params["drop[0]"] = _uber_location(drop)
    url = "https://m.uber.com/looking"
    if params:
        url += "?" + urlencode(params)
    if has_route and not client_id:
        message = (
            "Pickup and destination coordinates are in Uber's documented link format. "
            "Uber may replace the names with nearby provider locations. "
            "UBER_CLIENT_ID is not configured for the documented app handoff; "
            "confirm both locations in Uber's mobile web page."
        )
    elif has_route:
        message = (
            "Pickup and destination coordinates are in Uber's documented link format. "
            "Uber may replace the names with nearby provider locations; "
            "confirm both locations on the provider screen before requesting."
        )
    else:
        message = "Coordinates are unavailable; enter pickup and destination in Uber."
    return {
        "url": url,
        "mobile_url": None,
        "prefilled": False,
        "locations_in_url": has_route,
        "location_transfer": "url_generated_unverified" if has_route else "manual_entry_required",
        "verification_status": "not_verified_on_mobile_device",
        "message": message,
    }


def ola_link(route: dict[str, Any], ride_type: str | None = None) -> dict[str, Any]:
    pickup, drop = route["pickup"], route["destination"]
    has_route = _has_coords(pickup) and _has_coords(drop)
    url = "https://book.olacabs.com/"
    mobile_url = None
    message = "Coordinates are unavailable; enter pickup and destination in Ola."
    transfer_status = "manual_entry_required"
    locations_in_url = False
    affiliate_attribution = "not_configured"
    if has_route:
        web_params = {
            "lat": f"{pickup['lat']:.6f}",
            "lng": f"{pickup['lng']:.6f}",
            "drop_lat": f"{drop['lat']:.6f}",
            "drop_lng": f"{drop['lng']:.6f}",
            "pickup_name": pickup["text"],
            "drop_name": drop["text"],
            "dsw": "yes",
        }
        xapp_token = os.getenv("OLA_XAPP_TOKEN")
        if xapp_token:
            web_params["utm_source"] = xapp_token
            affiliate_attribution = "configured"
            mobile_params = {
                "lat": web_params["lat"],
                "lng": web_params["lng"],
                "drop_lat": web_params["drop_lat"],
                "drop_lng": web_params["drop_lng"],
                "address": pickup["text"],
                "drop_address": drop["text"],
                "landing_page": "bk",
                "utm_source": xapp_token,
            }
            mobile_url = (
                "https://olawebcdn.com/assets/ola-universal-link.html?"
                + urlencode(mobile_params)
            )
            transfer_status = "web_prefill_tested_universal_link_unverified"
            handoff_note = (
                "The documented Ola universal link is also available on mobile; "
                "native handoff has not been device-tested."
            )
        else:
            transfer_status = "web_prefill_tested_mobile_unverified"
            handoff_note = (
                "Ola's XAPP token is not configured, so the documented app/universal "
                "link and affiliate attribution are unavailable."
            )
        message = (
            "Ola displayed both route locations in the desktop web test. "
            f"{handoff_note} Confirm the route before booking."
        )
        url += "?" + urlencode(web_params)
        locations_in_url = True
    return {
        "url": url,
        "mobile_url": mobile_url,
        "prefilled": has_route,
        "locations_in_url": locations_in_url,
        "location_transfer": transfer_status,
        "verification_status": (
            "desktop_web_prefill_verified_mobile_unverified"
            if has_route
            else "not_verified_on_mobile_device"
        ),
        "affiliate_attribution": affiliate_attribution,
        "message": message,
    }


def rapido_link(route: dict[str, Any], ride_type: str | None = None) -> dict[str, Any]:
    return {
        "url": "https://www.rapido.bike/",
        "mobile_url": None,
        "prefilled": False,
        "locations_in_url": False,
        "location_transfer": "manual_entry_required",
        "verification_status": "not_supported",
        "message": "Rapido has no verified public route-prefill link; enter both locations in Rapido.",
    }


def namma_yatri_link(route: dict[str, Any], ride_type: str | None = None) -> dict[str, Any]:
    return {
        "url": "https://nammayatri.in/",
        "mobile_url": None,
        "prefilled": False,
        "locations_in_url": False,
        "location_transfer": "manual_entry_required",
        "verification_status": "not_supported",
        "message": "Namma Yatri has no verified public route-prefill link; enter both locations in Namma Yatri.",
    }


BUILDERS = {
    "uber": uber_link,
    "ola": ola_link,
    "rapido": rapido_link,
    "namma yatri": namma_yatri_link,
}


def booking_for(provider: str, route: dict[str, Any], ride_type: str | None = None) -> dict[str, Any] | None:
    builder = BUILDERS.get(provider.casefold())
    if not builder:
        return None
    return {"provider": provider, **builder(route, ride_type)}
