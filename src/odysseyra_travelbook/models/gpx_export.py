"""Write a GPX file out of geometry the tool computed.

The mirror image of :mod:`.gpx`, which reads a recording *in*. What goes out here
is a **route** — a `<rte>` of `<rtept>`s — not a `<trk>` of `<trkpt>`s, and the
distinction is the point: a track says "this is where the GPS went", a route says
"this is the way to go". A drive's line comes from the router, so calling it a
track would hand a phone a recording that never happened. (Our own reader honours
the same order of precedence: track points first, then route points — see
:func:`.gpx.parse_gpx`.)

Pure stdlib, no network, no dependencies. The whole-trip GPX/KML export in the
README's backlog is the natural next user of this module: it needs the same
serializer over more geometry (a `<rte>` per drive, a `<trk>` per attached
recording, a `<wpt>` per located stop), so extend it here rather than growing a
second writer elsewhere.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

CREATOR = "Odysseyra TravelBook"


def route_gpx(points, name: str = "") -> str:
    """A GPX 1.1 document holding ``points`` — ``[(lat, long), …]`` — as one
    named route.

    Raises :class:`ValueError` on fewer than two points: a one-point "route" is
    not a way to anywhere, and every consumer (ours included) would reject it.
    """
    pts = [(float(lat), float(long)) for lat, long in points]
    if len(pts) < 2:
        raise ValueError("a route needs at least two points")
    rows = "\n".join(f'    <rtept lat="{lat:.6f}" lon="{long:.6f}"/>' for lat, long in pts)
    label = f"\n    <name>{escape(name)}</name>" if name else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<gpx version="1.1" creator="{escape(CREATOR)}" '
        'xmlns="http://www.topografix.com/GPX/1/1">\n'
        f"  <rte>{label}\n{rows}\n  </rte>\n"
        "</gpx>\n"
    )
