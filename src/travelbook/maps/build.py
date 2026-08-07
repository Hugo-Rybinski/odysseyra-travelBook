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


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (31, 78, 95)


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


@dataclass
class _Pt:
    label: str
    lat: float
    long: float


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


def resolve_day(day, itinerary, cache):
    """Return (main_points, routes, area_details) for a day.

    * ``main_points`` — ordered ``[_Pt]``, one per located point activity (a
      place/area contributes a single pin).
    * ``routes`` — ``[[(lat, long), …]]`` drive geometries.
    * ``area_details`` — ``[(title, [_Pt])]`` for places with >= 2 nested points.
    """
    r = _Resolver(itinerary, cache)
    city = _anchor_city(day.city)
    main: list[_Pt] = []
    routes: list[list[tuple[float, float]]] = []
    areas: list[tuple[str, list[_Pt]]] = []

    for act in day.activities:
        if act.kind == "buffer":
            continue
        if act.kind == "road":
            a = r.endpoint_coord(act.start_coordinate, act.start, city)
            b = r.endpoint_coord(act.end_coordinate, act.end, city)
            if a and b:
                routes.append(route(a, b, cache))
            continue
        coord = r.point_coord(act, city)
        if coord:
            main.append(_Pt(act.title, coord[0], coord[1]))
        if act.kind == "place":
            nested = []
            for sub in act.activities:
                sc = r.point_coord(sub, city)
                if sc:
                    nested.append(_Pt(sub.title, sc[0], sc[1]))
            if len(nested) >= 2:
                areas.append((act.title, nested))
    return main, routes, areas


def render_day_maps(day, itinerary, cache, ink_saver: bool = False) -> DayMaps:
    """Build the main day map and any per-area detail maps (PIL images)."""
    main_pts, routes, area_details = resolve_day(day, itinerary, cache)
    accent = _hex_to_rgb(itinerary.cover_color)
    result = DayMaps()

    all_coords = [(p.lat, p.long) for p in main_pts]
    all_coords += [c for line in routes for c in line]
    if all_coords:
        img = render_map(all_coords, routes, [(p.lat, p.long) for p in main_pts],
                         accent, cache.tiles, ink_saver=ink_saver)
        result.main = RenderedMap(img, [p.label for p in main_pts])

    for title, pts in area_details:
        coords = [(p.lat, p.long) for p in pts]
        img = render_map(coords, [], coords, accent, cache.tiles, ink_saver=ink_saver)
        result.areas.append((title, RenderedMap(img, [p.label for p in pts])))

    return result
