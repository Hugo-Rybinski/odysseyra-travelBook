"""Write computed data back into a raw itinerary dict, so a later build is
deterministic and offline.

* :func:`fill_coordinates` — missing ``coordinate`` objects, geocoded from
  names/addresses (the ``geocode`` command). The geocoder is injectable for
  testing.
* :func:`fill_routes` — the driving line of every road leg that carries no
  ``gpx`` of its own, stored as a generated GPX route (the ``route`` command).
"""

from __future__ import annotations

import base64
import copy
import gzip

from .build import _anchor_city, road_departure, road_leg_lines
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


def _is_generated(leg) -> bool:
    """The model's reading of the flag, so the two agree on which file is ours."""
    from ..models.parsers import _parse_bool

    return _parse_bool(leg.get("gpx_generated", False))


def _encode_route(line, name: str) -> str:
    """``line`` as a gzipped, base64-encoded GPX ``<rte>`` — the shape the leg's
    ``gpx`` field already takes. Simplified exactly as a parsed GPX is
    (``models/gpx.py``'s ``_simplify``), so the file holds no point the drawing
    would throw away, and gzipped with no timestamp so a re-run over the same
    route rewrites the same bytes."""
    from ..models.gpx import _simplify
    from ..models.gpx_export import route_gpx

    kept = [line[i] for i in _simplify(line)]
    raw = gzip.compress(route_gpx(kept, name).encode("utf-8"), mtime=0)
    return base64.b64encode(raw).decode("ascii")


def fill_routes(data: dict, cache) -> tuple[int, int, int]:
    """Mutate ``data`` in place, storing the computed driving line of each road
    leg as its ``gpx`` with ``gpx_generated: true``. Returns ``(written,
    recorded, missed)``: legs given a route, legs left alone because they carry a
    user's own recording, and legs that couldn't be routed.

    The line is the one the maps draw — :func:`.build.road_leg_lines` over the
    departure :func:`.build.road_departure` resolves — asked for with
    ``fallback=False``, since a straight line between two towns stored as *the*
    route would outlive the network blip that produced it. Three rules make a
    re-run safe:

    * a ``gpx`` **without** the flag is the user's and is never touched;
    * a generated one is **recomputed**: the model is built from a copy with
      every generated file stripped, so the stored line can't feed itself, and
      the new line replaces it — it follows an edited endpoint;
    * a leg that can't be routed this time **keeps** its previous generated line
      rather than losing it to an offline run.

    A drive with ``hide_on_map`` is skipped, as the maps skip routing it.
    """
    from ..models import Itinerary

    stripped = copy.deepcopy(data)
    for day in stripped.get("days", []) or []:
        for act in (day.get("activities") or []) if isinstance(day, dict) else []:
            if isinstance(act, dict) and act.get("type") == "road":
                for leg in act.get("legs") or []:
                    if isinstance(leg, dict) and _is_generated(leg):
                        leg.pop("gpx", None)
                        leg.pop("gpx_generated", None)
    itinerary = Itinerary.from_dict(stripped)

    written = recorded = missed = 0
    for day, raw_day in zip(itinerary.days, data.get("days", []) or []):
        roads = [a for a in day.activities if a.kind == "road"]
        raw_roads = [a for a in raw_day.get("activities") or []
                     if isinstance(a, dict) and a.get("type") == "road"]
        for road, raw_road in zip(roads, raw_roads):
            if road.hide_on_map:
                continue
            legs = [leg for leg in raw_road.get("legs") or [] if isinstance(leg, dict)]
            lines = [(wp, seg) for wp, seg in road_leg_lines(
                road, road_departure(road, day, itinerary, cache), cache,
                fallback=False) if wp is not None]
            previous = road.start
            for leg, (wp, seg) in zip(legs, lines):
                name = f"{previous} → {wp.location}" if previous else wp.location
                previous = wp.location
                if leg.get("gpx") and not _is_generated(leg):
                    recorded += 1
                    continue
                if not seg or len(seg) < 2:
                    missed += 1
                    continue
                leg["gpx"] = _encode_route(seg, name)
                leg["gpx_generated"] = True
                written += 1
    return written, recorded, missed
