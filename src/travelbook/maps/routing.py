"""Driving-route geometry via OSRM, cached. Falls back to a straight line."""

from __future__ import annotations

import json
import os
import urllib.request

from . import USER_AGENT

# Public demo server (light use). Override with TRAVELBOOK_OSRM to point at a
# self-hosted OSRM or another provider using the same /route/v1 API.
OSRM = os.environ.get(
    "TRAVELBOOK_OSRM",
    "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson",
)


def route(a: tuple[float, float], b: tuple[float, float], cache) -> list[tuple[float, float]]:
    """Road geometry ``a``→``b`` as ``[(lat, long), …]`` (``a`` and ``b`` are
    ``(lat, long)``). Returns a straight ``[a, b]`` if routing is unavailable."""
    key = f"{a[0]:.5f},{a[1]:.5f}->{b[0]:.5f},{b[1]:.5f}"
    if cache is not None and key in cache.routes:
        return [tuple(p) for p in cache.routes[key]]
    coords = f"{a[1]},{a[0]};{b[1]},{b[0]}"  # OSRM wants lon,lat
    line: list[tuple[float, float]] = []
    try:
        req = urllib.request.Request(OSRM.format(coords=coords),
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as r:
            geom = json.load(r)["routes"][0]["geometry"]["coordinates"]
        line = [(lat, lon) for lon, lat in geom]
    except Exception:
        line = []
    result = line if len(line) >= 2 else [a, b]
    if cache is not None:
        cache.routes[key] = result
    return result
