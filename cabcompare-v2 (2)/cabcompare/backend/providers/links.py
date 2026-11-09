"""Booking link builders.

Every URL here is an https link on the provider's own domain, so on a phone
with the app installed the OS can hand it to the app, and on desktop it opens
the provider's website. Only Uber (documented "Ride Request" universal link)
and Ola (book.olacabs.com web booking) accept a pre-filled route. Rapido and
Namma Yatri have no public route-prefill link that we could verify, so those
open the provider's official page and the user enters the route there.

Verify each format against the provider's current docs before production use,
and edit ONLY this file if a provider changes its link scheme.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode


def _has_coords(place: dict[str, Any]) -> bool:
    return place.get("lat") is not None and place.get("lng") is not None


def uber_link(route: dict[str, Any]) -> dict[str, Any]:
    pickup, drop = route["pickup"], route["destination"]
    params: dict[str, str] = {"action": "setPickup"}
    client_id = os.getenv("UBER_CLIENT_ID")
    if client_id:
        params["client_id"] = client_id
    if _has_coords(pickup):
        params["pickup[latitude]"] = f"{pickup['lat']:.6f}"
        params["pickup[longitude]"] = f"{pickup['lng']:.6f}"
        params["pickup[formatted_address]"] = pickup["text"]
    else:
        params["pickup"] = "my_location"
    if _has_coords(drop):
        params["dropoff[latitude]"] = f"{drop['lat']:.6f}"
        params["dropoff[longitude]"] = f"{drop['lng']:.6f}"
    params["dropoff[formatted_address]"] = drop["text"]
    return {"url": "https://m.uber.com/ul/?" + urlencode(params), "prefilled": True}


def ola_link(route: dict[str, Any]) -> dict[str, Any]:
    pickup, drop = route["pickup"], route["destination"]
    if not (_has_coords(pickup) and _has_coords(drop)):
        # Ola needs coordinates; without them we can only open the booking page.
        return {"url": "https://book.olacabs.com/", "prefilled": False}
    params = {
        "serviceType": "p2p",
        "lat": f"{pickup['lat']:.6f}", "lng": f"{pickup['lng']:.6f}", "pickup": pickup["text"],
        "drop_lat": f"{drop['lat']:.6f}", "drop_lng": f"{drop['lng']:.6f}", "drop": drop["text"],
    }
    return {"url": "https://book.olacabs.com/?" + urlencode(params), "prefilled": True}


def rapido_link(route: dict[str, Any]) -> dict[str, Any]:
    return {"url": "https://www.rapido.bike/", "prefilled": False}


def namma_yatri_link(route: dict[str, Any]) -> dict[str, Any]:
    return {"url": "https://nammayatri.in/", "prefilled": False}


BUILDERS = {
    "uber": uber_link,
    "ola": ola_link,
    "rapido": rapido_link,
    "namma yatri": namma_yatri_link,
}


def booking_for(provider: str, route: dict[str, Any]) -> dict[str, Any] | None:
    builder = BUILDERS.get(provider.casefold())
    if not builder:
        return None
    return {"provider": provider, **builder(route)}
