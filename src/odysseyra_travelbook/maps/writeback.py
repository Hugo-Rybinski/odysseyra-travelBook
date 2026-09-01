"""Fill missing ``coordinate`` objects in a raw itinerary dict by geocoding
names/addresses, so a later build is deterministic and offline. Used by the
``odysseyra-travelBook geocode`` command. The geocoder is injectable for testing."""

from __future__ import annotations

from .build import _anchor_city
from .geocode import geocode as _default_geocode


def fill_coordinates(data: dict, countries, cache, geocoder=_default_geocode):
    """Mutate ``data`` in place, adding coordinates it can resolve. Returns
    ``(filled, missed)`` counts. Existing coordinates are never overwritten."""
    counts = [0, 0]

    def resolve(query, target: dict, key: str):
        if not query or key in target:
            return
        hit = geocoder(query, countries, cache)
        if hit:
            target[key] = {"lat": hit[0], "long": hit[1]}
            counts[0] += 1
        else:
            counts[1] += 1

    def q(text, city):
        return f"{text}, {city}" if (text and city) else text

    def do_activity(act, city):
        if not isinstance(act, dict):
            return
        kind = act.get("type")
        if kind == "road":
            # Both endpoints of every leg. A leg that inherits an endpoint from
            # its neighbour names nothing there, so there is nothing to geocode
            # — and the route-shaping waypoints are coordinates already.
            for leg in act.get("legs", []) or []:
                if isinstance(leg, dict):
                    resolve(q(leg.get("start_location"), city), leg, "start_coordinate")
                    resolve(q(leg.get("end_location"), city), leg, "end_coordinate")
        elif kind in ("point_of_interest", "place", "hike"):
            resolve(q(act.get("name"), city), act, "coordinate")
        elif kind == "meal":
            resolve(q(act.get("restaurant") or act.get("area"), city), act, "coordinate")
        for sub in act.get("activities", []) or []:
            do_activity(sub, city)

    for day in data.get("days", []) or []:
        if not isinstance(day, dict):
            continue
        city = _anchor_city(str(day.get("city", "")))
        for act in day.get("activities", []) or []:
            do_activity(act, city)

    # A booking carries no places of its own — its legs do.
    for t in data.get("transport", []) or []:
        if isinstance(t, dict):
            for leg in t.get("legs", []) or []:
                if isinstance(leg, dict):
                    resolve(leg.get("start"), leg, "start_coordinate")
                    resolve(leg.get("end"), leg, "end_coordinate")

    for a in data.get("accommodations", []) or []:
        if isinstance(a, dict):
            resolve(q(a.get("name"), a.get("city", "")), a, "coordinate")

    for cr in data.get("car_rentals", []) or []:
        if isinstance(cr, dict):
            resolve(cr.get("pickup_location"), cr, "pickup_coordinate")
            resolve(cr.get("dropoff_location") or cr.get("pickup_location"),
                    cr, "dropoff_coordinate")

    return tuple(counts)
