"""Embedded GPX tracks: decode the base64 blob a hike may carry, parse its track
points, and derive the two things both renderers draw — the map line and the
elevation profile.

Pure stdlib (``base64`` + ``gzip`` + ``xml.etree``): a GPX travels *inside* the
itinerary, so a hike's profile needs no network at all and its map needs only the
basemap tiles. Nothing here reaches out.

The raw file is deliberately not kept past parsing. A recorded track is tens of
thousands of points; what the renderers need is a simplified line (a few hundred
points, visually identical at map zoom) plus a resampled profile — so that is
what :class:`GpxTrack` holds, and what reaches the browser.
"""

from __future__ import annotations

import base64
import binascii
import gzip
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from .parsers import ItineraryError

__all__ = ["GpxKmMark", "GpxTrack", "GpxWaypoint", "decode_gpx", "gpx_track",
           "parse_gpx"]

# The simplified map line is capped at this many points. A GPS track logs a point
# a second; at the zoom a hike map is drawn, hundreds are already more than the
# line can show, and every one of them also rides into the browser's IndexedDB
# day cache.
MAP_MAX_POINTS = 600

# Samples in the resampled elevation profile — evenly spaced by *distance*, so
# the curve's x axis is metres walked rather than seconds recorded (a rest stop
# would otherwise flatten a whole section of the chart).
PROFILE_POINTS = 120

# Named points kept from a file's own ``<wpt>``s, at most this many. A hand-made
# hike GPX names a handful of landmarks — the col, the lake, the refuge you turn
# at; a routing export names *every turn instruction*, dozens of them. Truncating
# the second kind would pin its first fifteen left turns, so above the cap
# **none** are kept rather than an arbitrary prefix: that many labels on a figure
# a few centimetres wide isn't a set of landmarks, it's a different kind of data.
MAX_NAMED_POINTS = 15

# A named waypoint this close to either trailhead is dropped: the start and end
# markers already mark those two points, so "Parking" printed over the start
# marker is a label saying what the marker says.
_TERMINAL_MERGE_KM = 0.05

# Distance marks along the trail, in whole kilometres — the unit a walker thinks
# in, and the unit the elevation profile's x axis already is. A long trek would
# wear more numbers than either figure can hold, so the step coarsens through
# these until the count fits: at or under 15 km every kilometre is marked, which
# covers essentially every day hike.
MAX_KM_MARKS = 15
_KM_STEPS = (1, 2, 5, 10, 20, 50, 100)

# Elevation gain/loss is accumulated with hysteresis: a rise only counts once it
# exceeds this, so the metre-scale jitter of a barometric/GPS altimeter doesn't
# add up to hundreds of phantom metres over a long track.
_CLIMB_THRESHOLD_M = 5.0

# Half-width of the moving average smoothing the elevation series before any of
# it is measured (2 → a 5-sample window).
_SMOOTH_HALF = 2

_EARTH_R_KM = 6371.0088


@dataclass(frozen=True)
class GpxWaypoint:
    """A named point along the trail — the col, the lake, the refuge you turn at.

    Read from the file's own ``<wpt name=…>``, which is what that element means:
    a ``<trkpt>`` is where you *were* and an ``<rtept>`` where you planned to go,
    while a ``<wpt>`` is a place someone thought worth naming. Both renderers
    draw it as a small marker with its name beside it.
    """

    name: str
    lat: float
    long: float


@dataclass(frozen=True)
class GpxKmMark:
    """Where a whole kilometre of walking falls on the ground.

    The trail map marks it and the elevation profile ticks it, under the *same*
    number, and that is the entire point: it says which stretch of the map the
    steep part of the chart is. Which is why the step is decided **here**, once,
    rather than per renderer — two figures numbered differently would be worse
    than two figures numbered not at all.

    ``km`` is distance *walked* (the profile's own x axis), so an out-and-back
    passes the same ground twice under two different numbers. That's the honest
    reading of both figures: at 2 km you were on the way up, at 6 km on the way
    down, and the profile says so too.

    ``bearing`` — degrees clockwise from north, the direction you were **walking
    in** here — is what makes that readable on the map: an out-and-back draws its
    two legs a few metres apart, so without it there is no telling which line is
    the way out. It is measured here, off the full-resolution track over a short
    window either side of the mark (a recorded point is a metre from its
    neighbour, so a single segment's heading is mostly GPS noise). Deliberately
    *not* left to the renderers to infer from the drawn line: the nearest point
    of a doubled-back line can be on the other leg, which is exactly the
    direction you didn't walk.
    """

    km: int
    lat: float
    long: float
    bearing: float = 0.0


@dataclass
class GpxTrack:
    """A hike's recorded track, reduced to what gets drawn.

    * ``points`` — the simplified ``(lat, long)`` line, in walking order.
    * ``waypoints`` — the file's named ``<wpt>``s (see :class:`GpxWaypoint`).
    * ``km_marks`` — the whole-kilometre distance marks both figures share
      (see :class:`GpxKmMark`).
    * ``profile`` — ``(km walked, elevation m)`` samples, empty when the file
      carries no elevations (plenty of hand-drawn tracks don't).
    * ``distance_km`` — measured over the *full*-resolution track, before
      simplification, so it doesn't shrink with the point count.
    * ``ascent_m`` / ``descent_m`` / ``min_elevation_m`` / ``max_elevation_m`` —
      ``None`` without elevations.
    * ``point_count`` — points in the source file, for the Edit tab's summary.
    * ``named_point_count`` — named ``<wpt>``s in the source file, which is
      **not** ``len(waypoints)``: above :data:`MAX_NAMED_POINTS` none are kept,
      and that is the one case where something the file said is dropped without
      a trace. The count is what lets ``validate`` say so.
    """

    points: list[tuple[float, float]] = field(default_factory=list)
    waypoints: list[GpxWaypoint] = field(default_factory=list)
    km_marks: list[GpxKmMark] = field(default_factory=list)
    profile: list[tuple[float, float]] = field(default_factory=list)
    distance_km: float = 0.0
    ascent_m: float | None = None
    descent_m: float | None = None
    min_elevation_m: float | None = None
    max_elevation_m: float | None = None
    point_count: int = 0
    named_point_count: int = 0

    @property
    def bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """``((min_lat, min_long), (max_lat, max_long))`` over the track."""
        lats = [p[0] for p in self.points]
        longs = [p[1] for p in self.points]
        return ((min(lats), min(longs)), (max(lats), max(longs)))

    @property
    def has_elevation(self) -> bool:
        return bool(self.profile)


# --------------------------------------------------------------- decoding ---

def decode_gpx(value) -> str:
    """The GPX XML text behind a hike's ``gpx`` field.

    The field is base64, since a GPX is a multi-line XML document and JSON has no
    place for one. Two conveniences on top, both for hand-built files: a
    ``data:`` URI prefix is stripped, and a gzip-compressed payload is
    transparently inflated — a track compresses about tenfold, which is the
    difference between a JSON you can open and one you can't.
    """
    if not isinstance(value, str):
        raise ItineraryError("'gpx' must be a base64 string holding a GPX file")
    text = value.strip()
    if text.startswith("data:"):
        _, _, text = text.partition(",")
    # Line-wrapped base64 (as `base64` the command outputs it) is fine.
    text = "".join(text.split())
    if not text:
        raise ItineraryError("'gpx' is empty — expected a base64-encoded GPX file")
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ItineraryError(
            f"'gpx' is not valid base64 ({exc}) — encode the .gpx file with base64"
        ) from exc
    if raw[:2] == b"\x1f\x8b":  # gzip magic
        try:
            raw = gzip.decompress(raw)
        except OSError as exc:
            raise ItineraryError(f"'gpx' is gzip data but won't inflate ({exc})") from exc
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ItineraryError(
            "'gpx' does not decode as UTF-8 text — is it really a GPX file?"
        ) from exc


def _tag(elem) -> str:
    """An element's local name, namespace stripped. GPX 1.0 and 1.1 use different
    namespaces and plenty of files in the wild use none, so nothing here matches
    on one."""
    return elem.tag.rsplit("}", 1)[-1] if isinstance(elem.tag, str) else ""


def _coord_of(e) -> tuple[float, float] | None:
    try:
        return (float(e.get("lat")), float(e.get("lon")))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None  # a point without usable coordinates carries nothing


def _child_text(e, tag: str) -> str:
    for child in e:
        if _tag(child) == tag and child.text:
            return child.text.strip()
    return ""


def _points_of(root) -> tuple[str, list[tuple[float, float, float | None]]]:
    """``(kind, [(lat, long, ele | None), …])`` in file order, from whichever of
    the three GPX point kinds the file uses: track points first (a recording),
    else route points (a planned route), else plain waypoints. Segments are
    concatenated — a pause in the recording is a gap in time, not in the trail.

    The ``kind`` that won is returned because it decides whether the file's
    ``<wpt>``s are *landmarks* or the trail itself (see
    :func:`_named_waypoints`). ``("", [])`` when nothing is usable.
    """
    for wanted in ("trkpt", "rtept", "wpt"):
        found = [e for e in root.iter() if _tag(e) == wanted]
        if not found:
            continue
        out = []
        for e in found:
            coord = _coord_of(e)
            if coord is None:
                continue
            text = _child_text(e, "ele")
            try:
                ele = float(text) if text else None
            except ValueError:
                ele = None
            out.append((coord[0], coord[1], ele))
        if out:
            return wanted, out
    return "", []


def _named_waypoints(root, kind: str, line: list[tuple[float, float]]
                     ) -> list[GpxWaypoint]:
    """The file's ``<wpt>``s that carry a ``<name>``, as :class:`GpxWaypoint`s.

    Three filters, each of them the point of the field rather than tidiness:

    * **only ``<wpt>``, and only a named one.** An unnamed waypoint says nothing
      the line already drawn doesn't, and there is no label to print beside it.
    * **none at all when the line came out of the waypoints** (``kind == "wpt"``
      — a file with no track and no route): those points *are* the trail, so
      pinning each would label every bend of it.
    * **none within** :data:`_TERMINAL_MERGE_KM` of either trailhead, which the
      start/end markers already mark.

    The :data:`MAX_NAMED_POINTS` cap is applied by the caller, which keeps the
    pre-cap count for ``validate`` to report.
    """
    if kind == "wpt":
        return []
    out = []
    ends = (line[0], line[-1]) if line else ()
    for e in root.iter():
        if _tag(e) != "wpt":
            continue
        coord = _coord_of(e)
        name = _child_text(e, "name")
        if coord is None or not name:
            continue
        if any(_haversine_km(coord, end) <= _TERMINAL_MERGE_KM for end in ends):
            continue
        out.append(GpxWaypoint(name=name, lat=coord[0], long=coord[1]))
    return out


# ------------------------------------------------------------ measurement ---

def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = (math.sin(dlat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return 2 * _EARTH_R_KM * math.asin(math.sqrt(min(1.0, h)))


def _smooth(values: list[float]) -> list[float]:
    """A moving average over the elevation series, so measurement noise isn't
    mistaken for terrain (see ``_SMOOTH_HALF``)."""
    n = len(values)
    if n <= 2 * _SMOOTH_HALF:
        return list(values)
    out = []
    for i in range(n):
        lo = max(0, i - _SMOOTH_HALF)
        hi = min(n, i + _SMOOTH_HALF + 1)
        out.append(sum(values[lo:hi]) / (hi - lo))
    return out


def _climb(eles: list[float]) -> tuple[float, float]:
    """``(ascent, descent)`` in metres, accumulated with hysteresis: the running
    reference only moves once the series has climbed (or dropped) more than
    ``_CLIMB_THRESHOLD_M``, so a flat traverse reads as flat instead of totalling
    up its own jitter."""
    gain = loss = 0.0
    ref = eles[0]
    for e in eles[1:]:
        d = e - ref
        if d >= _CLIMB_THRESHOLD_M:
            gain += d
            ref = e
        elif d <= -_CLIMB_THRESHOLD_M:
            loss -= d
            ref = e
    return gain, loss


def _simplify(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Ramer–Douglas–Peucker down to ``MAP_MAX_POINTS``, doubling the tolerance
    until it fits. Starting from ~1 m keeps a faithful line for the short tracks
    that are already small enough, and a recorded track's collinear runs collapse
    long before the shape does."""
    if len(points) <= MAP_MAX_POINTS:
        return list(points)
    tol = 1e-5  # degrees, ~1.1 m of latitude
    reduced = list(points)
    for _ in range(24):
        reduced = _rdp(points, tol)
        if len(reduced) <= MAP_MAX_POINTS:
            break
        tol *= 2
    return reduced


def _rdp(points: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    """Ramer–Douglas–Peucker, iteratively (a recorded track is deep enough to
    blow the recursion limit). Distances are in degrees — fine for a within-a-day
    trail, where the aspect distortion is a fraction of the tolerance."""
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        worst, index = -1.0, first
        ax, ay = points[first]
        bx, by = points[last]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        for i in range(first + 1, last):
            px, py = points[i]
            if norm == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > worst:
                worst, index = d, i
        if worst > tol:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return [p for p, k in zip(points, keep) if k]


def _profile(cumulative: list[float], eles: list[float]) -> list[tuple[float, float]]:
    """``(km, m)`` samples evenly spaced along the track's length, linearly
    interpolated between the two neighbouring recordings."""
    total = cumulative[-1]
    if total <= 0:
        return [(0.0, round(eles[0], 1))]
    out = []
    j = 0
    for i in range(PROFILE_POINTS):
        target = total * i / (PROFILE_POINTS - 1)
        while j < len(cumulative) - 2 and cumulative[j + 1] < target:
            j += 1
        span = cumulative[j + 1] - cumulative[j]
        f = 0.0 if span <= 0 else (target - cumulative[j]) / span
        ele = eles[j] + (eles[j + 1] - eles[j]) * f
        out.append((round(target, 3), round(ele, 1)))
    return out


# Half-window used to measure a distance mark's walking direction, in km. A
# recorded point sits a metre or two from its neighbour, so one segment's heading
# is mostly noise; 30 m either side is a heading.
_BEARING_WINDOW_KM = 0.03


def _bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Degrees clockwise from north, ``a`` → ``b``. Planar (the longitude scaled
    by the latitude's cosine), which at a hike's scale is exact enough for an
    arrowhead."""
    kx = math.cos(math.radians((a[0] + b[0]) / 2))
    return math.degrees(math.atan2((b[1] - a[1]) * kx, b[0] - a[0])) % 360.0


def _at_km(cumulative: list[float], coords: list[tuple[float, float]],
           at: float) -> tuple[float, float]:
    """The point ``at`` km along the track, interpolated between recordings."""
    at = min(max(at, 0.0), cumulative[-1])
    j = 0
    while j < len(cumulative) - 2 and cumulative[j + 1] < at:
        j += 1
    span = cumulative[j + 1] - cumulative[j]
    f = 0.0 if span <= 0 else (at - cumulative[j]) / span
    (lat1, long1), (lat2, long2) = coords[j], coords[j + 1]
    return (lat1 + (lat2 - lat1) * f, long1 + (long2 - long1) * f)


def _km_marks(cumulative: list[float],
              coords: list[tuple[float, float]]) -> list[GpxKmMark]:
    """The whole-kilometre marks, placed on the ground by walking the same
    cumulative distances the profile is resampled from.

    Marks stop **short of the total**: one landing on the finish would print a
    number over the marker that already says the trail ends there, and the
    figure states the full length on its axis anyway.
    """
    total = cumulative[-1]
    step = next((s for s in _KM_STEPS if total / s <= MAX_KM_MARKS), _KM_STEPS[-1])
    out: list[GpxKmMark] = []
    mark = step
    while mark < total:
        here = _at_km(cumulative, coords, mark)
        behind = _at_km(cumulative, coords, mark - _BEARING_WINDOW_KM)
        ahead = _at_km(cumulative, coords, mark + _BEARING_WINDOW_KM)
        out.append(GpxKmMark(km=mark, lat=here[0], long=here[1],
                             bearing=round(_bearing(behind, ahead), 1)))
        mark += step
    return out


# ----------------------------------------------------------------- parsing ---

def parse_gpx(text: str) -> GpxTrack:
    """Parse GPX XML into a :class:`GpxTrack`. Raises :class:`ItineraryError` on
    XML that won't parse or that holds no usable points."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ItineraryError(f"'gpx' is not parseable XML ({exc})") from exc
    kind, raw = _points_of(root)
    if len(raw) < 2:
        raise ItineraryError(
            "'gpx' holds no track — expected at least two <trkpt>, <rtept> or "
            "<wpt> points with lat/lon"
        )

    coords = [(lat, long) for lat, long, _ in raw]
    cumulative = [0.0]
    for a, b in zip(coords, coords[1:]):
        cumulative.append(cumulative[-1] + _haversine_km(a, b))

    named = _named_waypoints(root, kind, coords)
    track = GpxTrack(
        points=_simplify(coords),
        # Above the cap **none** are kept, rather than an arbitrary prefix — see
        # MAX_NAMED_POINTS. The count survives either way, so `validate` can say
        # that a file naming forty turns had all forty left off the map.
        waypoints=named if len(named) <= MAX_NAMED_POINTS else [],
        km_marks=_km_marks(cumulative, coords),
        distance_km=cumulative[-1],
        point_count=len(raw),
        named_point_count=len(named),
    )

    # Elevations are all-or-nothing: a file that gives them for only some points
    # would make every derived figure a guess, so a gap means no profile.
    eles = [e for _, _, e in raw]
    if all(e is not None for e in eles):
        smoothed = _smooth([float(e) for e in eles])  # type: ignore[arg-type]
        ascent, descent = _climb(smoothed)
        track.profile = _profile(cumulative, smoothed)
        track.ascent_m = ascent
        track.descent_m = descent
        track.min_elevation_m = min(smoothed)
        track.max_elevation_m = max(smoothed)
    return track


def gpx_track(value) -> GpxTrack:
    """A hike's ``gpx`` field (base64, optionally gzipped) as a
    :class:`GpxTrack`. Raises :class:`ItineraryError` on anything unusable."""
    return parse_gpx(decode_gpx(value))
