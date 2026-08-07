"""Raster map rendering: stitch Carto (OSM) tiles, boost contrast, draw the
route and numbered pins, and keep the basemap's own labels on top. Pure Pillow.
"""

from __future__ import annotations

import math
import urllib.request

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from pathlib import Path

from . import USER_AGENT

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"

# Carto Positron, split into a label-free base and a labels-only overlay so the
# contrast boost works on clean imagery and the map's own place names sit on top
# of the route/pins. "@2x" = retina tiles. Roads-first, no relief.
BASE_URL = "https://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}@2x.png"
LABELS_URL = "https://basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}@2x.png"
ATTRIBUTION = "© OpenStreetMap contributors © CARTO"

TILE = 256      # logical slippy-map tile size (projection unit)
SCALE = 2       # @2x tiles -> device pixels are 2x logical
SS = 3          # overlay supersampling for antialiased strokes/shapes


# ---------------------------------------------------------- slippy-map math ---
def lonlat_to_px(lat: float, lon: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n * TILE
    lr = math.radians(lat)
    y = (1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * n * TILE
    return x, y


def _pick_zoom(bbox, map_w, map_h) -> int:
    min_lat, min_lon, max_lat, max_lon = bbox
    for z in range(17, 1, -1):
        x0, y0 = lonlat_to_px(max_lat, min_lon, z)
        x1, y1 = lonlat_to_px(min_lat, max_lon, z)
        if (x1 - x0) <= map_w * 0.8 and (y1 - y0) <= map_h * 0.7:
            return z
    return 2


def _fetch_tile(url, style, z, x, y, tiles_dir: Path) -> Image.Image:
    f = tiles_dir / f"{style}_{z}_{x}_{y}.png"
    if not f.exists():
        req = urllib.request.Request(url.format(z=z, x=x, y=y),
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as r:
            f.write_bytes(r.read())
    return Image.open(f).convert("RGBA")


# ------------------------------------------------------------------ helpers ---
def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf",):
        try:
            return ImageFont.truetype(str(FONT_DIR / name), size)
        except Exception:
            pass
    return ImageFont.load_default()


def boost_contrast(img: Image.Image, contrast=1.4, saturation=0.7) -> Image.Image:
    """Punch up the pale Positron base (uniform contrast + slight desaturation),
    applied to the text-free base before overlays so labels don't smear."""
    rgb = ImageEnhance.Color(img.convert("RGB")).enhance(saturation)
    rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    return rgb.convert("RGBA")


def _ss_layer(size, draw_fn) -> Image.Image:
    big = Image.new("RGBA", (size[0] * SS, size[1] * SS), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(big, "RGBA"), SS)
    return big.resize(size, Image.LANCZOS)


def pin_angles(px, head_r: float) -> list[float]:
    """Tip->head angle per pin; clustered pins fan their heads apart."""
    n = len(px)
    angles = [-math.pi / 2] * n
    thresh = 2.3 * head_r
    seen = [False] * n
    for i in range(n):
        if seen[i]:
            continue
        cluster = [i] + [j for j in range(i + 1, n)
                         if abs(px[i][0] - px[j][0]) < thresh
                         and abs(px[i][1] - px[j][1]) < thresh]
        if len(cluster) < 2:
            continue
        for k in cluster:
            seen[k] = True
        m = len(cluster)
        spread = min((m - 1) * 1.05, 2 * math.pi * (m - 1) / m)
        start = -math.pi / 2 - spread / 2
        for idx, k in enumerate(cluster):
            angles[k] = start + spread * idx / (m - 1)
    return angles


def _teardrop(d, hc, tip, R, fill):
    hcx, hcy = hc
    tx, ty = tip
    D = math.hypot(tx - hcx, ty - hcy)
    if D <= R:
        d.ellipse([hcx - R, hcy - R, hcx + R, hcy + R], fill=fill)
        return
    beta = math.acos(R / D)
    base = math.atan2(ty - hcy, tx - hcx)
    pL = (hcx + R * math.cos(base - beta), hcy + R * math.sin(base - beta))
    pR = (hcx + R * math.cos(base + beta), hcy + R * math.sin(base + beta))
    d.polygon([tip, pL, pR], fill=fill)
    d.ellipse([hcx - R, hcy - R, hcx + R, hcy + R], fill=fill)


def _pin(d, x, y, R, number, font, accent, angle):
    L = R * 2.15
    hc = (x + L * math.cos(angle), y + L * math.sin(angle))
    bw = R * 0.22
    _teardrop(d, hc, (x, y), R + bw, (255, 255, 255, 255))
    _teardrop(d, hc, (x, y), R, accent + (255,))
    # anchor="mm" centers the glyph on the head centre exactly
    d.text(hc, number, font=font, fill=(255, 255, 255, 255), anchor="mm")


# ---------------------------------------------------------------- top level ---
def render_map(all_coords, routes, points, accent, tiles_dir,
               map_w=900, map_h=620, ink_saver=False, labels=None,
               route_nodes=None) -> Image.Image:
    """Render an RGB map image fitting every ``(lat, long)`` in ``all_coords``.

    * ``routes`` — list of ``[(lat, long), …]`` polylines (drives), drawn as a
      translucent accent line.
    * ``points`` — ordered ``[(lat, long), …]``; each gets a pin.
    * ``labels`` — pin text per point (defaults to ``1..N``); e.g. letters for an
      area map or ``*`` for the night's stay.
    * ``route_nodes`` — ``[(lat, long), …]`` the named stops of the routes
      (the departure plus each named waypoint); each gets a small full-opacity
      accent disc sitting on top of the translucent route line. Unnamed
      route-shaping waypoints are not marked.
    * ``accent`` — ``(r, g, b)`` theme color (the trip's ``cover_color``).
    """
    lats = [c[0] for c in all_coords]
    lons = [c[1] for c in all_coords]
    z = _pick_zoom((min(lats), min(lons), max(lats), max(lons)), map_w, map_h)
    cx, cy = lonlat_to_px((min(lats) + max(lats)) / 2,
                          (min(lons) + max(lons)) / 2, z)
    left, top = cx - map_w / 2, cy - map_h / 2
    dtile = TILE * SCALE
    tx0, ty0 = int(left // TILE), int(top // TILE)
    tx1, ty1 = int((left + map_w) // TILE), int((top + map_h) // TILE)

    def stitch(url, style):
        canvas = Image.new("RGBA", ((tx1 - tx0 + 1) * dtile, (ty1 - ty0 + 1) * dtile))
        for tx in range(tx0, tx1 + 1):
            for ty in range(ty0, ty1 + 1):
                canvas.paste(_fetch_tile(url, style, z, tx, ty, tiles_dir),
                             ((tx - tx0) * dtile, (ty - ty0) * dtile))
        ox, oy = int((left - tx0 * TILE) * SCALE), int((top - ty0 * TILE) * SCALE)
        return canvas.crop((ox, oy, ox + map_w * SCALE, oy + map_h * SCALE)).convert("RGBA")

    def project(lat, lon):
        gx, gy = lonlat_to_px(lat, lon, z)
        return ((gx - left) * SCALE, (gy - top) * SCALE)

    img = boost_contrast(stitch(BASE_URL, "nolabels"),
                         contrast=1.15 if ink_saver else 1.4,
                         saturation=0.4 if ink_saver else 0.7)

    # routes: supersampled, translucent, theme color (no casing)
    route_lines = [[project(*c) for c in line] for line in routes if len(line) >= 2]
    if route_lines:
        def paint(d, ss):
            for line in route_lines:
                d.line([(x * ss, y * ss) for x, y in line],
                       fill=accent + (255,),
                       width=round((3 if ink_saver else 6) * SCALE * ss),
                       joint="curve")
        layer = _ss_layer(img.size, paint)
        img.alpha_composite(Image.blend(
            Image.new("RGBA", img.size, (0, 0, 0, 0)), layer, 0.6))

    # route nodes: small full-opacity accent discs (white-ringed) marking the
    # departure and each named waypoint, sitting on top of the translucent
    # route line.
    node_px = [project(lat, lon) for lat, lon in (route_nodes or [])]
    if node_px:
        nr = (3 if ink_saver else 4) * SCALE
        ring = 1.4 * SCALE

        def paint_nodes(d, ss):
            for x, y in node_px:
                cx, cy = x * ss, y * ss
                r = nr * ss
                d.ellipse([cx - r - ring * ss, cy - r - ring * ss,
                           cx + r + ring * ss, cy + r + ring * ss],
                          fill=(255, 255, 255, 255))
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent + (255,))
        img.alpha_composite(_ss_layer(img.size, paint_nodes))

    # pins: numbered teardrops, clustered ones fanned apart by rotation
    px = [project(lat, lon) for lat, lon in points]
    if px:
        R = 15 * SCALE
        angles = pin_angles(px, head_r=R)
        font = _font(round(17 * SCALE * SS))
        pin_col = (255, 255, 255) if ink_saver else accent

        def paint_pins(d, ss):
            for i, ((x, y), ang) in enumerate(zip(px, angles), start=1):
                text = labels[i - 1] if labels else str(i)
                if ink_saver:  # outline pin, accent text — light on ink
                    _teardrop(d, (x * ss + R * ss * 2.15 * math.cos(ang),
                                  y * ss + R * ss * 2.15 * math.sin(ang)),
                              (x * ss, y * ss), R * ss, (255, 255, 255, 255))
                _pin(d, x * ss, y * ss, R * ss, text, font, accent, ang)
        img.alpha_composite(_ss_layer(img.size, paint_pins))

    # the map's own place labels, composited last so they sit above route + pins
    img.alpha_composite(stitch(LABELS_URL, "onlylabels"))

    _attribution(img)
    return img.convert("RGB")


def _attribution(img: Image.Image) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    af = _font(11 * SCALE)
    bb = d.textbbox((0, 0), ATTRIBUTION, font=af)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    pad = 4 * SCALE
    d.rectangle([img.width - w - 2 * pad, img.height - h - 2 * pad,
                 img.width, img.height], fill=(255, 255, 255, 200))
    d.text((img.width - w - pad, img.height - h - pad), ATTRIBUTION, font=af,
           fill=(80, 80, 80))
