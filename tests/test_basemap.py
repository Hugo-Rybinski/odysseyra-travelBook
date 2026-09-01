"""The vector basemap: MVT decoding (`maps/mvt.py`) and drawing (`maps/basemap.py`).

Tiles are built here rather than fixtured from the network, so the decoder is
tested against bytes whose every field is known — including the orderings real
encoders use (features before the key/value dictionaries they index into) and
the ones the spec merely permits.
"""

import gzip
import struct

import pytest
from PIL import Image

from odysseyra_travelbook.maps import basemap, mvt, render


# --------------------------------------------------------------- a tiny encoder ---
def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _zig(n: int) -> int:
    return (n << 1) if n >= 0 else ((-n << 1) - 1)


def _field(num: int, wire: int) -> bytes:
    return _varint(num << 3 | wire)


def _msg(num: int, payload: bytes) -> bytes:
    return _field(num, 2) + _varint(len(payload)) + payload


def _packed(num: int, values) -> bytes:
    return _msg(num, b"".join(_varint(v) for v in values))


def _value(v) -> bytes:
    if isinstance(v, bool):
        return _msg(4, _field(7, 0) + _varint(int(v)))
    if isinstance(v, str):
        return _msg(4, _msg(1, v.encode()))
    if isinstance(v, int):
        return _msg(4, _field(4, 0) + _varint(v))
    return _msg(4, _field(3, 1) + struct.pack("<d", v))


def _geometry(kind: int, rings) -> bytes:
    """Encode rings as MoveTo/LineTo(/ClosePath) with zigzag deltas."""
    out = []
    x = y = 0
    for ring in rings:
        pts = list(ring)
        out.append(_varint(1 << 3 | 1))                      # MoveTo, 1 point
        out.append(_varint(_zig(pts[0][0] - x)))
        out.append(_varint(_zig(pts[0][1] - y)))
        x, y = pts[0]
        rest = pts[1:]
        if rest:
            out.append(_varint(len(rest) << 3 | 2))          # LineTo, n points
            for px, py in rest:
                out.append(_varint(_zig(px - x)))
                out.append(_varint(_zig(py - y)))
                x, y = px, py
        if kind == mvt.POLYGON:
            out.append(_varint(1 << 3 | 7))                  # ClosePath
    return b"".join(out)


def layer(name: str, features, extent: int = 4096) -> bytes:
    """One encoded Layer. ``features`` is ``[(kind, rings, props), …]``.

    Keys and values are emitted *after* the features that index into them —
    which is what real encoders do, and what the decoder has to cope with.
    """
    keys: list[str] = []
    vals: list = []
    body = [_msg(1, name.encode())]
    for kind, rings, props in features:
        tags = []
        for k, v in props.items():
            if k not in keys:
                keys.append(k)
            if v not in vals:
                vals.append(v)
            tags += [keys.index(k), vals.index(v)]
        feat = _field(1, 0) + _varint(1)
        if tags:
            feat += _packed(2, tags)
        feat += _field(3, 0) + _varint(kind)
        feat += _msg(4, _geometry(kind, rings))
        body.append(_msg(2, feat))
    for k in keys:
        body.append(_msg(3, k.encode()))
    for v in vals:
        body.append(_value(v))
    body.append(_field(5, 0) + _varint(extent))
    body.append(_field(15, 0) + _varint(2))
    return b"".join(body)


def tile(*layers: bytes) -> bytes:
    return b"".join(_msg(3, ly) for ly in layers)


FULL_RING = ((0, 0), (4096, 0), (4096, 4096), (0, 4096))          # clockwise
HOLE_RING = ((1000, 1000), (1000, 3000), (3000, 3000), (3000, 1000))  # ccw


# ------------------------------------------------------------------- decoding ---
def test_decodes_each_geometry_kind():
    data = tile(
        layer("place", [(mvt.POINT, [[(10, 20)]], {"name": "Somewhere"})]),
        layer("waterway", [(mvt.LINESTRING, [[(0, 0), (100, 50), (40, 90)]], {})]),
        layer("water", [(mvt.POLYGON, [FULL_RING], {})]),
    )
    t = mvt.decode(data)
    assert t["place"].features[0].rings == (((10, 20),),)
    assert t["waterway"].features[0].rings == (((0, 0), (100, 50), (40, 90)),)
    # ClosePath repeats the first point, so the ring comes back closed
    assert t["water"].features[0].rings[0][-1] == (0, 0)
    assert t["water"].features[0].kind == mvt.POLYGON


def test_decodes_negative_deltas_and_multiple_rings():
    """Coordinates are zigzag *deltas*, so a line that doubles back exercises
    the sign handling that a monotonic one never would."""
    data = tile(layer("waterway", [
        (mvt.LINESTRING, [[(500, 500), (100, 900)], [(700, 300), (200, 100)]], {}),
    ]))
    f = mvt.decode(data)["waterway"].features[0]
    assert f.rings == (((500, 500), (100, 900)), ((700, 300), (200, 100)))


def test_decodes_property_types():
    props = {"name": "Lac", "rank": 3, "maritime": False, "area": 12.5}
    data = tile(layer("water_name", [(mvt.POINT, [[(1, 1)]], props)]))
    got = mvt.decode(data)["water_name"].features[0].props
    assert got["name"] == "Lac"
    assert got["rank"] == 3
    assert got["maritime"] is False
    assert got["area"] == pytest.approx(12.5)


def test_unwanted_layers_are_skipped_whole():
    """`keep` is the whole point of the decoder: a city tile's poi/building
    layers are most of the payload and none of the drawing."""
    data = tile(
        layer("water", [(mvt.POLYGON, [FULL_RING], {})]),
        layer("poi", [(mvt.POINT, [[(5, 5)]], {"name": "A cafe"}) for _ in range(50)]),
        layer("building", [(mvt.POLYGON, [FULL_RING], {}) for _ in range(50)]),
    )
    t = mvt.decode(data, {"water"})
    assert set(t) == {"water"}
    # and asking for everything really does find them, so the skip was the filter
    assert set(mvt.decode(data)) == {"water", "poi", "building"}


def test_gzipped_tile_is_inflated():
    raw = tile(layer("water", [(mvt.POLYGON, [FULL_RING], {})]))
    assert mvt.decode(gzip.compress(raw)) == mvt.decode(raw)


def test_empty_and_degenerate_layers_are_dropped():
    # an empty tile, a layer with no features, and a feature with no geometry
    assert mvt.decode(b"") == {}
    assert mvt.decode(tile(layer("water", []))) == {}
    assert mvt.decode(tile(layer("water", [(0, [[(1, 1)]], {})]))) == {}


def test_ring_winding_tells_exterior_from_hole():
    """Tile coordinates run y-downwards, which flips the shoelace sign — get
    this backwards and every lake renders as a hole in the map."""
    assert mvt.ring_is_exterior(FULL_RING)
    assert not mvt.ring_is_exterior(HOLE_RING)
    assert not mvt.ring_is_exterior(tuple(reversed(FULL_RING)))


# ---------------------------------------------------------------- style helpers ---
def test_width_at_interpolates_clamps_and_declines():
    stops = ((10, 1.0), (12, 2.0), (14, 6.0))
    assert basemap.width_at(stops, 9) is None      # below the first stop: not drawn
    assert basemap.width_at(stops, 10) == 1.0
    assert basemap.width_at(stops, 11) == pytest.approx(1.5)
    assert basemap.width_at(stops, 13) == pytest.approx(4.0)
    assert basemap.width_at(stops, 20) == 6.0      # clamped above the last


def test_place_name_prefers_the_books_language():
    props = {"name": "España", "name:latin": "España", "name:fr": "Espagne",
             "name:en": "Spain"}
    assert basemap._place_name(props, "fr") == "Espagne"
    assert basemap._place_name(props, "en") == "Spain"
    assert basemap._place_name(props, None) == "España"        # latin fallback
    assert basemap._place_name({"name": "Ala-Archa"}, "fr") == "Ala-Archa"
    assert basemap._place_name({"rank": 2}, "en") == ""


def test_road_class_folds_construction_onto_the_finished_road():
    assert basemap._road_class({"class": "primary_construction"}) == "primary"
    assert basemap._road_class({"class": "motorway"}) == "motorway"
    assert basemap._road_class({}) == ""


def test_regions_are_not_labelled():
    """Deliberate: OSM's name:en for a French region is often a literal gloss
    ("BURGUNDY-FREE COUNTY"), and a region earns little on a trip map."""
    assert "state" not in basemap._PLACE_KINDS
    assert "country" in basemap._PLACE_KINDS and "city" in basemap._PLACE_KINDS


# ------------------------------------------------------------------- overzoom ---
def test_source_tiles_stay_within_the_pyramid():
    # a single tile-sized viewport sitting exactly on tile (10, 20) at z12
    got = basemap.source_tiles(12, 10 * 256, 20 * 256, 256, 256)
    assert (12, 10, 20) in got

    # Past the source's deepest zoom we overzoom its ancestors instead. z17 is
    # three levels down, so one z14 tile covers 8× the ground and a 900×620
    # viewport lands inside a single one.
    deep = basemap.source_tiles(17, 10 * 256 * 8, 20 * 256 * 8, 900, 620)
    assert deep == [(basemap.MAX_ZOOM, 10, 20)]


# -------------------------------------------------------------------- drawing ---
def _one_tile(monkeypatch, data: bytes):
    """Serve the same decoded tile for every request."""
    decoded = mvt.decode(data, basemap.LAYERS)
    monkeypatch.setattr(basemap, "fetch_tile", lambda z, x, y, td: decoded)


def test_water_is_painted_and_places_are_returned_once(monkeypatch, tmp_path):
    _one_tile(monkeypatch, tile(
        layer("water", [(mvt.POLYGON, [FULL_RING], {})]),
        layer("place", [(mvt.POINT, [[(2048, 2048)]],
                         {"name": "Lourdes", "class": "town", "rank": 4})]),
    ))
    img, labels = basemap.render_basemap(12, 0, 0, 256, 256, tmp_path, scale=2)
    assert img.size == (512, 512)
    assert img.getpixel((256, 256)) == basemap.WATER[:3]
    # every tile in the viewport carries the same place point; it must survive once
    assert [lb.text for lb in labels] == ["Lourdes"]


def test_a_lake_with_an_island_keeps_its_hole(monkeypatch, tmp_path):
    _one_tile(monkeypatch, tile(
        layer("water", [(mvt.POLYGON, [FULL_RING, HOLE_RING], {})]),
    ))
    img, _ = basemap.render_basemap(12, 0, 0, 256, 256, tmp_path, scale=2)
    assert img.getpixel((20, 20)) == basemap.WATER[:3]          # in the lake
    assert img.getpixel((256, 256)) == basemap.BACKGROUND       # on the island


def test_roads_below_their_first_stop_are_not_drawn(monkeypatch, tmp_path):
    """A z6 map shows motorways and nothing else — the per-zoom stops stand in
    for Positron's minzoom, which is what keeps a country map legible."""
    roads = tile(layer("transportation", [
        (mvt.LINESTRING, [[(0, 2048), (4096, 2048)]], {"class": "service"}),
    ]))
    _one_tile(monkeypatch, roads)
    far, _ = basemap.render_basemap(6, 0, 0, 256, 256, tmp_path, scale=2)
    assert far.getpixel((256, 256)) == basemap.BACKGROUND

    # A service road appears at z15. The viewport is sized to the overzoomed
    # tile's span (256 × 2**(15-14)) so the road's mid-tile y lands mid-canvas.
    near, _ = basemap.render_basemap(15, 0, 0, 512, 512, tmp_path, scale=2)
    assert near.getpixel((512, 512)) != basemap.BACKGROUND


def test_buildings_are_drawn_only_close_in(monkeypatch, tmp_path):
    """An area map is a few city blocks, where footprints are what you navigate
    by; on a day map of a whole région they'd be a grey smear."""
    _one_tile(monkeypatch, tile(
        layer("building", [(mvt.POLYGON, [FULL_RING], {})]),
    ))
    far, _ = basemap.render_basemap(basemap.BUILDING_MIN_ZOOM - 1, 0, 0, 256, 256,
                                   tmp_path, scale=2)
    near, _ = basemap.render_basemap(basemap.BUILDING_MIN_ZOOM, 0, 0, 256, 256,
                                    tmp_path, scale=2)
    assert far.getpixel((256, 256)) == basemap.BACKGROUND
    assert near.getpixel((256, 256)) == basemap.BUILDING[:3]


def test_a_language_names_the_places(monkeypatch, tmp_path):
    _one_tile(monkeypatch, tile(layer("place", [
        (mvt.POINT, [[(2048, 2048)]],
         {"name": "Kyrgyzstan", "name:fr": "Kirghizistan", "class": "country"}),
    ])))
    _, fr = basemap.render_basemap(6, 0, 0, 256, 256, tmp_path, scale=2, lang="fr")
    _, none = basemap.render_basemap(6, 0, 0, 256, 256, tmp_path, scale=2)
    assert [lb.text for lb in fr] == ["KIRGHIZISTAN"]      # country class is upper
    assert [lb.text for lb in none] == ["KYRGYZSTAN"]


# ----------------------------------------------------------- labels vs. pins ---
def test_a_label_is_dropped_where_a_pin_already_sits():
    """The whole reason labels are drawn from data instead of a pre-rendered
    label tile: the raster overlay was composited over our pins regardless, so a
    numbered pin could end up sitting on the town it marked."""
    label = basemap.Label("Cauterets", 100.0, 100.0, 24.0, (0, 0, 0), False, (3, 5.0))

    free = Image.new("RGB", (200, 200), (255, 255, 255))
    render._draw_labels(free, [label], [])
    assert free.getcolors(maxcolors=8) is None or len(free.getcolors()) > 1

    blocked = Image.new("RGB", (200, 200), (255, 255, 255))
    render._draw_labels(blocked, [label], [(0, 0, 200, 200)])
    assert blocked.getcolors() == [(200 * 200, (255, 255, 255))]


def test_a_label_that_would_be_clipped_is_dropped():
    """Half a name at the edge reads as a broken render, so it is left out."""
    edge = basemap.Label("Mont-de-Marsan", 4.0, 100.0, 24.0, (0, 0, 0), False, (3, 5.0))
    img = Image.new("RGB", (200, 200), (255, 255, 255))
    render._draw_labels(img, [edge], [])
    assert img.getcolors() == [(200 * 200, (255, 255, 255))]


def test_pin_box_covers_the_tip_and_the_head():
    """The dodge only works if the box really is where the teardrop is drawn."""
    import math
    box = render._pin_box(100, 200, 30, -math.pi / 2, 6)   # head straight up
    assert box[0] < 100 < box[2]
    assert box[1] < 200 - 30 and box[3] == 200             # tip is the bottom edge
