"""Driving-route geometry via OSRM, cached. Falls back to a straight line.

Transient failures (network, timeout, HTTP 429/5xx, a malformed body) are
retried with a short exponential backoff; a definitive "no route" answer (or an
HTTP 4xx) is not retried. Whenever routing ultimately fails, a straight line is
drawn and a warning is logged — and the straight line is **not** cached, so a
transient blip can't poison the cache into a permanent straight line.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request

from . import USER_AGENT

logger = logging.getLogger("travelbook.maps")

# Public demo server (light use). Override with TRAVELBOOK_OSRM to point at a
# self-hosted OSRM or another provider using the same /route/v1 API.
OSRM = os.environ.get(
    "TRAVELBOOK_OSRM",
    "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson",
)

ROUTE_RETRIES = 3       # attempts on a transient failure
ROUTE_BACKOFF = 0.5     # base seconds between attempts; grows 0.5, 1.0, 2.0 …


class _Transient(Exception):
    """A retryable OSRM failure (network, timeout, HTTP 429/5xx, bad body)."""


def _request_route(coords: str) -> list[tuple[float, float]] | None:
    """One OSRM attempt. Returns the ``[(lat, long), …]`` geometry, or ``None``
    for a definitive "no route" answer (empty result, or an HTTP 4xx). Raises
    :class:`_Transient` on a retryable failure."""
    req = urllib.request.Request(OSRM.format(coords=coords),
                                 headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except urllib.error.HTTPError as exc:
        if exc.code == 429 or exc.code >= 500:
            raise _Transient(f"HTTP {exc.code}") from exc
        return None  # 4xx (e.g. malformed request): definitive, don't retry
    except Exception as exc:  # URLError, timeout, JSON decode error, …
        raise _Transient(str(exc)) from exc
    routes = data.get("routes") or []
    if not routes:
        return None  # OSRM "NoRoute" (or empty) — definitive
    geom = routes[0].get("geometry", {}).get("coordinates") or []
    line = [(lat, lon) for lon, lat in geom]
    return line if len(line) >= 2 else None


def route(a: tuple[float, float], b: tuple[float, float], cache) -> list[tuple[float, float]]:
    """Road geometry ``a``→``b`` as ``[(lat, long), …]`` (``a`` and ``b`` are
    ``(lat, long)``). Retries transient OSRM failures with backoff; returns a
    straight ``[a, b]`` (logged, never cached) when routing is unavailable or
    finds no route."""
    key = f"{a[0]:.5f},{a[1]:.5f}->{b[0]:.5f},{b[1]:.5f}"
    if cache is not None and key in cache.routes:
        return [tuple(p) for p in cache.routes[key]]
    coords = f"{a[1]},{a[0]};{b[1]},{b[0]}"  # OSRM wants lon,lat
    line: list[tuple[float, float]] | None = None
    reason = "no route found"
    for attempt in range(ROUTE_RETRIES):
        try:
            line = _request_route(coords)
            if line is None:
                reason = "OSRM returned no route"
            break  # a definitive answer (route or no-route) — stop retrying
        except _Transient as exc:
            reason = str(exc)
            if attempt < ROUTE_RETRIES - 1:
                time.sleep(ROUTE_BACKOFF * (2 ** attempt))
    if line is not None:
        if cache is not None:
            cache.routes[key] = line
        return line
    logger.warning(
        "OSRM routing %.5f,%.5f → %.5f,%.5f failed (%s); drawing a straight "
        "line instead.", a[0], a[1], b[0], b[1], reason)
    return [a, b]
