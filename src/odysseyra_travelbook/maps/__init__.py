"""Map rendering: geocoding, routing, tiles and drawing.

Public entry points: :func:`build.render_day_maps` (a day's overview + area maps),
:func:`build.render_trip_map` (one map of the whole trip) and
:func:`build.render_hike_map` (a hike's embedded GPX track). The package is only
imported when there is a map to draw — ``defaults.include_maps_in_render`` for the
first two, a hike carrying a ``gpx`` for the third — so a build with neither
touches no network and needs nothing beyond the core deps.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

USER_AGENT = "odysseyra/0.1 (per-day maps; https://github.com/Hugo-Rybinski/travelBook)"


def http_get(url: str, timeout: int = 20) -> bytes:
    """Fetch the bytes at ``url``, raising ``urllib.error.HTTPError`` on a non-2xx
    status (exactly like ``urlopen``, so callers can branch on ``.code``).

    This is the **single network seam** for the maps package — geocoding, routing
    and tiles all go through it. Native builds use ``urllib``; the browser
    (Pyodide has no sockets) overrides ``odysseyra_travelbook.maps.http_get`` with a
    ``fetch``-based implementation. Keep the contract identical in both.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def default_cache_dir() -> Path:
    """Where geocode results, routes and tiles are cached between builds."""
    env = os.environ.get("ODYSSEYRA_CACHE")
    base = Path(env) if env else Path.home() / ".cache" / "odysseyra"
    return base


@dataclass
class Cache:
    """On-disk cache for the (networked) map inputs, so re-builds are offline."""

    dir: Path
    geocode: dict = field(default_factory=dict)
    routes: dict = field(default_factory=dict)

    @classmethod
    def open(cls, directory: Path | str | None = None) -> "Cache":
        d = Path(directory) if directory else default_cache_dir()
        (d / "tiles").mkdir(parents=True, exist_ok=True)
        c = cls(dir=d)
        gp, rp = d / "geocode.json", d / "routes.json"
        if gp.exists():
            c.geocode = json.loads(gp.read_text(encoding="utf-8"))
        if rp.exists():
            c.routes = json.loads(rp.read_text(encoding="utf-8"))
        return c

    def save(self) -> None:
        (self.dir / "geocode.json").write_text(
            json.dumps(self.geocode, ensure_ascii=False), encoding="utf-8")
        (self.dir / "routes.json").write_text(
            json.dumps(self.routes, ensure_ascii=False), encoding="utf-8")

    @property
    def tiles(self) -> Path:
        return self.dir / "tiles"


from .build import (  # noqa: E402
    DayMaps,
    render_day_maps,
    render_hike_map,
    render_trip_map,
)

__all__ = ["Cache", "DayMaps", "render_day_maps", "render_hike_map",
           "render_trip_map", "default_cache_dir", "USER_AGENT", "http_get"]
