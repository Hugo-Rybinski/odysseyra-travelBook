"""Per-day map rendering: geocoding, routing, tiles and drawing.

Public entry point: :func:`build.render_day_maps`. The whole package is only
imported when ``defaults.include_maps_in_render`` is on, so a build with maps off
touches no network and needs nothing beyond the core deps.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

USER_AGENT = "travelbook/0.1 (per-day maps; https://github.com/Hugo-Rybinski/travelBook)"


def default_cache_dir() -> Path:
    """Where geocode results, routes and tiles are cached between builds."""
    env = os.environ.get("TRAVELBOOK_CACHE")
    base = Path(env) if env else Path.home() / ".cache" / "travelbook"
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


from .build import DayMaps, render_day_maps  # noqa: E402

__all__ = ["Cache", "DayMaps", "render_day_maps", "default_cache_dir", "USER_AGENT"]
