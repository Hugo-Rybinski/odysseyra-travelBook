"""Resolve a Day's activities into map points/routes and render the images.

This is the bridge from the data model to :mod:`.render`. It decides which
objects are located (explicit ``coordinate`` first; geocoded from name/address
only when ``infer_coordinates_from_address`` is on), builds the drive routes, and
splits out per-area detail maps.

:func:`render_trip_map` does the same for the **whole trip** at once — one map
holding every day's points, pinned with their day number.

:func:`render_hike_map` is the odd one out: it draws a single hike's **GPX
track**, which needs no resolving at all (the geometry came with the itinerary)
and so needs nothing but tiles.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field

from .geocode import geocode
from .render import render_map
from .routing import route

# The pin label for the night's accommodation (★, U+2605) — distinct from the
# numbered activity pins (1..N) and the lettered area pins (A/B/C…). It renders
# on the PNG map, the PDF discs and the interactive markers (it's in DejaVu Sans).
STAY_PIN = "★"

# Kilometres per degree of latitude — the basis of every rough distance here.
# Longitude is scaled by cos(latitude) at the point of interest.
_KM_PER_DEG = 111.32


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (31, 78, 95)


def _route_through(points, cache, *, fallback=True):
    """Driving geometry through an ordered list of ``(lat, long)`` points,
    chaining :func:`route` over each consecutive pair (start → wp1 → … → end)
    and stitching the segments into one line.

    ``fallback=False`` gives ``None`` as soon as any pair can't be routed (see
    :func:`.routing.route`), rather than a line with a straight guess in it."""
    line: list[tuple[float, float]] = []
    for a, b in zip(points, points[1:]):
        seg = route(a, b, cache, fallback=fallback)
        if seg is None:
            return None
        if line and seg and line[-1] == seg[0]:
            line.extend(seg[1:])
        else:
            line.extend(seg)
    return line


def road_leg_lines(road, departure, cache, *, fallback=True):
    """One drawn line per **leg** of a drive, as
    ``[(arrival waypoint, [(lat, long), …] | None), …]``.

    Each named waypoint closes a leg; the unnamed ones before it are that leg's
    route-shaping points. A leg with a ``gpx`` contributes the recording's own
    line — the real road, bends and all — and its shaping points are then
    redundant (the recording already runs through them). Without one it is
    routed, so a road with no GPX draws exactly the line it always did.

    A leg's line is ``None`` when it couldn't be built: nothing to route from
    (no departure coordinate and no track), or — with ``fallback=False`` —
    routing was unavailable and a straight guess was refused.

    ``departure`` is the road's start coordinate, possibly ``None``: a track can
    carry a leg on its own."""
    out = []
    prev = departure
    shaping: list[tuple[float, float]] = []
    for wp in road.waypoints:
        here = (wp.coordinate.lat, wp.coordinate.long)
        if not wp.location:
            shaping.append(here)
            continue
        track = getattr(wp, "track", None)
        if track is not None and len(track.points) >= 2:
            out.append((wp, [(lat, long) for lat, long in track.points]))
        elif prev is not None:
            out.append((wp, _route_through([prev] + shaping + [here], cache,
                                           fallback=fallback)))
        else:
            out.append((wp, None))
        prev, shaping = here, []
    if shaping and prev is not None:  # trailing shaping points (no named arrival)
        out.append((None, _route_through([prev] + shaping, cache, fallback=fallback)))
    return out


def _road_route(road, departure, cache):
    """A drive's whole drawn line: its legs' lines (:func:`road_leg_lines`)
    stitched together, skipping any that couldn't be built."""
    line: list[tuple[float, float]] = []
    for _wp, seg in road_leg_lines(road, departure, cache):
        if not seg:
            continue
        if line and line[-1] == seg[0]:
            line.extend(seg[1:])
        else:
            line.extend(seg)
    return line


def road_departure(road, day, itinerary, cache):
    """A drive's departure coordinate as the map resolves it: the road's own
    ``coordinate`` when it has one, else geocoded from its ``start`` (anchored on
    the day's city), else ``None`` — the same call :func:`resolve_day` makes, so
    an export can't drift from what's drawn."""
    r = _Resolver(itinerary, cache)
    return r.endpoint_coord(road.coordinate, road.start, _anchor_city(day.city))


def road_leg_geometry(road, day, itinerary, cache, leg_index, *, fallback=False):
    """The drawn line of one leg of ``road`` — the ``leg_index``-th of its named
    waypoints — as ``(arrival waypoint, [(lat, long), …])``, or ``None`` when it
    can't be built.

    Defaults to ``fallback=False``: this is the seam the *export* uses, and a
    straight line between two towns is a wrong route, not a rough one."""
    lines = [(wp, seg) for wp, seg in
             road_leg_lines(road, road_departure(road, day, itinerary, cache),
                            cache, fallback=fallback)
             if wp is not None]
    if not 0 <= leg_index < len(lines):
        return None
    wp, seg = lines[leg_index]
    return None if not seg or len(seg) < 2 else (wp, seg)


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
    # id(object) -> the activity whose pin it wears instead of one of its own
    # (see `pin_aliases`). The value is the object, not its id, so holding this
    # dict keeps the target alive — an id() key of a freed object would collide.
    aliases: dict = field(default_factory=dict)

    def number_for(self, act) -> int | None:
        """The pin number for ``act`` on whichever map it appears (or None).

        Resolved through ``aliases`` so a drive's shared end reads the number of
        the activity it shares its place with — which is only numbered later in
        the pass, hence the lookup at read time rather than a copied value."""
        label = self.numbers.get(id(act))
        if label is None:
            shared = self.aliases.get(id(act))
            if shared is not None:
                return self.numbers.get(id(shared))
        return label


def pin_aliases(day) -> dict:
    """``{id(object): the activity it borrows a pin from}`` for ``day``.

    A drive with ``same_start_as_previous_activity`` /
    ``same_end_as_next_activity`` says that end of it *is* the neighbouring
    activity's place, so it must not earn a second number for the same point —
    :func:`resolve_day` draws no pin there and this maps the object the renderers
    ask about onto the one that does. Those objects are the same two the pins
    always hung off: the **road** carries its departure's label and the last
    waypoint its arrival's."""
    out: dict = {}
    for act in getattr(day, "activities", []) or []:
        if getattr(act, "kind", "") != "road":
            continue
        if act.start_shared_with is not None:
            out[id(act)] = act.start_shared_with
        if act.end_shared_with is not None and act.waypoints:
            out[id(act.waypoints[-1])] = act.end_shared_with
    return out


@dataclass
class _Pt:
    label: str
    lat: float
    long: float
    act: object = None      # the source activity, to map it back to its pin number
    # This point is one of a **drive's** own points (its departure, a junction,
    # its arrival — `Road.display_*_on_maps`) rather than a stop of its own. The
    # day map pins them like any other; the whole-trip map drops them, where a
    # drive is already drawn as a route and its junctions would only crowd the
    # day numbers. See `resolve_trip`.
    from_road: bool = False


# How close two same-named points must be to count as one place, in km. A day
# routinely names the same spot several times — a drive's junction is also the
# next drive's departure, the village you park in is also the POI you walk to,
# an out-and-back day passes its turning point twice — and each mention used to
# earn its own number, so one place wore two or three pins stacked on top of
# each other and the day's numbering ran far past the number of places in it.
# 1 km is "the same village / the same trailhead": close enough that two pins
# would overlap on a page-width map, far enough not to swallow a neighbour.
PIN_MERGE_KM = 1.0


def _pin_key(name: str) -> str:
    """``name`` reduced for comparison: accents stripped, case folded, the quote
    and dash variants unified, whitespace collapsed.

    The same place reaches us spelled by different hands — a road endpoint typed
    by the user, a POI title, a name lifted out of a GPX file — so `Pont
    d'Espagne`, `Pont d’Espagne` and `pont d'espagne` have to key alike. It stays
    a *name* comparison though: `Cauterets — car park` is deliberately not
    `Cauterets` (that distinction is why an endpoint can be written out even when
    a neighbour would supply it), and the empty string keys to nothing, so a
    nameless point never merges with another.
    """
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    for ch in "‘’ʼ`":
        s = s.replace(ch, "'")
    for ch in "‐‑‒–—":
        s = s.replace(ch, "-")
    return " ".join(s.casefold().split())


def _apart_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Equirectangular km between two nearby points — ample at this scale, and it
    needs no projection."""
    kx = _KM_PER_DEG * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((b[1] - a[1]) * kx, (b[0] - a[0]) * _KM_PER_DEG)


def fold_pins(pts: list[_Pt]) -> list[list[_Pt]]:
    """Group a day's located points so that one *place* earns one pin.

    Returns the groups in first-appearance order, each holding every ``_Pt`` that
    resolved to it — so the caller labels the group once and maps that one label
    onto all of their activities. Two points join when their names key alike
    (:func:`_pin_key`) **and** they sit within :data:`PIN_MERGE_KM`: the name
    alone would merge two different towns of the same name at opposite ends of a
    driving day, and proximity alone would merge a museum with the café across
    the square, which are two stops and want two numbers.

    A point is compared against each group's **first** member — the one whose
    coordinate the pin is actually drawn at — rather than against any member, so
    "within a kilometre" means within a kilometre *of the pin* and a chain of
    near-misses can't drift a group across a valley.
    """
    groups: list[list[_Pt]] = []
    keys: list[str] = []
    for p in pts:
        key = _pin_key(p.label)
        home = None
        if key:
            for grp, k in zip(groups, keys):
                if k == key and _apart_km((grp[0].lat, grp[0].long),
                                          (p.lat, p.long)) <= PIN_MERGE_KM:
                    home = grp
                    break
        if home is None:
            groups.append([p])
            keys.append(key)
        else:
            home.append(p)
    return groups


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
    for leg in itinerary.legs:
        if leg.start_date is None:
            continue
        if not (leg.start_date <= d <= (leg.end_date or leg.start_date)):
            continue
        a, b = _leg_coord(leg.start_coordinate), _leg_coord(leg.end_coordinate)
        if a and b:
            legs.append([a, b])
    return legs


def resolve_day(day, itinerary, cache, *, main: bool = True):
    """Return (main_points, routes, route_nodes, area_details) for a day.

    * ``main_points`` — ordered ``[_Pt]``, one per located point activity (a
      place/area contributes a single pin), plus any of a drive's own points that
      asked for one (``Road.display_*_on_maps``, all off by default).
    * ``routes`` — ``[[(lat, long), …]]`` drive geometries, each leg drawn from
      its ``gpx`` when it has one and routed otherwise (see :func:`_road_route`).
    * ``route_nodes`` — ``[[(lat, long), …]]`` the named stops of each route
      (the departure plus each *named* waypoint), for the full-opacity node
      discs on the map. Unnamed route-shaping waypoints are excluded.
    * ``area_details`` — ``[(title, [_Pt])]`` for places with >= 2 nested points,
      **unless that place set** ``show_map: false`` — then it draws no zoom map,
      so there is nothing for its nested points to be resolved onto.

    ``main=False`` (the day's own ``show_map`` is off) returns the first three
    empty and resolves the areas alone: there is no overview map to place a
    point, a route or a pin *number* on, and the geocoding and routing they would
    need is work the day threw away. The areas survive because their maps are
    switched separately, per place. Only the day's own map answers to this — the
    whole-trip map calls with the default, since the pin there carries the day,
    not the stop.
    """
    r = _Resolver(itinerary, cache)
    city = _anchor_city(day.city)
    main_pts: list[_Pt] = []
    routes: list[list[tuple[float, float]]] = []
    route_nodes: list[list[tuple[float, float]]] = []
    areas: list[tuple[str, list[_Pt]]] = []

    for act in day.activities:
        if act.kind == "buffer":
            continue
        if act.kind == "place":
            # Resolved even with the main map off: an area's own zoom map is
            # gated by the *place*, not by the day.
            nested = []
            for sub in act.activities:
                sc = r.point_coord(sub, city)
                if sc:
                    nested.append(_Pt(sub.title, sc[0], sc[1], sub))
            if main:
                coord = r.point_coord(act, city)
                hidden = act.coordinate is not None and not act.coordinate.show_on_map
                if coord is None and nested and not hidden:
                    # fall back to the centroid of the area's located sub-points
                    coord = (sum(p.lat for p in nested) / len(nested),
                             sum(p.long for p in nested) / len(nested))
                if coord:
                    main_pts.append(_Pt(act.title, coord[0], coord[1], act))
            if len(nested) >= 2 and act.show_map:
                areas.append((act.title, nested))
            continue
        if not main:
            continue
        if act.kind == "road":
            # the departure (start/coordinate) plus the waypoints, in order —
            # the last waypoint is the arrival.
            a = r.endpoint_coord(act.coordinate, act.start, city)
            line = _road_route(act, a, cache)
            if len(line) >= 2:
                routes.append(line)
                # only the departure and *named* waypoints get a node disc;
                # unnamed (route-shaping) waypoints still bend the route but
                # are not marked with their own circle.
                named = [(w.coordinate.lat, w.coordinate.long)
                         for w in act.waypoints if w.location]
                route_nodes.append(([a] if a else []) + named)
            # A drive is a route, not a pin — unless it asks for pins on its own
            # points (see Road.display_*_on_maps). They join the day's numbered
            # sequence here, in timeline order, so the numbers still read down
            # the page: the departure is the road's own pin, each pinned
            # junction/arrival is its waypoint's.
            # `start_shared_with` bows out of the sequence: the departure is the
            # previous activity's place, which is pinned already (`pin_aliases`).
            if (act.display_start_on_maps and a and act.start_shared_with is None
                    and (act.coordinate is None or act.coordinate.show_on_map)):
                main_pts.append(_Pt(act.start or act.title, a[0], a[1], act,
                                    from_road=True))
            for wp in act.pinned_waypoints():
                main_pts.append(_Pt(wp.location, wp.coordinate.lat,
                                    wp.coordinate.long, wp, from_road=True))
            continue
        coord = r.point_coord(act, city)
        if coord:
            main_pts.append(_Pt(act.title, coord[0], coord[1], act))
    return main_pts, routes, route_nodes, areas


def render_day_maps(day, itinerary, cache, ink_saver: bool = False,
                    lang: str | None = None) -> DayMaps:
    """Build the main day map and any per-area detail maps (PIL images).

    A day that set ``show_map: false`` draws no overview map — and therefore no
    pin *numbers* either, since those are that map's legend and mean nothing
    without it. Its places' zoom maps are unaffected: those answer to their own
    ``show_map``, and keep their A/B/C lettering.
    """
    show_main = bool(getattr(day, "show_map", True))
    main_pts, routes, route_nodes, area_details = resolve_day(
        day, itinerary, cache, main=show_main)
    accent = _hex_to_rgb(itinerary.cover_color)
    result = DayMaps(aliases=pin_aliases(day))

    # main map: places numbered 1..N. Points the day named twice for the same
    # place share one pin and one number (`fold_pins`), so N counts places
    # rather than mentions and the sequence still reads down the page.
    main_groups = fold_pins(main_pts)
    main_points = [(g[0].lat, g[0].long) for g in main_groups]
    main_labels = [str(i) for i in range(1, len(main_groups) + 1)]
    for i, grp in enumerate(main_groups, start=1):
        for p in grp:
            if p.act is not None:
                result.numbers[id(p.act)] = str(i)

    # the night's stay, pinned with ★
    stay = itinerary.stay_for(getattr(day, "date", None))
    if (show_main and stay is not None and stay.coordinate is not None
            and stay.coordinate.show_on_map):
        main_points.append((stay.coordinate.lat, stay.coordinate.long))
        main_labels.append(STAY_PIN)
        result.numbers[id(stay)] = STAY_PIN

    # area detail maps: pins lettered A, B, C…, folded the same way (an area is
    # small enough that two of its stops naming one place is the same story).
    area_groups = [(title, fold_pins(pts)) for title, pts in area_details]
    for _title, groups in area_groups:
        for j, grp in enumerate(groups):
            for p in grp:
                if p.act is not None:
                    result.numbers[id(p.act)] = chr(ord("A") + j)

    nodes = [c for line in route_nodes for c in line]
    # No overview map, so nothing for a leg's dotted line to be drawn on either
    # — and no `all_coords`, which is what leaves `result.main` unset below.
    legs = day_legs(day, itinerary) if show_main else []
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
                         legs=legs, lang=lang)
        result.main = RenderedMap(img, [g[0].label for g in main_groups])

    stay_coord = None
    if stay is not None and stay.coordinate is not None and stay.coordinate.show_on_map:
        stay_coord = (stay.coordinate.lat, stay.coordinate.long)

    for title, groups in area_groups:
        coords = [(g[0].lat, g[0].long) for g in groups]
        letters = [chr(ord("A") + j) for j in range(len(groups))]
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
                         ink_saver=ink_saver, labels=labels, lang=lang)
        result.areas.append((title, RenderedMap(img, [g[0].label for g in groups])))

    return result


# ----------------------------------------------------------- whole-trip map ---
# Ported from the viewer's 🗺️ Overview tab (web/src/render/tripGeo.ts): every
# day's located points and drives merged into a single map, each pin labeled with
# its **day number** rather than the day map's 1..N / ★ / A-B-C (which only mean
# something inside one day). Keep the two in step — with one deliberate
# difference, documented on `render_trip_map`: transport legs never widen the
# printed map's extent, because paper can't be zoomed out.

# A pin/drive stops driving the framing once it sits both >_FACTOR× the median
# distance from the trip's median center *and* >_FLOOR_KM away — the factor alone
# would trim a legitimate day trip out of a tight city stay, the floor alone the
# far end of a genuinely wide trip. At most _MAX_SHARE of the anchors can be
# trimmed: beyond that they are a real second cluster, not strays, and both stay
# in frame. Trimmed geometry is still *drawn*, clipped at the canvas edge — the
# alternative is zooming a whole France tour out to the Atlantic to reach the
# departure airport.
_OUTLIER_FACTOR = 6
_OUTLIER_FLOOR_KM = 400
_OUTLIER_MAX_SHARE = 1 / 3
_OUTLIER_MIN_ANCHORS = 4  # below this there is no "cluster" to speak of

# How far apart two of a day's points must be to earn their own pin, in degrees
# (~4-5 km). On paper a trip-zoom pin says only which day it is, so a city day's
# dozen sights would fan into an unreadable pinwheel of identical numbers where
# one or two dots carry the same information. The viewer keeps them all — there
# you zoom in and click a pin for its title.
_TRIP_PIN_GRID = 0.05


def _median(values: list[float]) -> float:
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def _center_of(sample):
    """``(lat, long, km per degree of longitude)`` at the sample's median point."""
    lat = _median([c[0] for c in sample])
    return (lat, _median([c[1] for c in sample]),
            _KM_PER_DEG * math.cos(math.radians(lat)))


def _km_from(center, lat: float, long: float) -> float:
    """Equirectangular km — ample for an "is this in another part of the world"
    test, and it needs no projection."""
    clat, clong, kx = center
    return math.hypot((long - clong) * kx, (lat - clat) * _KM_PER_DEG)


def resolve_trip(itinerary, cache):
    """Merge the whole trip into one map's geometry.

    Returns ``(points, labels, routes, legs)``:

    * ``points`` / ``labels`` — every day's located points, each labeled with its
      **day number**. Points closer than ``_TRIP_PIN_GRID`` share one pin *within
      a day*; a place revisited on another day keeps its own pin, since the pin
      carries the day. That night's accommodation is a point like any other — the
      trip map has no ★, since at this zoom the day number is what matters.
      A **drive's** own points are left out (`_Pt.from_road`): the drive is
      already drawn as a route here, and its departure, junctions and arrival
      would only stack more copies of the same day number along that line —
      `display_intermediate_point_on_maps` is on by default, so a multi-leg
      drive alone would have contributed several. They stay on the *day* map,
      where a numbered junction is what identifies it.
    * ``routes`` — each day's drive geometries.
    * ``legs`` — one straight ``[origin, destination]`` pair per transport leg
      with both endpoints mapped. Taken from the trip's own transport list, so an
      overnight leg is drawn once rather than on both of its day maps.

    Area detail points are skipped: an area's nested points collapse into its
    single main pin at trip zoom, where they would only add clutter.

    A day's own ``show_map`` is deliberately **not** honored here (hence the
    plain :func:`resolve_day` call): this map belongs to the trip, and its pin
    says *which day*, so dropping a day would leave a hole in the trip's shape
    rather than tidy one page. Switching off a day's overview map is a statement
    about that page.
    """
    points: list[tuple[float, float]] = []
    labels: list[str] = []
    routes: list[list[tuple[float, float]]] = []
    seen: set[tuple[str, int, int]] = set()

    for n, day in enumerate(itinerary.days, start=1):
        label = str(n)
        main, day_routes, _nodes, _areas = resolve_day(day, itinerary, cache)
        spots = [(p.lat, p.long) for p in main if not p.from_road]
        stay = itinerary.stay_for(getattr(day, "date", None))
        if stay is not None and stay.coordinate is not None and stay.coordinate.show_on_map:
            spots.append((stay.coordinate.lat, stay.coordinate.long))
        for lat, long in spots:
            key = (label, round(lat / _TRIP_PIN_GRID), round(long / _TRIP_PIN_GRID))
            if key in seen:
                continue
            seen.add(key)
            points.append((lat, long))
            labels.append(label)
        routes.extend(day_routes)

    legs = []
    for leg in itinerary.legs:
        a, b = _leg_coord(leg.start_coordinate), _leg_coord(leg.end_coordinate)
        if a and b:
            legs.append([a, b])
    return points, labels, routes, legs


def _trip_extent(points, lines):
    """The coordinates the trip map is framed on: everything but the far-off
    strays (see the ``_OUTLIER_*`` constants). Empty when nothing is located.

    ``lines`` are the drives. Each is weighed as a single unit, and counts as far
    off only when it lies *entirely* beyond the cutoff — so a drive reaching into
    the trip still counts as part of it, while a whole drive to a distant airport
    can be set aside the way one stray pin is. That matters because with maps on
    a "Manhattan → JFK" departure day is a route and no pin at all.
    """
    # The statistics come from the pins alone: route vertices are hundreds per
    # drive and would drag the center toward whichever day drove furthest. With
    # no pins at all (a trip of pure drives/legs) the vertices are all there is.
    sample = list(points) or [c for line in lines for c in line]
    if not sample:
        return []
    everything = list(points) + [c for line in lines for c in line]
    center = _center_of(sample)
    cutoff = max(_median([_km_from(center, lat, long) for lat, long in sample])
                 * _OUTLIER_FACTOR, _OUTLIER_FLOOR_KM)

    far_pin = [_km_from(center, lat, long) > cutoff for lat, long in points]
    far_line = [bool(line) and all(_km_from(center, lat, long) > cutoff
                                   for lat, long in line) for line in lines]
    anchors = len(points) + len(lines)
    far = far_pin.count(True) + far_line.count(True)
    # Trim only when there is something to set aside, enough of a trip to judge
    # against, and the far-off anchors are a small minority.
    if not (far and anchors >= _OUTLIER_MIN_ANCHORS
            and far <= anchors * _OUTLIER_MAX_SHARE):
        return everything
    # Once trimming is on it applies per *vertex*, as in the viewer: a drive
    # running from far away into the trip keeps the part that's inside the frame
    # and simply enters from off-page.
    extent = [c for c in everything if _km_from(center, c[0], c[1]) <= cutoff]
    return extent or everything


def render_trip_map(itinerary, cache, ink_saver: bool = False,
                    map_w: int = 940, map_h: int = 1240,
                    lang: str | None = None):
    """One map of the whole trip as a PIL image, or ``None`` when nothing on the
    trip is located. Portrait by default, to fill a book page.

    Same inputs as the day maps (so a warm cache makes it nearly free), same
    drawing: numbered teardrop pins, translucent accent drive routes, dotted
    transport legs.

    Like a day map, and unlike the viewer's Overview, **legs do not widen the
    extent**: an intercontinental flight would frame a France tour on the
    Atlantic and squash the trip into a corner. Its dotted line simply runs off
    the edge. On screen that's fine — you zoom out — but a page can't be zoomed,
    so the print stays framed on where the trip actually happens. Only a trip
    with nothing else locatable is framed on its legs.
    """
    points, labels, routes, legs = resolve_trip(itinerary, cache)
    extent = _trip_extent(points, routes)
    if not extent:
        extent = [c for line in legs for c in line]   # a trip of pure travel
    if not extent:
        return None
    return render_map(extent, routes, points, _hex_to_rgb(itinerary.cover_color),
                      cache.tiles, map_w=map_w, map_h=map_h, ink_saver=ink_saver,
                      labels=labels, legs=legs, lang=lang)


# ------------------------------------------------------------- hike track ---

def render_hike_map(track, accent_hex: str, cache, ink_saver: bool = False,
                    map_w: int = 900, map_h: int = 560,
                    lang: str | None = None):
    """One hike's GPX track as a PIL image, framed on the track itself.

    Unlike every other map here there is nothing to resolve: the geometry is the
    recording the itinerary carries (see ``models/gpx.py``), so no geocoding and
    no routing happen — only the basemap tiles are fetched. That is also why this
    takes a ``GpxTrack`` rather than an itinerary object.

    The trail is drawn as a route line, with a small accent disc at each end
    (a ``route_node``, the same marker a drive's named stops get). There are no
    numbered pins: on a map of one trail a pin would label the only thing on it.
    """
    if track is None or len(track.points) < 2:
        return None
    line = [(lat, long) for lat, long in track.points]
    return render_map(line, [line], [], _hex_to_rgb(accent_hex), cache.tiles,
                      map_w=map_w, map_h=map_h, ink_saver=ink_saver,
                      route_nodes=[line[0], line[-1]], lang=lang)
