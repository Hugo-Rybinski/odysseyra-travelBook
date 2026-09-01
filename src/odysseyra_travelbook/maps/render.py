"""Map rendering: draw the Carto Positron basemap, boost its contrast, add the
route and numbered pins, and place the basemap's own labels on top. Pure Pillow.

The basemap itself comes from :mod:`basemap`, which rasterizes Carto's **vector**
tiles — the ones the web viewer's MapLibre map draws. The pre-rendered raster
tiles this module used to stitch now come back watermarked unless a key is
supplied (and with an HTTP 200, so nothing could tell). Two consequences show up
here: the basemap arrives as one image instead of a base + labels-only sandwich,
and the labels arrive as *data*, drawn last so they can dodge our own pins —
something a pre-rendered label tile could never do.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from pathlib import Path

from . import basemap

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"

ATTRIBUTION = "© OpenStreetMap contributors © CARTO"

TILE = 256      # logical slippy-map tile size (projection unit)
SCALE = 2       # device pixels per logical pixel (a "@2x" render)
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


# ------------------------------------------------------------------ helpers ---
def _font(size: int, name: str = "DejaVuSans-Bold.ttf"):
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except Exception:
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


def dashes(line, dash: float, gap: float):
    """Split a projected polyline into dash pieces — ``[((x1, y1), (x2, y2)), …]``.

    Walks the whole line so the dash rhythm carries across its corners (a
    transport leg is a single straight segment, but this keeps it general).
    Pillow has no dash support, hence doing it by hand.
    """
    out = []
    if dash <= 0 or gap < 0:
        return out
    period = dash + gap
    phase = 0.0            # distance already consumed inside the current period
    for (x1, y1), (x2, y2) in zip(line, line[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        if seg <= 0:
            continue
        ux, uy = (x2 - x1) / seg, (y2 - y1) / seg
        pos = 0.0
        while pos < seg:
            if phase < dash:                       # inside a dash
                take = min(dash - phase, seg - pos)
                out.append(((x1 + ux * pos, y1 + uy * pos),
                            (x1 + ux * (pos + take), y1 + uy * (pos + take))))
            else:                                  # inside a gap
                take = min(period - phase, seg - pos)
            pos += take
            phase = (phase + take) % period
    return out


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


def _boxes_overlap(a, b, pad: float = 0.0) -> bool:
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0]
                or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def _pin_box(x, y, R, angle, bw):
    """The area a pin occupies — its tip plus its head disc — so a place label
    can be dropped rather than printed under it."""
    L = R * 2.15
    hx, hy = x + L * math.cos(angle), y + L * math.sin(angle)
    r = R + bw
    return (min(x, hx - r), min(y, hy - r), max(x, hx + r), max(y, hy + r))


def _draw_labels(img: Image.Image, labels, taken: list) -> None:
    """Draw the basemap's place names, skipping any that would collide.

    Greedy in the order :mod:`basemap` ranked them (a capital before a hamlet),
    testing each against the pins and the labels already placed. The raster
    label tiles this replaces couldn't do that — they were composited over our
    pins whatever they hit — so a numbered pin sometimes sat on top of the very
    town it marked.
    """
    d = ImageDraw.Draw(img, "RGBA")
    for lb in labels:
        size = max(7, round(lb.size))
        if lb.italic:
            font = _font(size, "DejaVuSans-Oblique.ttf")
        elif lb.priority[0] <= 2:      # a country or a city carries weight
            font = _font(size)
        else:
            font = _font(size, "DejaVuSans.ttf")
        box = d.textbbox((lb.x, lb.y), lb.text, font=font, anchor="mm")
        # A name only half on the page reads as a rendering fault, so it is
        # dropped rather than clipped — the anchor being inside isn't enough.
        if box[0] < 0 or box[1] < 0 or box[2] > img.width or box[3] > img.height:
            continue
        if any(_boxes_overlap(box, t, pad=2 * SCALE) for t in taken):
            continue
        taken.append(box)
        d.text((lb.x, lb.y), lb.text, font=font, fill=lb.color, anchor="mm",
               stroke_width=max(1, round(size * 0.13)),
               stroke_fill=basemap.LABEL_HALO)


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
               route_nodes=None, legs=None, lang=None) -> Image.Image:
    """Render an RGB map image fitting every ``(lat, long)`` in ``all_coords``.

    * ``routes`` — list of ``[(lat, long), …]`` polylines (drives), drawn as a
      translucent accent line.
    * ``legs`` — list of ``[(lat, long), (lat, long)]`` transport endpoint pairs,
      drawn as thin dotted straight lines under the routes. They are not
      expected to be inside ``all_coords``: a leg heading far away is simply
      clipped at the edge (see ``build.render_day_maps``).
    * ``points`` — ordered ``[(lat, long), …]``; each gets a pin.
    * ``labels`` — pin text per point (defaults to ``1..N``); e.g. letters for an
      area map or ``*`` for the night's stay.
    * ``route_nodes`` — ``[(lat, long), …]`` the named stops of the routes
      (the departure plus each named waypoint); each gets a small full-opacity
      accent disc sitting on top of the translucent route line. Unnamed
      route-shaping waypoints are not marked.
    * ``accent`` — ``(r, g, b)`` theme color (the trip's ``cover_color``).
    * ``lang`` — names the basemap's places in the book's language where the
      tiles carry a translation.
    """
    lats = [c[0] for c in all_coords]
    lons = [c[1] for c in all_coords]
    z = _pick_zoom((min(lats), min(lons), max(lats), max(lons)), map_w, map_h)
    cx, cy = lonlat_to_px((min(lats) + max(lats)) / 2,
                          (min(lons) + max(lons)) / 2, z)
    left, top = cx - map_w / 2, cy - map_h / 2

    def project(lat, lon):
        gx, gy = lonlat_to_px(lat, lon, z)
        return ((gx - left) * SCALE, (gy - top) * SCALE)

    base, place_labels = basemap.render_basemap(
        z, left, top, map_w, map_h, tiles_dir, scale=SCALE, lang=lang)
    img = boost_contrast(base,
                         contrast=1.15 if ink_saver else 1.4,
                         saturation=0.4 if ink_saver else 0.7)

    # transport legs: thin dotted straight lines, drawn first so a drive's solid
    # geometry sits on top of them where the two overlap.
    leg_lines = [[project(*c) for c in line] for line in (legs or []) if len(line) >= 2]
    if leg_lines:
        def paint_legs(d, ss):
            w = round((2 if ink_saver else 3) * SCALE * ss)
            dash, gap = 8 * SCALE * ss, 7 * SCALE * ss
            for line in leg_lines:
                for a, b in dashes([(x * ss, y * ss) for x, y in line], dash, gap):
                    d.line([a, b], fill=accent + (255,), width=w)
        layer = _ss_layer(img.size, paint_legs)
        img.alpha_composite(Image.blend(
            Image.new("RGBA", img.size, (0, 0, 0, 0)), layer, 0.75))

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
    keep_clear = []
    if px:
        R = 15 * SCALE
        angles = pin_angles(px, head_r=R)
        font = _font(round(17 * SCALE * SS))
        pin_col = (255, 255, 255) if ink_saver else accent
        keep_clear = [_pin_box(x, y, R, ang, R * 0.22)
                      for (x, y), ang in zip(px, angles)]

        def paint_pins(d, ss):
            for i, ((x, y), ang) in enumerate(zip(px, angles), start=1):
                text = labels[i - 1] if labels else str(i)
                if ink_saver:  # outline pin, accent text — light on ink
                    _teardrop(d, (x * ss + R * ss * 2.15 * math.cos(ang),
                                  y * ss + R * ss * 2.15 * math.sin(ang)),
                              (x * ss, y * ss), R * ss, (255, 255, 255, 255))
                _pin(d, x * ss, y * ss, R * ss, text, font, accent, ang)
        img.alpha_composite(_ss_layer(img.size, paint_pins))

    # the map's own place labels, drawn last so they sit above route + pins —
    # and skipped where a pin already claims the space.
    keep_clear.append(_attribution_box(img))
    _draw_labels(img, place_labels, keep_clear)

    _attribution(img)
    return img.convert("RGB")


def _attribution_box(img: Image.Image):
    """Where :func:`_attribution` will sit, so no label is placed under it."""
    d = ImageDraw.Draw(img)
    af = _font(11 * SCALE)
    bb = d.textbbox((0, 0), ATTRIBUTION, font=af)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    pad = 4 * SCALE
    return (img.width - w - 2 * pad, img.height - h - 2 * pad, img.width, img.height)


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
