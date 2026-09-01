"""Mapbox Vector Tile decoding — bytes to features, pure stdlib.

Why this exists: Carto still serves its **vector** basemap keyless — those are
the tiles the web viewer's MapLibre map already draws — while the pre-rendered
**raster** tiles this package used to stitch now come back stamped
``API KEY REQUIRED``. They come back with an HTTP 200 and a valid PNG, so no
amount of retrying or error handling downstream could notice; the watermark just
appears in the book. Reusing the viewer's source means turning geometry into
pixels ourselves, and this module is the first half of that. :mod:`basemap` is
the second half (features to an image).

Only what a basemap figure needs is decoded. The caller names the layers it
wants, and every other layer is skipped over by its length prefix without a
single feature being decoded — which matters more than it sounds: on a dense
city tile the ``poi`` / ``housenumber`` / ``building`` layers we never draw are
13 of every 16 features in the tile.

Nothing here knows about styling, projection or Pillow: a tile decodes to
integer coordinates in its own local grid (0…``extent``), and the caller places
that grid on the world. See https://github.com/mapbox/vector-tile-spec (v2).
"""

from __future__ import annotations

import gzip
import struct
from dataclasses import dataclass
from typing import Collection

# Geometry types, as in the spec's GeomType enum (0 = UNKNOWN, which we drop).
POINT = 1
LINESTRING = 2
POLYGON = 3

DEFAULT_EXTENT = 4096


@dataclass(frozen=True, slots=True)
class Feature:
    """One tile feature in local tile coordinates.

    ``rings`` is a tuple of point sequences whose meaning follows ``kind``: one
    entry per point for :data:`POINT`, one per line for :data:`LINESTRING`, and
    for :data:`POLYGON` an exterior ring followed by any interior rings (holes),
    which the spec distinguishes by winding order — see
    :func:`ring_is_exterior`.
    """

    kind: int
    rings: tuple[tuple[tuple[int, int], ...], ...]
    props: dict[str, object]


@dataclass(frozen=True, slots=True)
class Layer:
    name: str
    extent: int
    features: tuple[Feature, ...]


# --------------------------------------------------------------- protobuf ---
# A hand-rolled reader rather than a dependency: the wire format we need is
# four field types wide, and `protobuf` is a compiled package that would have to
# work inside Pyodide too.


def _varint(b: bytes, i: int) -> tuple[int, int]:
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def _zigzag(n: int) -> int:
    return (n >> 1) ^ -(n & 1)


def _skip(b: bytes, i: int, wire: int) -> int:
    """Advance past one field's payload, given its wire type."""
    if wire == 0:
        return _varint(b, i)[1]
    if wire == 2:
        n, i = _varint(b, i)
        return i + n
    if wire == 5:
        return i + 4
    if wire == 1:
        return i + 8
    raise ValueError(f"unsupported protobuf wire type {wire}")


def _string(b: bytes, i: int, n: int) -> str:
    # "replace" rather than raising: one odd byte in a place name is not a
    # reason to lose the whole map.
    return b[i:i + n].decode("utf-8", "replace")


def _value(b: bytes, i: int, end: int) -> object:
    """One Value message — exactly one of its seven typed fields is set."""
    while i < end:
        key, i = _varint(b, i)
        field, wire = key >> 3, key & 7
        if field == 1 and wire == 2:            # string
            n, i = _varint(b, i)
            return _string(b, i, n)
        if field == 2 and wire == 5:            # float
            return struct.unpack_from("<f", b, i)[0]
        if field == 3 and wire == 1:            # double
            return struct.unpack_from("<d", b, i)[0]
        if field in (4, 5) and wire == 0:       # int64 / uint64
            return _varint(b, i)[0]
        if field == 6 and wire == 0:            # sint64
            return _zigzag(_varint(b, i)[0])
        if field == 7 and wire == 0:            # bool
            return bool(_varint(b, i)[0])
        i = _skip(b, i, wire)
    return None


def _geometry(b: bytes, i: int, end: int, kind: int):
    """Decode the packed command/parameter stream into point sequences.

    Coordinates are deltas in a zigzag varint encoding, so every ring has to be
    walked in order — there is no random access into a tile's geometry.
    """
    rings: list[tuple[tuple[int, int], ...]] = []
    cur: list[tuple[int, int]] = []
    x = y = 0
    while i < end:
        cmd, i = _varint(b, i)
        cmd_id, count = cmd & 7, cmd >> 3
        if cmd_id == 7:                          # ClosePath: no parameters
            if cur:
                cur.append(cur[0])
            continue
        for _ in range(count):
            if i >= end:                         # truncated tile; keep what we have
                break
            dx, i = _varint(b, i)
            dy, i = _varint(b, i)
            x += _zigzag(dx)
            y += _zigzag(dy)
            if cmd_id == 1:                      # MoveTo starts a new ring/line/point
                if cur:
                    rings.append(tuple(cur))
                cur = [(x, y)]
            else:                                # LineTo continues the current one
                cur.append((x, y))
    if cur:
        rings.append(tuple(cur))
    return tuple(rings)


def _feature(b: bytes, i: int, end: int, keys: list[str], vals: list[object]) -> Feature:
    # Tags and geometry are length-delimited and may arrive in either order (and
    # before the type), so spans are noted first and decoded once the whole
    # message has been walked.
    kind = 0
    tags: tuple[int, int] | None = None
    geom: tuple[int, int] | None = None
    while i < end:
        key, i = _varint(b, i)
        field, wire = key >> 3, key & 7
        if wire == 2:
            n, i = _varint(b, i)
            if field == 2:
                tags = (i, i + n)
            elif field == 4:
                geom = (i, i + n)
            i += n
        elif wire == 0:
            v, i = _varint(b, i)
            if field == 3:
                kind = v
        else:
            i = _skip(b, i, wire)

    props: dict[str, object] = {}
    if tags:
        j, stop = tags
        while j < stop:
            k, j = _varint(b, j)
            v, j = _varint(b, j)
            if k < len(keys) and v < len(vals):
                props[keys[k]] = vals[v]
    return Feature(kind, _geometry(b, *geom, kind) if geom else (), props)


def _layer_name(b: bytes, i: int, end: int) -> str:
    """Peek a layer's name without decoding it, so it can be skipped whole."""
    while i < end:
        key, i = _varint(b, i)
        field, wire = key >> 3, key & 7
        if field == 1 and wire == 2:
            n, i = _varint(b, i)
            return _string(b, i, n)
        i = _skip(b, i, wire)
    return ""


def _layer(b: bytes, i: int, end: int, name: str) -> Layer:
    # Encoders emit the features *before* the key/value dictionaries they index
    # into, so feature spans are collected on the way past and resolved after.
    keys: list[str] = []
    vals: list[object] = []
    spans: list[tuple[int, int]] = []
    extent = DEFAULT_EXTENT
    while i < end:
        key, i = _varint(b, i)
        field, wire = key >> 3, key & 7
        if wire == 2:
            n, i = _varint(b, i)
            if field == 2:
                spans.append((i, i + n))
            elif field == 3:
                keys.append(_string(b, i, n))
            elif field == 4:
                vals.append(_value(b, i, i + n))
            i += n
        elif wire == 0:
            v, i = _varint(b, i)
            if field == 5:
                extent = v or DEFAULT_EXTENT
        else:
            i = _skip(b, i, wire)
    feats = tuple(_layer_features(b, spans, keys, vals))
    return Layer(name, extent, feats)


def _layer_features(b, spans, keys, vals):
    for start, stop in spans:
        f = _feature(b, start, stop, keys, vals)
        if f.kind and f.rings:
            yield f


# ------------------------------------------------------------------- public ---
def decode(data: bytes, keep: Collection[str] | None = None) -> dict[str, Layer]:
    """Decode a ``.mvt`` tile to ``{layer name: Layer}``.

    ``keep`` names the layers wanted; anything else is stepped over without
    being decoded (pass ``None`` for everything). Gzipped tiles are inflated
    transparently — the same courtesy :mod:`models.gpx` extends to a GPX file.
    An empty layer is dropped rather than returned empty, so ``in`` on the
    result answers "is there anything to draw".
    """
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    out: dict[str, Layer] = {}
    i, n = 0, len(data)
    while i < n:
        key, i = _varint(data, i)
        field, wire = key >> 3, key & 7
        if field == 3 and wire == 2:                 # Tile.layers
            ln, i = _varint(data, i)
            end = i + ln
            name = _layer_name(data, i, end)
            if keep is None or name in keep:
                layer = _layer(data, i, end, name)
                if layer.features:
                    out[name] = layer
            i = end
        else:
            i = _skip(data, i, wire)
    return out


def ring_is_exterior(ring: Collection[tuple[int, int]]) -> bool:
    """Whether a polygon ring is an exterior one (rather than a hole).

    The spec distinguishes them by winding order: an exterior ring runs
    clockwise, an interior one counter-clockwise. Tile coordinates put the
    origin top-left with y growing *downwards*, which flips the usual reading of
    the shoelace sum — clockwise-on-screen comes out positive there. Used only
    where a polygon actually has more than one ring, since punching holes costs
    a mask.
    """
    pts = tuple(ring)
    area = 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        area += x1 * y2 - x2 * y1
    return area > 0
