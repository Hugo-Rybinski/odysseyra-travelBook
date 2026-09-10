"""Write a GPX file out of geometry the tool computed.

The mirror image of :mod:`.gpx`, which reads a recording *in*. The distinction
that shapes this module is **route vs. track**: a `<trk>` says "this is where
the GPS went", a `<rte>` says "this is the way to go". A drive's line comes from
the router, so calling it a track would hand a phone a recording that never
happened — while a hike's line came out of a real recording and is a track.
Both go through the same writer here, and each caller says which it has.
(Our own reader honours the same order of precedence: track points first, then
route points — see :func:`.gpx.parse_gpx`. So a document holding both reads back
as its tracks.)

Pure stdlib, no network, no dependencies. Everything that serializes geometry
belongs here rather than in a second writer elsewhere: :func:`route_gpx` is the
viewer's *(Build GPX file)* link (one leg of one drive), and
:func:`gpx_document` is what :mod:`..gpx_bundle` assembles the whole-trip and
per-day files from. The KML half of the README's backlog is the next such
caller.
"""

from __future__ import annotations

from typing import NamedTuple, Sequence
from xml.sax.saxutils import escape

CREATOR = "Odysseyra TravelBook"

__all__ = ["CREATOR", "GpxLine", "GpxPoint", "gpx_document", "route_gpx"]


class GpxPoint(NamedTuple):
    """One `<wpt>`: a named place worth marking on its own."""

    lat: float
    long: float
    name: str = ""
    desc: str = ""


class GpxLine(NamedTuple):
    """One `<rte>` or `<trk>` — which of the two is decided by the caller, not by
    this type: the same shape of geometry is a route when we computed it and a
    track when a GPS recorded it."""

    points: Sequence[tuple[float, float]]
    name: str = ""
    desc: str = ""


def _tag(name: str, value: str, indent: str) -> str:
    return f"{indent}<{name}>{escape(value)}</{name}>\n" if value else ""


def _point(tag: str, lat: float, long: float, indent: str) -> str:
    return f'{indent}<{tag} lat="{float(lat):.6f}" lon="{float(long):.6f}"/>\n'


def _waypoint(p: GpxPoint, indent: str) -> str:
    """A `<wpt>`, self-closing when it carries nothing but its position."""
    inner = indent + "  "
    body = _tag("name", p.name, inner) + _tag("desc", p.desc, inner)
    if not body:
        return _point("wpt", p.lat, p.long, indent)
    head = f'{indent}<wpt lat="{float(p.lat):.6f}" lon="{float(p.long):.6f}">\n'
    return f"{head}{body}{indent}</wpt>\n"


def _line(tag: str, line: GpxLine, indent: str) -> str:
    """A `<rte>` or a `<trk>` (whose points sit in one `<trkseg>`)."""
    pts = [(float(lat), float(long)) for lat, long in line.points]
    if len(pts) < 2:
        raise ValueError("a route needs at least two points")
    inner = indent + "  "
    body = _tag("name", line.name, inner) + _tag("desc", line.desc, inner)
    if tag == "trk":
        rows = "".join(_point("trkpt", lat, long, inner + "  ") for lat, long in pts)
        body += f"{inner}<trkseg>\n{rows}{inner}</trkseg>\n"
    else:
        body += "".join(_point("rtept", lat, long, inner) for lat, long in pts)
    return f"{indent}<{tag}>\n{body}{indent}</{tag}>\n"


def gpx_document(
    name: str = "",
    *,
    waypoints: Sequence[GpxPoint] = (),
    routes: Sequence[GpxLine] = (),
    tracks: Sequence[GpxLine] = (),
) -> str:
    """A GPX 1.1 document holding any mix of waypoints, routes and tracks.

    The elements are emitted in the order the schema fixes — ``metadata``,
    ``wpt*``, ``rte*``, ``trk*`` — whatever order the arguments arrive in, since
    a file that lists them otherwise is rejected by strict readers.

    A route or track with fewer than two points raises :class:`ValueError`: a
    one-point line is not a way to anywhere, and every consumer (ours included)
    would reject it. There is deliberately **no timestamp**: nothing here was
    recorded at a moment, and a stamped file would differ on every export.
    """
    body = (
        (f"  <metadata>\n{_tag('name', name, '    ')}  </metadata>\n" if name else "")
        + "".join(_waypoint(p, "  ") for p in waypoints)
        + "".join(_line("rte", r, "  ") for r in routes)
        + "".join(_line("trk", t, "  ") for t in tracks)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<gpx version="1.1" creator="{escape(CREATOR)}" '
        'xmlns="http://www.topografix.com/GPX/1/1">\n'
        f"{body}"
        "</gpx>\n"
    )


def route_gpx(points, name: str = "") -> str:
    """A GPX 1.1 document holding ``points`` — ``[(lat, long), …]`` — as one
    named **route**. The single-line case, used by the viewer's *(Build GPX
    file)* link; see :func:`gpx_document` for the rest."""
    return gpx_document(routes=[GpxLine(points, name)])
