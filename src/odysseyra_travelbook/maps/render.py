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

from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from pathlib import Path

from . import basemap

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"

ATTRIBUTION = "© OpenStreetMap contributors © CARTO"

TILE = 256      # logical slippy-map tile size (projection unit)
SCALE = 2       # device pixels per logical pixel (a "@2x" render)
SS = 3          # overlay supersampling for antialiased strokes/shapes

# --- a trail's own decoration (see `Trail`) ---------------------------------
# Target spacing between direction arrowheads along the walked line, and the
# head's length, both in logical px (pre-``SCALE``). The spacing is a *target*:
# the arrows are spread evenly over the line's usable length, so a short trail
# gets fewer rather than a cramped run of them.
ARROW_SPACING = 58
ARROW_LEN = 10

# With distance marks on the line, the arrowheads are spaced this much further
# apart. The marks are then the figure's scale — numbered, and on a day hike
# drawn at this size roughly one every `ARROW_SPACING` — and the heads go back to
# being the occasional "this way" they were for: at the same pitch the two land
# on each other all the way along, and a tick drawn across the line under a head
# drawn along it is a smudge rather than either. Kept modest on purpose: an
# out-and-back already loses half its heads to the doubled-back rule, so a large
# factor there leaves a trail with one arrow on it.
ARROW_SPARSE = 1.4

# A distance mark: the tick drawn across the line, and its number's size.
KM_TICK_LEN = 9
KM_LABEL_PT = 9

# Length left clear at each end of the line, so no arrowhead is drawn under a
# trailhead marker.
ARROW_CLEAR = 16

# A trail whose two ends are this close is walked back to where it started — a
# loop, or an out-and-back — and draws its start marker alone. Deliberately a
# *ground* distance rather than a screen one so the figure doesn't gain a second
# marker purely by being drawn larger; `TrailDecor` in web/src/render/DayMapGL.tsx
# uses the same threshold, and the two must agree or the same hike shows a finish
# on paper and not on screen.
LOOP_MERGE_KM = 0.03


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


@dataclass
class Trail:
    """A walked line's own decoration, on top of the route line itself.

    A drive is drawn as a route and *described* in the itinerary — "Amboise →
    Sarlat", with its junctions listed — so its line needs no direction and its
    named stops are the numbered pins. A **trail** has none of that: it is one
    activity with one line, and without decoration an out-and-back and a loop
    look alike, neither says which end you set off from, and the col you turn at
    is just a bend. So this carries the three things that line can't say for
    itself:

    * ``line`` — the walked geometry, in walking order, which is where the
      direction arrowheads and the two trailhead markers are placed from.
    * ``waypoints`` — ``(lat, long, name)`` for the points the file names
      (a hike's GPX ``<wpt>``s), each drawn as a small marker with its name.
    * ``km_marks`` — ``(lat, long, km, bearing)`` distance marks, drawn as a tick
      across the line, an arrowhead just past it pointing the way you were
      walking, and its number. The elevation profile ticks the *same* numbers on
      its axis, which is what lets one figure be read onto the other. The
      ``bearing`` (degrees clockwise from north) is measured off the recording by
      ``models/gpx.py``, never inferred from the drawn line — on an out-and-back
      the nearest point of the line can be on the other leg, i.e. the direction
      you didn't walk, and telling the two legs apart is exactly what the arrows
      are for.

    Only :func:`build.render_hike_map` passes one; every other map leaves it
    ``None`` and renders exactly as before.
    """

    line: list[tuple[float, float]] = field(default_factory=list)
    waypoints: list[tuple[float, float, str]] = field(default_factory=list)
    km_marks: list[tuple[float, float, int, float]] = field(default_factory=list)


def arrows_along(line, spacing: float, clear: float):
    """``[(x, y, angle), …]`` along a projected polyline, one arrowhead every
    ``spacing`` with ``clear`` left free at each end.

    The heads are spread *evenly* over the usable length rather than laid down
    at a fixed pitch from one end: a fixed pitch leaves a ragged remainder at the
    far end, which on a line whose only job is to say "this way" reads as the
    arrows having run out. A line with no room for even one head gets none — the
    two trailhead markers still say where it begins and ends.

    A head landing on top of one already placed is **dropped**, which is what
    makes an out-and-back readable: it is one line walked twice, so its outbound
    and return heads land on the same stretch of path pointing opposite ways, and
    drawing both turned every doubled-back section into a row of little
    butterflies. Keeping the first — the outbound one, the line being in walking
    order — says the one thing the reader needs, which way round you set off;
    the return is that same line back.
    """
    segs = []
    total = 0.0
    for (x1, y1), (x2, y2) in zip(line, line[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length <= 0:
            continue
        segs.append(((x1, y1), (x2, y2), length, total))
        total += length
    span = total - 2 * clear
    if not segs or span <= 0 or spacing <= 0:
        return []
    n = max(1, round(span / spacing))
    step = span / n
    out = []
    gap = spacing * 0.25   # "on top of one already placed", in the caller's units
    i = 0
    for k in range(n):
        target = clear + step * (k + 0.5)
        while i < len(segs) - 1 and segs[i][3] + segs[i][2] < target:
            i += 1
        (x1, y1), (x2, y2), length, base = segs[i]
        f = (target - base) / length
        x, y = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
        if any(math.hypot(x - hx, y - hy) < gap for hx, hy, _ in out):
            continue
        out.append((x, y, math.atan2(y2 - y1, x2 - x1)))
    return out


def _apart_km(a, b) -> float:
    """Rough ground distance between two ``(lat, long)``, equirectangular. Only
    ever asked whether two points are metres apart, where the projection's error
    is nothing (see :data:`LOOP_MERGE_KM`)."""
    kx = 111.32 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((b[1] - a[1]) * kx, (b[0] - a[0]) * 110.574)


def _arrowhead(d, x, y, ang, L, fill):
    """A slim triangle centred on ``(x, y)`` and pointing along ``ang``."""
    ux, uy = math.cos(ang), math.sin(ang)
    px, py = -uy, ux
    bx, by = x - ux * L / 2, y - uy * L / 2
    w = L * 0.40
    d.polygon([(x + ux * L / 2, y + uy * L / 2),
               (bx + px * w, by + py * w),
               (bx - px * w, by - py * w)], fill=fill)


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


def _draw_trail(img, trail, project, accent, ink_saver):
    """Draw a trail's direction arrowheads and its markers.

    Returns ``(boxes, marks)`` — the footprints every marker occupies (so a
    basemap place name isn't printed under one) and ``(x, y, r, name)`` per
    *named* point, whose labels are drawn later by :func:`_draw_trail_labels`
    once the pins have claimed their space too.

    The three markers are deliberately different shapes rather than three
    colours: this figure is printed, sometimes in ink-saver, and read at a few
    centimetres wide. The **start** is a solid disc (the heaviest mark — it is
    where you set off), the **end** a ring (the same size, hollow: you finish
    where the line stops), and a **named point** a smaller solid disc, the same
    marker a drive's named stop wears elsewhere in the book. A line whose two
    ends land on the same pixel — a loop, an out-and-back — draws the start
    alone: two markers stacked would read as one badly drawn shape.
    """
    line = [project(lat, lon) for lat, lon in trail.line]
    if len(line) < 2:
        return [], []

    scaled = (1.0 if not ink_saver else 0.85)
    term_r = 5.5 * SCALE * scaled
    named_r = 3.5 * SCALE * scaled
    ring = 1.7 * SCALE
    head = ARROW_LEN * SCALE * scaled
    loop = _apart_km(trail.line[0], trail.line[-1]) <= LOOP_MERGE_KM

    named = [(project(lat, lon), name) for lat, lon, name in trail.waypoints]
    # A mark's screen angle comes from its measured walking bearing: north is
    # -y, so a bearing β points along β - 90° on the page, and the tick lies
    # across it at β.
    km_marks = [(project(lat, lon), km, math.radians(bearing - 90))
                for lat, lon, km, bearing in trail.km_marks]
    tick = KM_TICK_LEN * SCALE * scaled

    # An arrowhead behind a marker is a smudge under a disc, so it is dropped —
    # the same thing ``ARROW_CLEAR`` does for the two trailheads, applied to
    # everything that can sit anywhere along the line. Two cases this exists
    # for: an out-and-back's turnaround, which is the *middle* of the line so no
    # end-clearance protects the named point you walked all that way to; and a
    # distance tick, which crosses the line exactly where a head would run along
    # it.
    blocked = [(line[0], term_r + ring)]
    if not loop:
        blocked.append((line[-1], term_r + ring))
    blocked += [(pt, named_r + ring) for pt, _name in named]
    blocked += [(pt, tick * 1.5) for pt, _km, _ang in km_marks]
    spacing = ARROW_SPACING * SCALE * (ARROW_SPARSE if km_marks else 1)
    arrows = [(x, y, ang)
              for x, y, ang in arrows_along(line, spacing, ARROW_CLEAR * SCALE)
              if not any(math.hypot(x - bx, y - by) < radius + head * 0.6
                         for (bx, by), radius in blocked)]

    def paint(d, ss):
        # Distance ticks first, under everything: a white bar a shade wider than
        # the accent one, the same halo trick the arrowheads use — and an
        # arrowhead immediately past each one, pointing the way you were walking.
        # That pairing is what makes a doubled-back trail readable: the two legs
        # are drawn a few metres apart, so "3" alone doesn't say which of the
        # two lines it belongs to, while "3" with an arrow down the valley does.
        for (x, y), _km, walk in km_marks:
            across = walk + math.pi / 2
            dx, dy = math.cos(across) * tick / 2, math.sin(across) * tick / 2
            for width, colour in (((3.0 * SCALE) * ss, (255, 255, 255, 255)),
                                  ((1.6 * SCALE) * ss, accent + (255,))):
                d.line([((x - dx) * ss, (y - dy) * ss),
                        ((x + dx) * ss, (y + dy) * ss)],
                       fill=colour, width=round(width))
            ax = x + math.cos(walk) * (head * 0.5 + 1.5 * SCALE)
            ay = y + math.sin(walk) * (head * 0.5 + 1.5 * SCALE)
            _arrowhead(d, ax * ss, ay * ss, walk, (head + 1.6 * SCALE) * ss,
                       (255, 255, 255, 255))
            _arrowhead(d, ax * ss, ay * ss, walk, head * ss, accent + (255,))
        # Arrowheads: a white one a shade larger under an accent one, so the
        # head reads over the trail line it sits on (the line is the same accent)
        # and over the basemap either side of it.
        for x, y, ang in arrows:
            _arrowhead(d, x * ss, y * ss, ang, (head + 1.6 * SCALE) * ss,
                       (255, 255, 255, 255))
            _arrowhead(d, x * ss, y * ss, ang, head * ss, accent + (255,))
        for (x, y), _name in named:
            _disc(d, x * ss, y * ss, named_r * ss, ring * ss,
                  accent + (255,), ss)
        sx, sy = line[0]
        _disc(d, sx * ss, sy * ss, term_r * ss, ring * ss, accent + (255,), ss)
        if not loop:
            ex, ey = line[-1]
            _disc(d, ex * ss, ey * ss, term_r * ss, ring * ss, accent + (255,),
                  ss, hollow=True)

    img.alpha_composite(_ss_layer(img.size, paint))

    boxes = [_disc_box(line[0], term_r + ring)]
    if not loop:
        boxes.append(_disc_box(line[-1], term_r + ring))
    # Labels are drawn later (see `_draw_trail_labels`), once the pins have
    # claimed their space too. A named point is set bold at the size of a
    # basemap town; a distance number is smaller and regular — it is a
    # *measurement*, and reading as one keeps it from competing with the places.
    marks = []
    for (x, y), name in named:
        boxes.append(_disc_box((x, y), named_r + ring))
        marks.append((x, y, named_r + ring, name, 11, True, None))
    for (x, y), km, walk in km_marks:
        boxes.append(_disc_box((x, y), tick / 2))
        # the arrowhead past the tick, so a number isn't printed over it
        boxes.append(_disc_box((x + math.cos(walk) * (head * 0.5 + 1.5 * SCALE),
                                y + math.sin(walk) * (head * 0.5 + 1.5 * SCALE)),
                               head * 0.55))
        # The number goes on the **left of the way you were walking**. On an
        # out-and-back that separates the two legs for free: the return walks the
        # opposite bearing, so its left is the other side of the ground, and the
        # outbound numbers end up along one side of the path with the return's
        # along the other. Two numbers on the same side of two lines a few metres
        # apart is exactly what made a doubled-back trail unreadable.
        marks.append((x, y, tick / 2, str(km), KM_LABEL_PT, False,
                      walk - math.pi / 2))
    return boxes, marks


def _disc(d, cx, cy, r, ring, fill, ss, hollow: bool = False):
    """A white-ringed disc — solid, or hollow (white-centred) for the end mark."""
    d.ellipse([cx - r - ring, cy - r - ring, cx + r + ring, cy + r + ring],
              fill=(255, 255, 255, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    if hollow:
        h = r - 1.8 * SCALE * ss
        if h > 0:
            d.ellipse([cx - h, cy - h, cx + h, cy + h], fill=(255, 255, 255, 255))


def _disc_box(xy, r):
    x, y = xy
    return (x - r, y - r, x + r, y + r)


def _draw_trail_labels(img: Image.Image, marks, accent, taken: list) -> None:
    """Label a trail's named points and its distance marks, beside each marker.

    Placed by the same greedy, collision-checked rule as the basemap's own
    labels, and **before** them, so where a col's name and a hamlet's would
    collide the trail's wins — on a map of one trail, the trail's own points are
    what the reader came for. A label with nowhere to go is dropped rather than
    printed over something, exactly as a basemap label is; on an out-and-back
    that is what thins the distance numbers where the two legs run together, and
    losing one number to a legible figure is the right trade.

    ``marks`` arrive in draw order, which is *named points first*: they are the
    places, and a distance number is what yields when the two want one spot.
    Each carries an optional preferred direction to sit in — see
    :func:`_label_dirs`.
    """
    if not marks:
        return
    d = ImageDraw.Draw(img, "RGBA")
    for x, y, r, text, pt, bold, prefer in marks:
        font = _font(pt * SCALE, "DejaVuSans-Bold.ttf" if bold
                     else "DejaVuSans.ttf")
        pad = r + 3.5 * SCALE
        for ang in _label_dirs(prefer):
            dx, dy = math.cos(ang) * pad, math.sin(ang) * pad
            box = d.textbbox((x + dx, y + dy), text, font=font,
                             anchor=_anchor_for(ang))
            if (box[0] < 0 or box[1] < 0
                    or box[2] > img.width or box[3] > img.height):
                continue
            if any(_boxes_overlap(box, t, pad=2 * SCALE) for t in taken):
                continue
            taken.append(box)
            d.text((x + dx, y + dy), text, font=font, fill=accent,
                   anchor=_anchor_for(ang),
                   stroke_width=max(1, round(pt * SCALE * 0.13)),
                   stroke_fill=basemap.LABEL_HALO)
            break


def _label_dirs(prefer: float | None) -> list[float]:
    """Screen directions to try placing a label in, best first.

    Without a preference — a named point — it starts to the right, the reading
    direction, then left, above, below. With one it tries that direction and
    then its opposite before falling back on those four, so the preference is a
    *strong* hint rather than a rule: a number that would collide there still
    gets printed somewhere rather than dropped.
    """
    fallback = [0.0, math.pi, -math.pi / 2, math.pi / 2]
    if prefer is None:
        return fallback
    return [prefer, prefer + math.pi] + fallback


def _anchor_for(ang: float) -> str:
    """The Pillow text anchor that sets a label *away* from a point offset in
    direction ``ang`` — so it never overlaps the marker it belongs to, whichever
    way round the trail happens to run."""
    cx, cy = math.cos(ang), math.sin(ang)
    if abs(cx) >= abs(cy):
        return "lm" if cx > 0 else "rm"
    return "mt" if cy > 0 else "mb"


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
               route_nodes=None, legs=None, lang=None,
               trail: Trail | None = None) -> Image.Image:
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
    * ``trail`` — a walked line's own decoration: direction arrowheads, distinct
      start/end markers and its named points (see :class:`Trail`). Only a hike's
      trail map passes one.
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

    # a trail's own decoration, over its route line and under the pins: which way
    # you walk it, where it starts and ends, and the points its file names.
    trail_boxes, trail_marks = ([], [])
    if trail is not None:
        trail_boxes, trail_marks = _draw_trail(img, trail, project, accent,
                                               ink_saver)

    # pins: numbered teardrops, clustered ones fanned apart by rotation
    px = [project(lat, lon) for lat, lon in points]
    keep_clear = list(trail_boxes)
    if px:
        R = 15 * SCALE
        angles = pin_angles(px, head_r=R)
        font = _font(round(17 * SCALE * SS))
        pin_col = (255, 255, 255) if ink_saver else accent
        keep_clear += [_pin_box(x, y, R, ang, R * 0.22)
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
    # and skipped where a pin, a trail marker or a trail's own name already
    # claims the space.
    keep_clear.append(_attribution_box(img))
    _draw_trail_labels(img, trail_marks, accent, keep_clear)
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
