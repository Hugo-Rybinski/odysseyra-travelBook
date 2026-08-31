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

__all__ = ["GpxTrack", "decode_gpx", "gpx_track", "parse_gpx"]

# The simplified map line is capped at this many points. A GPS track logs a point
# a second; at the zoom a hike map is drawn, hundreds are already more than the
# line can show, and every one of them also rides into the browser's IndexedDB
# day cache.
MAP_MAX_POINTS = 600

# Samples in the resampled elevation profile — evenly spaced by *distance*, so
# the curve's x axis is metres walked rather than seconds recorded (a rest stop
# would otherwise flatten a whole section of the chart).
PROFILE_POINTS = 120

# Elevation gain/loss is accumulated with hysteresis: a rise only counts once it
# exceeds this, so the metre-scale jitter of a barometric/GPS altimeter doesn't
# add up to hundreds of phantom metres over a long track.
_CLIMB_THRESHOLD_M = 5.0

# Half-width of the moving average smoothing the elevation series before any of
# it is measured (2 → a 5-sample window).
_SMOOTH_HALF = 2

_EARTH_R_KM = 6371.0088


@dataclass
class GpxTrack:
    """A hike's recorded track, reduced to what gets drawn.

    * ``points`` — the simplified ``(lat, long)`` line, in walking order.
    * ``profile`` — ``(km walked, elevation m)`` samples, empty when the file
      carries no elevations (plenty of hand-drawn tracks don't).
    * ``distance_km`` — measured over the *full*-resolution track, before
      simplification, so it doesn't shrink with the point count.
    * ``ascent_m`` / ``descent_m`` / ``min_elevation_m`` / ``max_elevation_m`` —
      ``None`` without elevations.
    * ``point_count`` — points in the source file, for the Edit tab's summary.
    """

    points: list[tuple[float, float]] = field(default_factory=list)
    profile: list[tuple[float, float]] = field(default_factory=list)
    distance_km: float = 0.0
    ascent_m: float | None = None
    descent_m: float | None = None
    min_elevation_m: float | None = None
    max_elevation_m: float | None = None
    point_count: int = 0

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


def _points_of(root) -> list[tuple[float, float, float | None]]:
    """``(lat, long, ele | None)`` in file order, from whichever of the three GPX
    point kinds the file uses: track points first (a recording), else route
    points (a planned route), else plain waypoints. Segments are concatenated —
    a pause in the recording is a gap in time, not in the trail."""
    for wanted in ("trkpt", "rtept", "wpt"):
        found = [e for e in root.iter() if _tag(e) == wanted]
        if not found:
            continue
        out = []
        for e in found:
            try:
                lat = float(e.get("lat"))  # type: ignore[arg-type]
                long = float(e.get("lon"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue  # a point without usable coordinates carries nothing
            ele = None
            for child in e:
                if _tag(child) == "ele" and child.text:
                    try:
                        ele = float(child.text.strip())
                    except ValueError:
                        ele = None
                    break
            out.append((lat, long, ele))
        if out:
            return out
    return []


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


# ----------------------------------------------------------------- parsing ---

def parse_gpx(text: str) -> GpxTrack:
    """Parse GPX XML into a :class:`GpxTrack`. Raises :class:`ItineraryError` on
    XML that won't parse or that holds no usable points."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ItineraryError(f"'gpx' is not parseable XML ({exc})") from exc
    raw = _points_of(root)
    if len(raw) < 2:
        raise ItineraryError(
            "'gpx' holds no track — expected at least two <trkpt>, <rtept> or "
            "<wpt> points with lat/lon"
        )

    coords = [(lat, long) for lat, long, _ in raw]
    cumulative = [0.0]
    for a, b in zip(coords, coords[1:]):
        cumulative.append(cumulative[-1] + _haversine_km(a, b))

    track = GpxTrack(
        points=_simplify(coords),
        distance_km=cumulative[-1],
        point_count=len(raw),
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
