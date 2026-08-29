"""Resolve a Day's activities into map points/routes and render the images.

This is the bridge from the data model to :mod:`.render`. It decides which
objects are located (explicit ``coordinate`` first; geocoded from name/address
only when ``infer_coordinates_from_address`` is on), builds the drive routes, and
splits out per-area detail maps.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .geocode import geocode
from .render import render_map
from .routing import route

# The pin label for the night's accommodation (★, U+2605) — distinct from the
# numbered activity pins (1..N) and the lettered area pins (A/B/C…). It renders
# on the PNG map, the PDF discs and the interactive markers (it's in DejaVu Sans).
STAY_PIN = "★"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (31, 78, 95)


def _route_through(points, cache):
    """Driving geometry through an ordered list of ``(lat, long)`` points,
    chaining :func:`route` over each consecutive pair (start → wp1 → … → end)
    and stitching the segments into one line."""
    line: list[tuple[float, float]] = []
    for a, b in zip(points, points[1:]):
        seg = route(a, b, cache)
        if line and seg and line[-1] == seg[0]:
            line.extend(seg[1:])
        else:
            line.extend(seg)
    return line


def _anchor_city(city: str) -> str:
    for arrow in ("→", "->"):
        if arrow in city:
            city = city.split(arrow)[-1]
    return city.strip()


@dataclass
class RenderedMap:
    image: object          # PIL.Image.Image
    legend: list[str]      # activity names, in pin order


@dataclass
class DayMaps:
    main: RenderedMap | None = None
    areas: list[tuple[str, RenderedMap]] = field(default_factory=list)  # (area title, map)
    numbers: dict = field(default_factory=dict)  # id(activity) -> its pin number

    def number_for(self, act) -> int | None:
        """The pin number for ``act`` on whichever map it appears (or None)."""
        return self.numbers.get(id(act))


@dataclass
class _Pt:
    label: str
    lat: float
    long: float
    act: object = None      # the source activity, to map it back to its pin number


class _Resolver:
    def __init__(self, itinerary, cache):
        self.it = itinerary
        self.cache = cache
        self.infer = itinerary.infer_coordinates_from_address
        self.countries = itinerary.inference_countries

    def _geo(self, query: str):
        if not self.infer or not query:
            return None
        return geocode(query, self.countries, self.cache)

    def point_coord(self, act, city: str):
        """(lat, long) for a point activity, honoring show_on_map + inference."""
        c = act.coordinate
        if c is not None:
            return (c.lat, c.long) if c.show_on_map else None
        query = None
        if act.kind in ("point_of_interest", "place", "hike"):
            query = f"{act.name}, {city}" if city else act.name
        elif act.kind == "meal":
            who = act.restaurant or act.area
            query = f"{who}, {city}" if (who and city) else who
        return self._geo(query)

    def endpoint_coord(self, coord, name: str, city: str):
        if coord is not None:
            return (coord.lat, coord.long)
        return self._geo(f"{name}, {city}" if city else name)


def _leg_coord(coord):
    """``(lat, long)`` for a transport endpoint, honoring ``show_on_map``."""
    if coord is None or not coord.show_on_map:
        return None
    return (coord.lat, coord.long)


def day_legs(day, itinerary):
    """``[[(lat, long), (lat, long)], …]`` — one straight origin→destination pair
    per transport leg touching ``day``, drawn as a dotted line (the real path
    isn't known, and for a flight isn't a path on the ground at all).

    A leg touches every day it is *in progress* on: the day it departs, the day
    it arrives, and any day in between. So an **overnight** leg appears on both
    of its day maps — leaving on the departure day's map, arriving on the next
    day's. Only legs whose JSON gives both endpoint coordinates (with
    ``show_on_map``) are drawn; endpoints are never geocoded, so the same legs
    appear whatever ``infer_coordinates_from_address`` says.
    """
    d = getattr(day, "date", None)
    if d is None:
        return []
    legs = []
    for t in itinerary.transports:
        if t.start_date is None:
            continue
        if not (t.start_date <= d <= (t.end_date or t.start_date)):
            continue
        a, b = _leg_coord(t.start_coordinate), _leg_coord(t.end_coordinate)
        if a and b:
            legs.append([a, b])
    return legs


def resolve_day(day, itinerary, cache):
    """Return (main_points, routes, route_nodes, area_details) for a day.

    * ``main_points`` — ordered ``[_Pt]``, one per located point activity (a
      place/area contributes a single pin).
    * ``routes`` — ``[[(lat, long), …]]`` drive geometries.
    * ``route_nodes`` — ``[[(lat, long), …]]`` the named stops of each route
      (the departure plus each *named* waypoint), for the full-opacity node
      discs on the map. Unnamed route-shaping waypoints are excluded.
    * ``area_details`` — ``[(title, [_Pt])]`` for places with >= 2 nested points.
    """
    r = _Resolver(itinerary, cache)
    city = _anchor_city(day.city)
    main: list[_Pt] = []
    routes: list[list[tuple[float, float]]] = []
    route_nodes: list[list[tuple[float, float]]] = []
    areas: list[tuple[str, list[_Pt]]] = []

    for act in day.activities:
        if act.kind == "buffer":
            continue
        if act.kind == "road":
            # the departure (start/coordinate) plus the waypoints, in order —
            # the last waypoint is the arrival.
            a = r.endpoint_coord(act.coordinate, act.start, city)
            waypoints = [(w.coordinate.lat, w.coordinate.long) for w in act.waypoints]
            pts = ([a] if a else []) + waypoints
            if len(pts) >= 2:
                routes.append(_route_through(pts, cache))
                # only the departure and *named* waypoints get a node disc;
                # unnamed (route-shaping) waypoints still bend the route but
                # are not marked with their own circle.
                named = [(w.coordinate.lat, w.coordinate.long)
                         for w in act.waypoints if w.location]
                route_nodes.append(([a] if a else []) + named)
            continue
        if act.kind == "place":
            nested = []
            for sub in act.activities:
                sc = r.point_coord(sub, city)
                if sc:
                    nested.append(_Pt(sub.title, sc[0], sc[1], sub))
            coord = r.point_coord(act, city)
            hidden = act.coordinate is not None and not act.coordinate.show_on_map
            if coord is None and nested and not hidden:
                # fall back to the centroid of the area's located sub-points
                coord = (sum(p.lat for p in nested) / len(nested),
                         sum(p.long for p in nested) / len(nested))
            if coord:
                main.append(_Pt(act.title, coord[0], coord[1], act))
            if len(nested) >= 2:
                areas.append((act.title, nested))
            continue
        coord = r.point_coord(act, city)
        if coord:
            main.append(_Pt(act.title, coord[0], coord[1], act))
    return main, routes, route_nodes, areas


def render_day_maps(day, itinerary, cache, ink_saver: bool = False) -> DayMaps:
    """Build the main day map and any per-area detail maps (PIL images)."""
    main_pts, routes, route_nodes, area_details = resolve_day(day, itinerary, cache)
    accent = _hex_to_rgb(itinerary.cover_color)
    result = DayMaps()

    # main map: activities numbered 1..N
    main_points = [(p.lat, p.long) for p in main_pts]
    main_labels = [str(i) for i in range(1, len(main_pts) + 1)]
    for i, p in enumerate(main_pts, start=1):
        if p.act is not None:
            result.numbers[id(p.act)] = str(i)

    # the night's stay, pinned with ★
    stay = itinerary.stay_for(getattr(day, "date", None))
    if stay is not None and stay.coordinate is not None and stay.coordinate.show_on_map:
        main_points.append((stay.coordinate.lat, stay.coordinate.long))
        main_labels.append(STAY_PIN)
        result.numbers[id(stay)] = STAY_PIN

    # area detail maps: pins lettered A, B, C…
    for _title, pts in area_details:
        for j, p in enumerate(pts):
            if p.act is not None:
                result.numbers[id(p.act)] = chr(ord("A") + j)

    nodes = [c for line in route_nodes for c in line]
    legs = day_legs(day, itinerary)
    all_coords = list(main_points) + [c for line in routes for c in line]
    # Legs do NOT widen the extent: a transatlantic flight would zoom a day map
    # out to the ocean. It stays framed on the day's own pins and drives, with
    # the leg's dotted line running off the edge toward where it goes. Only a
    # day with nothing else locatable (a pure travel day) is framed on its legs.
    if not all_coords:
        all_coords = [c for line in legs for c in line]
    if all_coords:
        img = render_map(all_coords, routes, main_points, accent, cache.tiles,
                         ink_saver=ink_saver, labels=main_labels, route_nodes=nodes,
                         legs=legs)
        result.main = RenderedMap(img, [p.label for p in main_pts])

    stay_coord = None
    if stay is not None and stay.coordinate is not None and stay.coordinate.show_on_map:
        stay_coord = (stay.coordinate.lat, stay.coordinate.long)

    for title, pts in area_details:
        coords = [(p.lat, p.long) for p in pts]
        letters = [chr(ord("A") + j) for j in range(len(pts))]
        # The extent is fixed by the area's own points (the first argument);
        # pins are the lettered points plus that night's stay ★. Passing the ★ as
        # a *pin only* — never in the extent — is what keeps the detail map's zoom
        # and centering exactly as they'd be without it: a hotel just outside the
        # area's box still shows in the surrounding margin, and one further out
        # simply falls off the canvas instead of widening the shot.
        points, labels = list(coords), list(letters)
        if stay_coord is not None:
            points.append(stay_coord)
            labels.append(STAY_PIN)
        img = render_map(coords, [], points, accent, cache.tiles,
                         ink_saver=ink_saver, labels=labels)
        result.areas.append((title, RenderedMap(img, [p.label for p in pts])))

    return result
