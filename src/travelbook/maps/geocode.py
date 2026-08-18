"""Geocoding via Nominatim (OSM), with a country filter and disk cache.

Nominatim is used (rather than Photon) because it supports ``countrycodes`` —
which is what ``inference_countries`` needs to keep e.g. a Kyrgyz 'Karakol' from
resolving to one in Cyprus. Only called when ``infer_coordinates_from_address``
is on; failures return ``None`` so the build degrades gracefully.
"""

from __future__ import annotations

import json
import time
import urllib.parse

from travelbook import maps as _maps  # call _maps.http_get so the browser override applies

NOMINATIM = "https://nominatim.openstreetmap.org/search"
_MIN_INTERVAL = 1.1  # Nominatim usage policy: <= 1 request/second
_last_request = [0.0]


def geocode(query: str, countries: list[str], cache) -> tuple[float, float] | None:
    """``(lat, long)`` for ``query`` (restricted to ``countries`` when set), or
    ``None``. Results — including misses — are cached on disk."""
    key = query + "|" + ",".join(sorted(countries))
    if key in cache.geocode:
        v = cache.geocode[key]
        return (v["lat"], v["long"]) if v else None

    params = {"q": query, "format": "jsonv2", "limit": 1}
    if countries:
        params["countrycodes"] = ",".join(c.lower() for c in countries)
    url = f"{NOMINATIM}?{urllib.parse.urlencode(params)}"
    # be a good citizen: never exceed ~1 req/s
    wait = _MIN_INTERVAL - (time.monotonic() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    result = None
    try:
        hits = json.loads(_maps.http_get(url).decode("utf-8"))
        if hits:
            result = (float(hits[0]["lat"]), float(hits[0]["lon"]))
    except Exception:
        result = None
    finally:
        _last_request[0] = time.monotonic()

    cache.geocode[key] = {"lat": result[0], "long": result[1]} if result else None
    return result
