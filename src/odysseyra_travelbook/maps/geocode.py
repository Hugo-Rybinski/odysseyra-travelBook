"""Geocoding via Nominatim (OSM), with a country filter and disk cache.

Nominatim is used (rather than Photon) because it supports ``countrycodes`` —
which is what ``inference_countries`` needs to keep e.g. a Kyrgyz 'Karakol' from
resolving to one in Cyprus. Only called when ``infer_coordinates_from_address``
is on; failures return ``None`` so the build degrades gracefully.

Transient failures (network, timeout, HTTP 429/5xx, a malformed body) are
retried with a short exponential backoff, and a warning is logged when they
ultimately lose — the same treatment :mod:`routing` gives OSRM, and for the same
reason: **a transient failure must never be cached**. A definitive "nothing
matches that text" is worth remembering forever; "we couldn't ask" is not. One
bad second used to be written to disk as a permanent negative, and since a
missing coordinate means a missing pin, an address that failed once silently
stayed unmapped in every later build — enough of them and a day's map, or the
whole trip page, disappears while the build still reports success.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse

from odysseyra_travelbook import maps as _maps  # call _maps.http_get so the browser override applies

logger = logging.getLogger("odysseyra_travelbook.maps")

NOMINATIM = "https://nominatim.openstreetmap.org/search"
_MIN_INTERVAL = 1.1  # Nominatim usage policy: <= 1 request/second
_last_request = [0.0]

GEOCODE_RETRIES = 3     # attempts on a transient failure
GEOCODE_BACKOFF = 0.5   # base seconds between attempts; grows 0.5, 1.0, 2.0 …


class _Transient(Exception):
    """A retryable Nominatim failure (network, timeout, HTTP 429/5xx, bad body)."""


def _request(url: str) -> tuple[float, float] | None:
    """One Nominatim attempt: ``(lat, long)``, or ``None`` for a definitive "no
    match" (an empty result set, or an HTTP 4xx). Raises :class:`_Transient` on
    a retryable failure."""
    try:
        hits = json.loads(_maps.http_get(url).decode("utf-8"))
        if not hits:
            return None      # the service answered: this text matches nothing
        return (float(hits[0]["lat"]), float(hits[0]["lon"]))
    except urllib.error.HTTPError as exc:
        if exc.code == 429 or exc.code >= 500:
            raise _Transient(f"HTTP {exc.code}") from exc
        return None          # 4xx (e.g. malformed query): definitive
    except Exception as exc:  # URLError, timeout, JSON/keys/float — bad body
        raise _Transient(str(exc)) from exc


def geocode(query: str, countries: list[str], cache) -> tuple[float, float] | None:
    """``(lat, long)`` for ``query`` (restricted to ``countries`` when set), or
    ``None``.

    Definitive answers — including "no match" — are cached on disk. A transient
    failure returns ``None`` **without** caching it, so the next build asks
    again."""
    key = query + "|" + ",".join(sorted(countries))
    if cache is not None and key in cache.geocode:
        v = cache.geocode[key]
        return (v["lat"], v["long"]) if v else None

    params = {"q": query, "format": "jsonv2", "limit": 1}
    if countries:
        params["countrycodes"] = ",".join(c.lower() for c in countries)
    url = f"{NOMINATIM}?{urllib.parse.urlencode(params)}"

    reason = ""
    for attempt in range(GEOCODE_RETRIES):
        # be a good citizen: never exceed ~1 req/s, retries included
        wait = _MIN_INTERVAL - (time.monotonic() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        try:
            result = _request(url)
            break                      # a definitive answer — stop retrying
        except _Transient as exc:
            reason = str(exc)
            if attempt < GEOCODE_RETRIES - 1:
                time.sleep(GEOCODE_BACKOFF * (2 ** attempt))
        finally:
            _last_request[0] = time.monotonic()
    else:
        logger.warning(
            "Geocoding %r failed (%s); it stays unmapped this build. "
            "Not cached, so the next build will retry.", query, reason)
        return None

    if cache is not None:
        cache.geocode[key] = {"lat": result[0], "long": result[1]} if result else None
    return result
