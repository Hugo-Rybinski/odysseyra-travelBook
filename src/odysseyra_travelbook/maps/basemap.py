"""Basemap drawing: Carto's vector tiles rendered to an image with Pillow.

The second half of the vector path (:mod:`mvt` is the first): decoded features
in, a pale Positron-like basemap out, plus the place labels as *data* for the
caller to draw last.

**Why we rasterize the basemap ourselves.** Carto's pre-rendered raster tiles
now answer keyless requests with an ``API KEY REQUIRED`` watermark — served with
an HTTP 200, so nothing could detect it — while the *vector* tiles behind the
web viewer's MapLibre map are still open. Those are the tiles this module draws,
from the same URL template ``web/src/maps/carto.ts`` pins, so the two renderers
finally read the same source: the browser's service worker has often already
cached the very tile a static render is about to ask for.

**It is a deliberate subset of Positron, not a port of it.** The real style is
93 layers; a map figure a few centimetres wide needs about fifteen. Colours and
per-zoom widths below are lifted from ``positron-gl-style/style.json`` so the
result reads as the same basemap, but bridges/tunnels aren't distinguished from
plain roads, buildings and POIs aren't drawn at all, and road *names* are
skipped — at this size they were clutter, and the place names are what orient a
reader. Two things are consequently better than the raster path, not worse:
labels are drawn in the book's own typeface and can dodge our pins, and a map
costs one tile fetch per tile instead of two (the old base + labels-only
sandwich).

Zoom 14 is the deepest the source publishes, so anything closer is drawn by
overzooming those tiles — exactly what MapLibre does in the viewer, which is why
the two stay consistent past z14.
"""

from __future__ import annotations

import logging
import math
import time
import urllib.error
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from odysseyra_travelbook import maps as _maps  # call _maps.http_get so the browser override applies

from . import mvt

logger = logging.getLogger("odysseyra_travelbook.maps")

# The same host and template the viewer pins in web/src/maps/carto.ts. Carto's
# TileJSON shards over tiles-a/b/c/d; pinning one keeps the URLs identical
# between the two renderers, which is what lets the browser's service-worker
# cache serve a static render's tiles.
VECTOR_URL = "https://tiles-a.basemaps.cartocdn.com/vectortiles/carto.streets/v1/{z}/{x}/{y}.mvt"
MAX_ZOOM = 14          # the source's deepest zoom; past it we overzoom
TILE = 256             # logical slippy-map tile size (projection unit)

# Only these layers are decoded; `poi` and `housenumber` are skipped by their
# length prefix, which on a city tile is most of the payload (13 of every 16
# features). `building` is kept but only drawn close in — see BUILDING_MIN_ZOOM.
LAYERS = frozenset({
    "water", "waterway", "landcover", "landuse", "park", "boundary",
    "transportation", "building", "place", "water_name",
})

# An area map is a few city blocks, which is exactly where footprints stop being
# noise and start being the thing you navigate by. Positron fades them in around
# here too; below it they'd be a grey smear.
BUILDING_MIN_ZOOM = 14

TILE_RETRIES = 3      # attempts on a transient tile failure
TILE_BACKOFF = 0.4    # base seconds between attempts; grows 0.4, 0.8, 1.6 …

# Supersampling budget. Pillow strokes are aliased, so the basemap is drawn
# large and reduced — but the whole-trip page is already 1880×2480 device
# pixels, and quadrupling that is a 56 MB canvas the browser build would feel.
# Past the budget the extra sampling is dropped rather than the map.
MAX_SS_PIXELS = 12_000_000


# ------------------------------------------------------------------ palette ---
# Straight out of positron-gl-style. Where the style used a translucent fill we
# keep the alpha, so overlapping landuse stacks the way it does in the viewer.
BACKGROUND = (250, 250, 248)
GREEN = (234, 241, 233, 128)          # landcover / parks / cemeteries …
RESIDENTIAL = (237, 237, 237, 90)
WATER = (212, 218, 220, 255)
WATERWAY = (209, 219, 223, 255)
BOUNDARY_COUNTRY = (235, 214, 216, 255)
BOUNDARY_REGION = (234, 213, 215, 255)
ROAD_CASE_FAR = (230, 230, 230, 255)   # Positron lightens the casing below z12
ROAD_CASE_NEAR = (221, 221, 221, 255)
ROAD_FILL = (255, 255, 255, 255)
ROAD_FILL_MINOR = (253, 253, 253, 255)
PATH = (213, 213, 213, 255)
RAIL = (221, 221, 221, 255)
BUILDING = (237, 237, 237, 255)
BUILDING_EDGE = (223, 223, 223, 255)

LABEL_PLACE = (85, 85, 85)
LABEL_WATER = (122, 150, 160)
LABEL_HALO = (250, 250, 248)

_LANDUSE_GREEN = frozenset({
    "cemetery", "stadium", "pitch", "playground", "track", "hospital",
    "school", "university", "college", "kindergarten", "zoo",
})

# Roads, smallest class first so a motorway's casing wins at a junction — the
# order Positron stacks them in. Widths are its per-zoom stops (the plain,
# non-ramp variants); the first stop doubles as the layer's minimum zoom.
_ROADS: tuple[tuple[tuple[str, ...], tuple[tuple[float, float], ...], tuple[tuple[float, float], ...]], ...] = (
    (("service",),
     ((15, 1), (16, 3), (17, 6), (18, 8)),
     ((15, 2), (16, 2), (17, 4), (18, 6))),
    (("minor",),
     ((11, 0.5), (12, 0.5), (14, 2), (15, 3), (16, 4.3), (17, 10), (18, 14)),
     ((15, 3), (16, 4), (17, 8), (18, 12))),
    (("secondary", "tertiary"),
     ((11, 0.5), (12, 1.5), (13, 3), (14, 5), (15, 6), (16, 8), (17, 12), (18, 16)),
     ((13, 2), (14, 3), (15, 4), (16, 6), (17, 10), (18, 14))),
    (("primary",),
     ((7, 0.8), (8, 1), (11, 3), (13, 4), (14, 6), (15, 8), (16, 10), (17, 14), (18, 18)),
     ((10, 0.3), (13, 2), (14, 4), (15, 6), (16, 8), (17, 12), (18, 16))),
    (("trunk",),
     ((5, 0.5), (7, 0.8), (8, 1), (11, 3), (13, 4), (14, 6), (15, 8), (16, 10), (17, 14), (18, 18)),
     ((11, 1), (13, 2), (14, 4), (15, 6), (16, 8), (17, 12), (18, 16))),
    (("motorway",),
     ((5, 0.5), (7, 0.7), (8, 0.8), (11, 3), (12, 4), (13, 5), (14, 7), (15, 9), (16, 11), (17, 13)),
     ((10, 1), (12, 2), (13, 3), (14, 5), (15, 7), (16, 9), (17, 11))),
)
_PATH_WIDTHS = ((15, 0.5), (16, 1), (18, 3))
_RAIL_WIDTHS = ((13, 0.5), (14, 1), (15, 1), (16, 3))
_WATERWAY_WIDTHS = ((8, 0.5), (9, 1), (15, 2), (16, 3))
_BOUNDARY_COUNTRY_WIDTHS = ((3, 1), (6, 1.5))
_BOUNDARY_REGION_WIDTHS = ((4, 0.5), (7, 1))

# Place labels: size in logical pixels, and how they sort against each other
# when two would collide. A capital outranks a hamlet whatever their OSM rank.
#
# `state`/`province` are deliberately absent. They earn little on a trip map —
# the country and the towns do the orienting — and OSM's `name:en` for a region
# is often a literal gloss: Bourgogne-Franche-Comté came out as "BURGUNDY-FREE
# COUNTY", Pays de la Loire as "PAYS OF THE LOIRE". A name nobody calls the
# place is worse than no name.
_PLACE_KINDS: dict[str, tuple[int, float, bool]] = {
    # class:        (priority, size, uppercase)
    "country":      (0, 12.5, True),
    "city":         (2, 13.5, False),
    "town":         (3, 11.5, False),
    "village":      (4, 10.0, False),
    "island":       (5, 10.0, False),
    "suburb":       (6, 9.5, False),
    "hamlet":       (6, 9.5, False),
    "locality":     (6, 9.5, False),
    "neighbourhood": (7, 9.0, False),
}
MAX_LABELS = 60        # candidates considered; collision then thins them out


@dataclass(frozen=True, slots=True)
class Label:
    """One basemap label, positioned in **device** pixels, for the caller to draw
    after its own overlays (so a place name can be dropped where a pin sits)."""

    text: str
    x: float
    y: float
    size: float          # font size in device pixels
    color: tuple[int, int, int]
    italic: bool
    priority: tuple[int, float]


# -------------------------------------------------------------------- fetch ---
def tile_bytes(url: str) -> bytes:
    """One tile's bytes, retrying transient failures (network, timeout, HTTP
    429/5xx) with a short backoff — the same treatment routing gives OSRM.

    A map is stitched from several tiles and any single failure loses the whole
    image (the caller swallows it), so one rate-limited tile in a burst would
    silently cost a day's map — or, for the whole-trip map, a whole page.

    A **404 is not a failure**: a vector-tile server answers it for a tile that
    holds no features, which over empty country (a high-altitude lake in
    Kyrgyzstan, a stretch of desert) is the honest answer rather than an error.
    Raising there cost the whole image for want of one blank square — the map
    that most needs drawing, since a trail out in the middle of nowhere is
    exactly where the tiles run out. It comes back as no bytes, which
    :func:`mvt.decode` reads as no layers, so the square draws as bare
    background. Every other 4xx still raises: those say the *request* is wrong
    (a bad URL, a moved endpoint, a key now required), which must not degrade
    into a book of blank maps.

    That reading needs the status, which the **browser doesn't get** — Carto
    sends no CORS header on a 404, so the response is blocked and the shim only
    sees a network error. :func:`render_basemap` is where that case is caught,
    by asking whether the source answered at all rather than what this one
    square said; see its comment."""
    last: Exception | None = None
    for attempt in range(TILE_RETRIES):
        try:
            return _maps.http_get(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return b""      # an empty tile, not a failure
            if not (exc.code == 429 or exc.code >= 500):
                raise           # 4xx: definitive (bad URL, moved, …)
            last = exc
        except Exception as exc:  # URLError, timeout, the browser's fetch shim …
            last = exc
        if attempt < TILE_RETRIES - 1:
            time.sleep(TILE_BACKOFF * (2 ** attempt))
    raise last  # type: ignore[misc]


def fetch_tile(z: int, x: int, y: int, tiles_dir: Path) -> dict[str, mvt.Layer]:
    """The decoded layers of one vector tile, caching the raw tile on disk.

    The cached file keeps the wire bytes rather than the decode, so a warm cache
    is byte-identical to what the network served and stays valid across changes
    to which layers we draw. An empty tile caches as an empty file — a rebuild
    over blank country then costs no request at all."""
    f = tiles_dir / f"vec_{z}_{x}_{y}.mvt"
    if not f.exists():
        f.write_bytes(tile_bytes(VECTOR_URL.format(z=z, x=x, y=y)))
    return mvt.decode(f.read_bytes(), LAYERS)


# ------------------------------------------------------------------ helpers ---
def width_at(stops: tuple[tuple[float, float], ...], z: float) -> float | None:
    """A style width interpolated at zoom ``z``; ``None`` below its first stop.

    Positron gives most layers a per-zoom ramp plus a minzoom; the first stop
    stands in for the minzoom, which is what makes a z6 map show motorways and
    nothing else."""
    if z < stops[0][0]:
        return None
    prev_z, prev_w = stops[0]
    for sz, sw in stops[1:]:
        if z <= sz:
            span = sz - prev_z
            t = 0.0 if span <= 0 else (z - prev_z) / span
            return prev_w + (sw - prev_w) * t
        prev_z, prev_w = sz, sw
    return prev_w


def _road_class(props: dict) -> str:
    """A road's class, with OpenMapTiles' ``…_construction`` variants folded onto
    the finished road — a road being built still reads as a road on paper."""
    cls = props.get("class")
    if not isinstance(cls, str):
        return ""
    return cls[:-len("_construction")] if cls.endswith("_construction") else cls


def _ss_for(width: int, height: int) -> int:
    return 2 if width * height * 4 <= MAX_SS_PIXELS else 1


def _place_name(props: dict, lang: str | None) -> str:
    """A place's name for the book's language, falling back to the Latin
    transliteration and then to the local name.

    The raster tiles had the name burnt in, always local — a French book called
    Spain ``ESPAÑA`` and a Kyrgyz lake ``Ысык-Көл``. Now that the label is data,
    the same trip prints ``Espagne`` or ``Spain``. ``name:latin`` is Positron's
    own fallback, and the last resort is what OSM carries locally.
    """
    for key in ((f"name:{lang}",) if lang else ()) + ("name:latin", "name"):
        v = props.get(key)
        if isinstance(v, str) and v:
            return v
    return ""


# ------------------------------------------------------------------- drawing ---
class _Painter:
    """Draws one canvas from a set of decoded tiles.

    Holds the projection from a tile's local grid to canvas pixels: a tile at
    ``(zsrc, tx, ty)`` with extent ``E`` covers ``TILE * k`` logical pixels of
    the render zoom, where ``k`` is 1 unless we're overzooming past the source's
    deepest level.
    """

    def __init__(self, z, left, top, map_w, map_h, scale, ss):
        self.zsrc = min(z, MAX_ZOOM)
        self.k = 2 ** (z - self.zsrc)
        self.z = z
        self.left, self.top = left, top
        self.px = scale * ss
        self.w = int(map_w * scale * ss)
        self.h = int(map_h * scale * ss)
        self.img = Image.new("RGB", (self.w, self.h), BACKGROUND)
        self.d = ImageDraw.Draw(self.img, "RGBA")

    def _frame(self, tx: int, ty: int, extent: int):
        """``(ax, ay, unit)`` mapping a tile-local coordinate to canvas pixels."""
        span = TILE * self.k
        unit = span / extent * self.px
        ax = (tx * span - self.left) * self.px
        ay = (ty * span - self.top) * self.px
        return ax, ay, unit

    # Rejecting an off-canvas feature before projecting it is what makes deep
    # overzoom cheap: at z17 a z14 tile is 8× wider than the canvas, so most of
    # its geometry never needs touching.
    def _visible(self, ring, ax, ay, unit) -> bool:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        x0, x1 = ax + min(xs) * unit, ax + max(xs) * unit
        y0, y1 = ay + min(ys) * unit, ay + max(ys) * unit
        m = 4 * self.px
        return x1 >= -m and x0 <= self.w + m and y1 >= -m and y0 <= self.h + m

    def _project(self, ring, ax, ay, unit):
        return [(ax + x * unit, ay + y * unit) for x, y in ring]

    def fills(self, tiles, layer, colour, match=None, outline=None):
        for (tx, ty), tile in tiles:
            lay = tile.get(layer)
            if not lay:
                continue
            ax, ay, unit = self._frame(tx, ty, lay.extent)
            for ft in lay.features:
                if ft.kind != mvt.POLYGON or (match and not match(ft.props)):
                    continue
                self._polygon(ft, ax, ay, unit, colour, outline)

    def _polygon(self, ft, ax, ay, unit, colour, outline=None):
        rings = [r for r in ft.rings if len(r) >= 3 and self._visible(r, ax, ay, unit)]
        if not rings:
            return
        if len(rings) == 1:
            self.d.polygon(self._project(rings[0], ax, ay, unit), fill=colour,
                           outline=outline)
            return
        # More than one ring: some may be holes (a lake with an island in it).
        # Split on winding order; several exteriors and no hole is just a
        # multipolygon and stays cheap.
        outer = [r for r in rings if mvt.ring_is_exterior(r)]
        inner = [r for r in rings if not mvt.ring_is_exterior(r)]
        if not inner or not outer:
            for r in rings:
                self.d.polygon(self._project(r, ax, ay, unit), fill=colour)
            return
        self._holed(outer, inner, ax, ay, unit, colour)

    def _holed(self, outer, inner, ax, ay, unit, colour):
        """Fill exteriors minus holes, through a mask.

        Painting the hole in a background colour would be wrong — whatever was
        drawn underneath should show through — so this needs a real mask. It is
        cut to the polygon's own bounding box: a canvas-sized mask per lake was
        the difference between a map that renders and one that crawls.
        """
        polys = [self._project(r, ax, ay, unit) for r in outer]
        holes = [self._project(r, ax, ay, unit) for r in inner]
        xs = [x for p in polys for x, _ in p]
        ys = [y for p in polys for _, y in p]
        x0, y0 = max(0, int(min(xs)) - 1), max(0, int(min(ys)) - 1)
        x1, y1 = min(self.w, int(max(xs)) + 2), min(self.h, int(max(ys)) + 2)
        if x1 <= x0 or y1 <= y0:
            return
        mask = Image.new("L", (x1 - x0, y1 - y0), 0)
        md = ImageDraw.Draw(mask)
        alpha = colour[3] if len(colour) > 3 else 255
        for p in polys:
            md.polygon([(x - x0, y - y0) for x, y in p], fill=alpha)
        for p in holes:
            md.polygon([(x - x0, y - y0) for x, y in p], fill=0)
        patch = Image.new("RGB", (x1 - x0, y1 - y0), colour[:3])
        self.img.paste(patch, (x0, y0), mask)

    def lines(self, tiles, layer, colour, stops, match=None):
        w = width_at(stops, self.z)
        if w is None:
            return
        width = max(1, round(w * self.px))
        for (tx, ty), tile in tiles:
            lay = tile.get(layer)
            if not lay:
                continue
            ax, ay, unit = self._frame(tx, ty, lay.extent)
            for ft in lay.features:
                # Lines only. `transportation` also carries polygons (pedestrian
                # squares, piers); Positron doesn't stroke them and stroking
                # their outline would draw a road round every plaza.
                if ft.kind != mvt.LINESTRING or (match and not match(ft.props)):
                    continue
                for ring in ft.rings:
                    if len(ring) < 2 or not self._visible(ring, ax, ay, unit):
                        continue
                    self.d.line(self._project(ring, ax, ay, unit),
                                fill=colour, width=width, joint="curve")

    def labels(self, tiles, scale, ss, lang) -> list[Label]:
        """Collect label candidates, in device (not supersampled) pixels.

        Deduplicated on the way in: a label layer's features sit in a generous
        buffer, so one city arrives from every tile around it — Paris comes back
        nine times from a fifteen-tile map, all at the same world point. Since
        the cap is applied after sorting, leaving them in would spend the whole
        label budget on one name.
        """
        found: dict[tuple[str, int, int], Label] = {}
        for (tx, ty), tile in tiles:
            for layer in ("place", "water_name"):
                lay = tile.get(layer)
                if not lay:
                    continue
                ax, ay, unit = self._frame(tx, ty, lay.extent)
                for ft in lay.features:
                    if ft.kind != mvt.POINT:
                        continue
                    name = _place_name(ft.props, lang)
                    if not name:
                        continue
                    cls = ft.props.get("class")
                    if layer == "place":
                        kind = _PLACE_KINDS.get(cls if isinstance(cls, str) else "")
                        if kind is None:
                            continue
                        prio, size, upper = kind
                        colour, italic = LABEL_PLACE, False
                        text = name.upper() if upper else name
                    else:
                        prio, size = 8, 9.5
                        colour, italic = LABEL_WATER, True
                        text = name
                    x, y = ft.rings[0][0]
                    dx, dy = (ax + x * unit) / ss, (ay + y * unit) / ss
                    if not (0 <= dx <= self.w / ss and 0 <= dy <= self.h / ss):
                        continue
                    rank = ft.props.get("rank")
                    key = (text, round(dx / 4), round(dy / 4))
                    found.setdefault(key, Label(
                        text, dx, dy, size * scale, colour, italic,
                        (prio, float(rank) if isinstance(rank, (int, float)) else 99.0)))
        out = sorted(found.values(), key=lambda l: l.priority)
        return out[:MAX_LABELS]


# ----------------------------------------------------------------- top level ---
def source_tiles(z: int, left: float, top: float, map_w: int, map_h: int):
    """The ``(z, x, y)`` tiles covering a viewport, at the source's own zoom.

    ``left``/``top`` are logical world pixels at the *render* zoom, so past
    :data:`MAX_ZOOM` this returns the shallower ancestors to overzoom.
    """
    zsrc = min(z, MAX_ZOOM)
    k = 2 ** (z - zsrc)
    span = TILE * k
    x0 = math.floor(left / span)
    x1 = math.floor((left + map_w) / span)
    y0 = math.floor(top / span)
    y1 = math.floor((top + map_h) / span)
    n = 2 ** zsrc
    return [(zsrc, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
            if 0 <= y < n]


def render_basemap(z, left, top, map_w, map_h, tiles_dir, *, scale=2, lang=None):
    """Draw the basemap for a viewport and return ``(image, labels)``.

    ``left``/``top`` are the viewport's top-left in logical world pixels at zoom
    ``z``; ``map_w``/``map_h`` its logical size. The image comes back RGB at
    ``scale`` device pixels per logical one. Labels are *not* drawn — they are
    returned for the caller to place after its own pins, which is the whole
    reason they can dodge them. ``lang`` names the places in the book's language
    where the tile offers a translation.
    """
    ss = _ss_for(int(map_w * scale), int(map_h * scale))
    p = _Painter(z, left, top, map_w, map_h, scale, ss)

    # One failed square must not cost the whole map, but a *broken source* must
    # not degrade into a book of blank ones — so the policy is per render rather
    # than per tile: draw whatever answered, and only raise when **nothing** did.
    # `tile_bytes` already reads a 404 as an empty tile, which covers this under
    # urllib; the browser can't, and that is what this is here for. Carto sends
    # `Access-Control-Allow-Origin: *` on a tile it has and *no CORS header at
    # all* on a 404, so a cross-origin 404 is blocked before the status is
    # readable: `netbridge.ts` sees a bare NetworkError and reports status 0,
    # indistinguishable from being offline. There is no way back from that — so
    # instead of asking each tile whether its failure was fatal, ask the render
    # whether the source answered at all. It did if any tile came back (an empty
    # one counts: answering "nothing here" is an answer), and a wrong URL, a
    # moved endpoint or a key now required fails every square, which still
    # raises and still surfaces as a missing map rather than a blank one.
    tiles, failures = [], []
    for zsrc, x, y in source_tiles(z, left, top, map_w, map_h):
        # The x index wraps the globe; y was already clamped to the pyramid.
        try:
            tiles.append(((x, y), fetch_tile(zsrc, x % (2 ** zsrc), y, tiles_dir)))
        except Exception as exc:
            failures.append(exc)
    if failures and not tiles:
        raise failures[0]
    if failures:
        logger.warning("%d of %d basemap tiles could not be fetched (%s); the "
                       "map is drawn without them.", len(failures),
                       len(failures) + len(tiles), failures[0])

    p.fills(tiles, "landcover", GREEN)
    p.fills(tiles, "park", GREEN)
    p.fills(tiles, "landuse", GREEN, lambda pr: pr.get("class") in _LANDUSE_GREEN)
    p.fills(tiles, "landuse", RESIDENTIAL, lambda pr: pr.get("class") == "residential")
    p.fills(tiles, "water", WATER)
    if z >= BUILDING_MIN_ZOOM:
        p.fills(tiles, "building", BUILDING, outline=BUILDING_EDGE)
    p.lines(tiles, "waterway", WATERWAY, _WATERWAY_WIDTHS)
    p.lines(tiles, "boundary", BOUNDARY_REGION, _BOUNDARY_REGION_WIDTHS,
            lambda pr: pr.get("admin_level") in (4, 6) and not pr.get("maritime"))
    p.lines(tiles, "boundary", BOUNDARY_COUNTRY, _BOUNDARY_COUNTRY_WIDTHS,
            lambda pr: pr.get("admin_level") == 2 and not pr.get("maritime"))

    case_colour = ROAD_CASE_FAR if z < 12 else ROAD_CASE_NEAR
    for classes, case, _fill in _ROADS:
        p.lines(tiles, "transportation", case_colour, case,
                lambda pr, c=classes: _road_class(pr) in c)
    p.lines(tiles, "transportation", PATH, _PATH_WIDTHS,
            lambda pr: _road_class(pr) in ("path", "track"))
    for classes, _case, fill in _ROADS:
        colour = ROAD_FILL_MINOR if classes[0] in ("minor", "service") else ROAD_FILL
        p.lines(tiles, "transportation", colour, fill,
                lambda pr, c=classes: _road_class(pr) in c)
    p.lines(tiles, "transportation", RAIL, _RAIL_WIDTHS,
            lambda pr: _road_class(pr) == "rail")

    labels = p.labels(tiles, scale, ss, lang)
    img = p.img if ss == 1 else p.img.resize(
        (int(map_w * scale), int(map_h * scale)), Image.LANCZOS)
    return img, labels
