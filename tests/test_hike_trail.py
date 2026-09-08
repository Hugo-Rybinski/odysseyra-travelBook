"""A hike trail map's own decoration: the direction arrowheads, the start/finish
markers and the named points its GPX carries.

The line alone is a shape with no story — an out-and-back and a loop look alike,
neither says which end you set off from, and the col you turn at is just a bend —
so this covers the three things `maps/render.py`'s ``Trail`` adds on top of it.
The drawing itself is pixels, and asserting on those would pin nothing worth
pinning; what the tests hold is the *geometry and the decisions* — where the
heads go, how many, which markers exist — plus that ``render_hike_map`` actually
asks for them. `web/src/render/DayMapGL.tsx` implements the same rules for the
interactive map, and there is no JS test runner, so this file is the contract
both sides answer to.
"""

import math

import pytest

from odysseyra_travelbook.maps import build as mapbuild
from odysseyra_travelbook.maps.render import (
    ARROW_CLEAR,
    ARROW_LEN,
    ARROW_SPACING,
    ARROW_SPARSE,
    LOOP_MERGE_KM,
    SCALE,
    Trail,
    arrows_along,
)
from odysseyra_travelbook.models import parse_gpx


# -- fixtures ----------------------------------------------------------------

class _NoCache:
    """Enough of a ``Cache`` for a stubbed renderer: nothing is ever fetched."""

    tiles = None

    def save(self):
        pass


def straight(n=400, dx=0.0):
    """A due-north track, optionally drifting east, with elevations."""
    return [(42.7 + 0.03 * i / (n - 1), -0.14 + dx * i / (n - 1), 1000.0 + i)
            for i in range(n)]


def gpx_of(points, wpts=()):
    body = "".join(f'<trkpt lat="{a:.6f}" lon="{b:.6f}"><ele>{c}</ele></trkpt>'
                   for a, b, c in points)
    block = "".join(f'<wpt lat="{a}" lon="{b}"><name>{n}</name></wpt>'
                    for a, b, n in wpts)
    return ('<?xml version="1.0"?><gpx version="1.1">'
            f'{block}<trk><trkseg>{body}</trkseg></trk></gpx>')


@pytest.fixture
def drawn(monkeypatch):
    """Capture what ``render_hike_map`` asks ``render_map`` to draw."""
    seen = {}

    def fake(all_coords, routes, points, accent, tiles_dir, **kw):
        from PIL import Image
        seen.update(all_coords=all_coords, routes=routes, points=points, **kw)
        return Image.new("RGB", (10, 10), "white")

    monkeypatch.setattr(mapbuild, "render_map", fake)
    return seen


# -- where the arrowheads go -------------------------------------------------

def test_arrowheads_are_spread_evenly_and_clear_of_both_ends():
    line = [(0.0, 0.0), (0.0, 600.0)]      # 600 px of projected line
    heads = arrows_along(line, spacing=100, clear=50)
    assert len(heads) == 5                  # (600 - 2*50) / 100
    ys = [y for _x, y, _a in heads]
    assert ys[0] >= 50 and ys[-1] <= 550    # nothing under a trailhead marker
    gaps = [b - a for a, b in zip(ys, ys[1:])]
    assert all(g == pytest.approx(gaps[0]) for g in gaps)


def test_the_heads_point_along_the_line():
    heads = arrows_along([(0.0, 0.0), (400.0, 0.0)], spacing=100, clear=20)
    assert all(a == pytest.approx(0.0) for _x, _y, a in heads)      # due east
    heads = arrows_along([(0.0, 0.0), (0.0, 400.0)], spacing=100, clear=20)
    assert all(a == pytest.approx(math.pi / 2) for _x, _y, a in heads)  # due south


def test_a_line_with_no_room_for_one_head_gets_none():
    """The two trailhead markers still say where it begins and ends."""
    assert arrows_along([(0.0, 0.0), (0.0, 30.0)], spacing=100, clear=20) == []


def test_a_doubled_back_line_keeps_the_outbound_heads_only():
    """An out-and-back is one line walked twice, so its outbound and return heads
    fall on the same stretch pointing opposite ways. Drawing both turned every
    doubled-back section into a row of little butterflies."""
    out_and_back = [(0.0, y) for y in range(0, 601, 10)]
    out_and_back += [(0.0, y) for y in range(590, -1, -10)]
    heads = arrows_along(out_and_back, spacing=100, clear=50)
    # every surviving head walks *up* the line (positive y, its file order)
    assert heads and all(a == pytest.approx(math.pi / 2) for _x, _y, a in heads)


def test_the_spacing_is_a_target_not_a_pitch():
    """The heads are spread over the whole usable length: a fixed pitch would
    leave a ragged remainder at the far end, which on a line whose only job is to
    say "this way" reads as the arrows having run out. So the count is the
    spacing rounded to fit, and the step lands wherever that puts it."""
    for length, expected in ((260, 2), (250, 2), (240, 2), (200, 1)):
        span = length - 60
        heads = arrows_along([(0.0, 0.0), (0.0, float(length))],
                             spacing=100, clear=30)
        assert len(heads) == expected, length
        ys = [y for _x, y, _a in heads]
        assert ys[0] == pytest.approx(30 + span / (2 * expected))


# -- what render_hike_map asks for -------------------------------------------

def test_the_trail_decoration_reaches_the_renderer(drawn):
    track = parse_gpx(gpx_of(straight(), wpts=[(42.715, -0.14, "Col de Riou")]))
    assert mapbuild.render_hike_map(track, "#2f5d7c", _NoCache()) is not None
    trail = drawn["trail"]
    assert isinstance(trail, Trail)
    assert trail.line == track.points
    assert trail.waypoints == [(42.715, -0.14, "Col de Riou")]
    # the two identical route-node discs it replaces are gone
    assert not drawn.get("route_nodes")


def test_the_extent_is_the_line_not_its_named_points(drawn):
    """A `<wpt>` is a place *on* the trail, so framing the trail frames it — and
    a stray one named miles away must not zoom the trail out."""
    track = parse_gpx(gpx_of(straight(), wpts=[(45.0, 3.0, "Somewhere else")]))
    mapbuild.render_hike_map(track, "#2f5d7c", _NoCache())
    assert drawn["all_coords"] == track.points


def test_a_hike_with_no_named_points_draws_the_bare_trail(drawn):
    track = parse_gpx(gpx_of(straight()))
    mapbuild.render_hike_map(track, "#2f5d7c", _NoCache())
    assert drawn["trail"].waypoints == []
    assert drawn["trail"].km_marks                  # …but it still has a scale


def test_the_distance_marks_reach_the_renderer_as_the_model_placed_them(drawn):
    """The map's ticks and the profile's must be the same kilometres, so neither
    renderer gets to choose them — `maps/build.py` passes the model's through,
    walking bearing included (which the renderer must not re-derive: see
    `test_a_doubled_back_track_measures_opposite_bearings`)."""
    track = parse_gpx(gpx_of(straight()))
    mapbuild.render_hike_map(track, "#2f5d7c", _NoCache())
    assert drawn["trail"].km_marks == [(m.lat, m.long, m.km, m.bearing)
                                       for m in track.km_marks]
    assert [km for _lat, _long, km, _b in drawn["trail"].km_marks] == [1, 2, 3]


# -- which side a distance number sits on ------------------------------------

def test_a_number_prefers_the_left_of_the_way_you_walked():
    """Which is what pulls an out-and-back's two sets of numbers apart. The
    return leg walks the opposite bearing, so its left is the other side of the
    ground: the outbound numbers end up along one side of the path and the
    return's along the other, and a "3" no longer belongs to either of two lines
    a few metres apart."""
    from odysseyra_travelbook.maps.render import _anchor_for, _label_dirs

    def side(bearing_deg):
        """The unit screen vector the label is first tried in, walking that
        bearing (`_draw_trail` hands `walk - 90°`, walk being `bearing - 90°`)."""
        walk = math.radians(bearing_deg - 90)
        ang = _label_dirs(walk - math.pi / 2)[0]
        return (round(math.cos(ang), 6), round(math.sin(ang), 6))

    assert side(0) == (-1.0, 0.0)      # walking north → the number sits west
    assert side(180) == (1.0, 0.0)     # walking back south → it sits east
    assert side(90) == (0.0, -1.0)     # walking east → above (screen y is down)
    # …and the text is anchored so it sets away from the tick either way
    assert _anchor_for(math.pi) == "rm"
    assert _anchor_for(0.0) == "lm"
    assert _anchor_for(math.pi / 2) == "mt"
    assert _anchor_for(-math.pi / 2) == "mb"


def test_a_preference_is_a_hint_not_a_rule():
    """A number that can't go on its side still gets printed somewhere — the
    four plain directions stay on the end of the list — because a dropped
    kilometre makes the scale a lie."""
    from odysseyra_travelbook.maps.render import _label_dirs

    assert len(_label_dirs(1.0)) == 6
    assert _label_dirs(None) == _label_dirs(1.0)[2:]


# -- the loop rule -----------------------------------------------------------

def test_a_closed_line_is_walked_back_to_where_it_started():
    """A loop and an out-and-back both finish at the start, so the figure draws
    the start marker alone — two markers stacked read as one badly drawn shape.
    `LOOP_MERGE_KM` is a *ground* distance, so the same hike decides the same way
    on paper and on screen (DayMapGL.tsx applies the identical threshold)."""
    from odysseyra_travelbook.maps.render import _apart_km

    assert _apart_km((42.7, -0.14), (42.7, -0.14)) == 0.0
    # ~11 m apart: a GPX loop rarely closes to the metre
    assert _apart_km((42.7, -0.14), (42.7001, -0.14)) <= LOOP_MERGE_KM
    # ~110 m apart: a one-way trail, and it earns its finish marker
    assert _apart_km((42.7, -0.14), (42.701, -0.14)) > LOOP_MERGE_KM


# -- the drawing itself ------------------------------------------------------

def test_the_decorated_map_is_still_an_image(monkeypatch):
    """A smoke test over the real drawing code, on a blank basemap: every trail
    overlay is composited for real, at both ink levels and over four shapes of
    line. It must not raise, whatever the geometry — including a degenerate one,
    since a hand-written GPX can hold anything."""
    from PIL import Image

    from odysseyra_travelbook.maps import basemap
    from odysseyra_travelbook.maps.render import render_map

    monkeypatch.setattr(
        basemap, "render_basemap",
        lambda z, left, top, w, h, tiles, scale=1, lang=None: (
            Image.new("RGBA", (w * scale, h * scale), (255, 255, 255, 255)), []))

    line = [(42.7 + 0.001 * i, -0.14) for i in range(40)]
    marks = [(42.71, -0.14, 1, 0.0), (42.72, -0.14, 2, 183.5)]
    for trail in (Trail(line=line),
                  Trail(line=line, waypoints=[(42.72, -0.14, "Col de Riou")]),
                  Trail(line=line, km_marks=marks),
                  Trail(line=line, waypoints=[(42.72, -0.14, "Col")],
                        km_marks=marks),
                  Trail(line=line + line[::-1], km_marks=marks),  # out-and-back
                  Trail(line=[line[0], line[0]], km_marks=marks)):  # degenerate
        for ink_saver in (False, True):
            img = render_map(line, [line], [], (47, 93, 124), None,
                             map_w=300, map_h=200, ink_saver=ink_saver,
                             trail=trail)
            assert img.size == (300 * SCALE, 200 * SCALE)


def test_the_constants_stay_in_a_sane_relation():
    """The clear span at each end has to hold a head, or the first arrow would be
    drawn under the start marker."""
    assert ARROW_CLEAR >= ARROW_LEN
    assert ARROW_SPACING > ARROW_LEN
    # With a numbered scale on the line the heads step back — but only a little,
    # because an out-and-back has already lost half of them to the doubled-back
    # rule and a big factor there leaves a trail with one arrow on it.
    assert 1 < ARROW_SPARSE < 2
