"""A hike's embedded GPX: decoding the base64 blob, parsing the track, the
figures measured off it, and how it reaches the model, the serializer, the
validator and the two renderers. All offline — a GPX travels inside the JSON."""

import base64
import gzip
import math

import pytest

from odysseyra_travelbook.models import (
    Itinerary,
    ItineraryError,
    decode_gpx,
    gpx_track,
    parse_gpx,
    to_dict,
)
from odysseyra_travelbook.models.gpx import (
    MAP_MAX_POINTS,
    MAX_KM_MARKS,
    MAX_NAMED_POINTS,
    PROFILE_POINTS,
)
from odysseyra_travelbook.validate import validate_text


# -- fixtures ----------------------------------------------------------------

def gpx_xml(points, namespaced=True, tag="trkpt"):
    """A GPX document over ``points`` — ``(lat, lon)`` or ``(lat, lon, ele)``."""
    body = []
    for p in points:
        ele = f"<ele>{p[2]}</ele>" if len(p) > 2 else ""
        body.append(f'<{tag} lat="{p[0]}" lon="{p[1]}">{ele}</{tag}>')
    ns = ' xmlns="http://www.topografix.com/GPX/1/1"' if namespaced else ""
    inner = "".join(body)
    if tag == "trkpt":
        inner = f"<trk><trkseg>{inner}</trkseg></trk>"
    elif tag == "rtept":
        inner = f"<rte>{inner}</rte>"
    return f'<?xml version="1.0"?><gpx version="1.1"{ns}>{inner}</gpx>'


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def ridge(n=300, gain=400.0, jitter=0.0):
    """A straight climb-and-descend track running due north, with an optional
    metre-scale altimeter jitter laid over it."""
    out = []
    for i in range(n):
        f = i / (n - 1)
        ele = 1000 + gain * math.sin(math.pi * f) + jitter * math.sin(i * 1.7)
        out.append((round(42.7 + 0.02 * f, 6), -0.14, round(ele, 1)))
    return out


TRACK_B64 = b64(gpx_xml(ridge()))


def hike_doc(gpx=TRACK_B64, **hike):
    """A one-day itinerary whose only activity is a hike (optionally with GPX)."""
    act = {"type": "hike", "name": "Ridge", "duration": "3h", **hike}
    if gpx is not None:
        act["gpx"] = gpx
    return {"travel_description": {"title": "T"}, "defaults": {},
            "days": [{"title": "D", "date": "2026-06-01", "activities": [act]}]}


# -- decoding ----------------------------------------------------------------

def test_decode_accepts_plain_gzip_data_uri_and_wrapped_base64():
    xml = gpx_xml(ridge(4))
    raw = b64(xml)
    assert decode_gpx(raw) == xml
    assert decode_gpx(base64.b64encode(gzip.compress(xml.encode())).decode()) == xml
    assert decode_gpx(f"data:application/gpx+xml;base64,{raw}") == xml
    # `base64` the command wraps its output at 76 columns
    wrapped = "\n".join(raw[i:i + 76] for i in range(0, len(raw), 76))
    assert decode_gpx(wrapped) == xml


def test_decode_rejects_what_is_not_a_gpx():
    for bad, hint in (
        (None, "base64 string"),
        ("", "empty"),
        ("not base64 at all!", "not valid base64"),
        (b64("plain text, no XML here"), "not parseable XML"),
    ):
        with pytest.raises(ItineraryError) as exc:
            gpx_track(bad)
        assert hint in str(exc.value)


def test_decode_reports_a_gzip_stream_that_will_not_inflate():
    # gzip magic, then nonsense — decoding must name the real problem
    with pytest.raises(ItineraryError) as exc:
        gpx_track(base64.b64encode(b"\x1f\x8b" + b"\x00" * 40).decode())
    assert "inflate" in str(exc.value)


def test_a_gpx_with_fewer_than_two_points_holds_no_track():
    with pytest.raises(ItineraryError) as exc:
        gpx_track(b64(gpx_xml([(42.7, -0.14, 1000)])))
    assert "no track" in str(exc.value)


# -- parsing -----------------------------------------------------------------

def test_parses_track_route_and_waypoints_with_or_without_a_namespace():
    for tag in ("trkpt", "rtept", "wpt"):
        for namespaced in (True, False):
            track = parse_gpx(gpx_xml(ridge(5), namespaced=namespaced, tag=tag))
            assert len(track.points) == 5, (tag, namespaced)


def test_track_points_win_over_route_points_and_waypoints():
    """A recording is what happened; a route or waypoint list is a plan."""
    xml = ('<?xml version="1.0"?><gpx><wpt lat="1" lon="1"/><wpt lat="2" lon="2"/>'
           '<wpt lat="3" lon="3"/>'
           '<trk><trkseg><trkpt lat="42.7" lon="-0.1"/>'
           '<trkpt lat="42.8" lon="-0.1"/></trkseg></trk></gpx>')
    assert parse_gpx(xml).points == [(42.7, -0.1), (42.8, -0.1)]


def test_segments_are_one_continuous_track():
    """A pause in the recording is a gap in time, not a gap in the trail."""
    xml = ('<?xml version="1.0"?><gpx><trk>'
           '<trkseg><trkpt lat="42.7" lon="-0.1"/><trkpt lat="42.71" lon="-0.1"/></trkseg>'
           '<trkseg><trkpt lat="42.72" lon="-0.1"/><trkpt lat="42.73" lon="-0.1"/></trkseg>'
           '</trk></gpx>')
    assert len(parse_gpx(xml).points) == 4


def test_points_without_usable_coordinates_are_skipped():
    xml = ('<?xml version="1.0"?><gpx><trk><trkseg>'
           '<trkpt lat="42.7" lon="-0.1"/><trkpt lat="oops" lon="-0.1"/>'
           '<trkpt lon="-0.1"/><trkpt lat="42.8" lon="-0.1"/>'
           '</trkseg></trk></gpx>')
    assert parse_gpx(xml).points == [(42.7, -0.1), (42.8, -0.1)]


# -- the named points --------------------------------------------------------

def with_wpts(points, wpts, tag="trkpt"):
    """``gpx_xml`` plus a leading block of ``<wpt>``s — ``(lat, lon, name)``,
    a ``None`` name standing for one with no ``<name>`` at all."""
    block = "".join(
        f'<wpt lat="{a}" lon="{b}">' + (f"<name>{n}</name>" if n else "") + "</wpt>"
        for a, b, n in wpts)
    xml = gpx_xml(points, tag=tag)
    head, _, body = xml.partition("<gpx")           # insert inside <gpx …>, ahead
    open_tag, _, rest = body.partition(">")         # of the <trk>/<rte> that follows
    return f"{head}<gpx{open_tag}>{block}{rest}"


def test_a_named_waypoint_becomes_a_point_on_the_trail():
    track = parse_gpx(with_wpts(ridge(50), [(42.71, -0.1395, "Col de Riou")]))
    assert [(w.name, w.lat, w.long) for w in track.waypoints] == [
        ("Col de Riou", 42.71, -0.1395)]
    # and it doesn't touch the line, which is the recording
    assert len(track.points) == 50


def test_an_unnamed_waypoint_carries_nothing():
    """There is no label to print beside it, and the line already says where the
    trail goes."""
    track = parse_gpx(with_wpts(ridge(50), [(42.71, -0.14, None)]))
    assert track.waypoints == []


def test_a_waypoint_at_either_trailhead_is_dropped():
    """The start and end markers already mark those two points, so "Parking"
    printed over the start marker only says what the marker says."""
    ridge_pts = ridge(50)
    ends = [(ridge_pts[0][0], ridge_pts[0][1], "Parking"),
            (ridge_pts[-1][0], ridge_pts[-1][1], "Summit cairn"),
            (42.71, -0.14, "Col")]
    assert [w.name for w in parse_gpx(with_wpts(ridge_pts, ends)).waypoints] == ["Col"]


def test_a_file_whose_line_is_its_waypoints_names_none_of_them():
    """Those points *are* the trail, so pinning each would label every bend."""
    pts = [(42.7 + 0.001 * i, -0.14) for i in range(6)]
    xml = ('<?xml version="1.0"?><gpx>' + "".join(
        f'<wpt lat="{a}" lon="{b}"><name>P{i}</name></wpt>'
        for i, (a, b) in enumerate(pts)) + "</gpx>")
    track = parse_gpx(xml)
    assert len(track.points) == 6 and track.waypoints == []


def test_a_turn_by_turn_export_contributes_no_named_points_at_all():
    """Above the cap **none** are kept rather than an arbitrary prefix: a routing
    export names every instruction, and its first fifteen left turns are not the
    landmarks this field is for."""
    turns = [(42.71 + 0.0005 * i, -0.14, f"Turn {i}")
             for i in range(MAX_NAMED_POINTS + 1)]
    assert parse_gpx(with_wpts(ridge(50), turns)).waypoints == []
    # one fewer and they are a plausible set of landmarks, so they are kept
    assert len(parse_gpx(with_wpts(ridge(50), turns[:-1])).waypoints) == MAX_NAMED_POINTS


# -- the distance marks ------------------------------------------------------

def test_a_whole_kilometre_is_marked_on_the_ground():
    """The marks tie the two figures together, so they are placed once, here:
    the map ticks the coordinate and the profile ticks the number."""
    track = parse_gpx(gpx_xml(ridge(400)))          # ~2.2 km due north
    assert [m.km for m in track.km_marks] == [1, 2]
    # each one sits on the track, in order, between its neighbours' latitudes
    lats = [m.lat for m in track.km_marks]
    assert lats == sorted(lats)
    assert track.points[0][0] < lats[0] < track.points[-1][0]


def test_marks_stop_short_of_the_finish():
    """One landing on the end would print a number over the marker that already
    says the trail stops there — and the axis states the full length anyway."""
    track = parse_gpx(gpx_xml(ridge(400)))
    assert track.distance_km == pytest.approx(2.2, abs=0.1)
    assert all(m.km < track.distance_km for m in track.km_marks)


def test_a_walk_under_a_kilometre_is_not_marked_at_all():
    short = [(42.7 + 0.0001 * i, -0.14, 1000.0) for i in range(20)]   # ~200 m
    track = parse_gpx(gpx_xml(short))
    assert track.distance_km < 1 and track.km_marks == []


def test_the_step_coarsens_so_neither_figure_drowns_in_numbers():
    """Every kilometre up to 15 — which covers essentially every day hike — and
    past that the step grows rather than the count."""
    def step_of(km_long):
        n = 400
        pts = [(42.0 + (km_long / 111.0) * i / (n - 1), -0.14, 1000.0)
               for i in range(n)]
        kms = [m.km for m in parse_gpx(gpx_xml(pts)).km_marks]
        assert kms[0] == kms[1] - kms[0], kms          # the first mark is one step
        steps = {b - a for a, b in zip(kms, kms[1:])}
        assert len(steps) == 1, kms                    # evenly spaced throughout
        assert len(kms) <= MAX_KM_MARKS, kms
        return steps.pop()

    assert step_of(9) == 1
    assert step_of(14) == 1        # a long day hike, still every kilometre
    assert step_of(24) == 2
    assert step_of(60) == 5
    assert step_of(400) == 50


def test_a_mark_carries_the_direction_you_were_walking_in():
    """Degrees clockwise from north, measured off the recording — the map draws
    an arrowhead by it."""
    north = parse_gpx(gpx_xml(ridge(400)))
    assert all(m.bearing == pytest.approx(0, abs=1) for m in north.km_marks)
    east = [(42.7, -0.14 + 0.0004 * i, 1000.0) for i in range(400)]
    assert all(m.bearing == pytest.approx(90, abs=1)
               for m in parse_gpx(gpx_xml(east)).km_marks)


def test_a_doubled_back_track_measures_opposite_bearings():
    """The whole reason the bearing is measured here rather than inferred from
    the drawn line: an out-and-back's two legs are metres apart, so the *nearest*
    point of the line at a mark can be on the other leg — the direction you
    didn't walk. Distance along the recording has no such ambiguity."""
    up = ridge(300)
    track = parse_gpx(gpx_xml(up + up[::-1]))
    half = track.distance_km / 2
    there = [m.bearing for m in track.km_marks if m.km < half - 0.2]
    back = [m.bearing for m in track.km_marks if m.km > half + 0.2]
    assert there and back
    assert all(b == pytest.approx(0, abs=2) for b in there)      # due north
    assert all(b == pytest.approx(180, abs=2) for b in back)     # due south


def test_an_out_and_back_numbers_the_same_ground_twice():
    """`km` is distance *walked*, which is the profile's own x axis — so at 2 km
    you were on the way up and at 6 km on the way down, and both figures say so.
    """
    up = ridge(200)
    track = parse_gpx(gpx_xml(up + up[::-1]))
    kms = [m.km for m in track.km_marks]
    assert kms == sorted(kms) and len(kms) >= 3
    # a mark from the second half sits back down among the first half's latitudes
    half = track.distance_km / 2
    there = [m for m in track.km_marks if m.km < half]
    back = [m for m in track.km_marks if m.km > half]
    assert there and back
    assert min(m.lat for m in back) < max(m.lat for m in there)


# -- measurement -------------------------------------------------------------

def test_distance_is_measured_over_the_track():
    # 0.02° of latitude ≈ 2.22 km, walked straight north
    track = parse_gpx(gpx_xml(ridge(100)))
    assert track.distance_km == pytest.approx(2.22, abs=0.03)


def test_climb_and_extremes_come_from_the_elevations():
    track = parse_gpx(gpx_xml(ridge(300, gain=400)))
    assert track.ascent_m == pytest.approx(400, abs=15)
    assert track.descent_m == pytest.approx(400, abs=15)
    assert track.min_elevation_m == pytest.approx(1000, abs=5)
    assert track.max_elevation_m == pytest.approx(1400, abs=5)


def test_altimeter_jitter_does_not_inflate_the_climb():
    """The whole point of the smoothing + hysteresis: a metre-scale wobble on
    every sample must not add up to hundreds of phantom metres of ascent."""
    clean = parse_gpx(gpx_xml(ridge(400, gain=300, jitter=0)))
    noisy = parse_gpx(gpx_xml(ridge(400, gain=300, jitter=4)))
    assert noisy.ascent_m == pytest.approx(clean.ascent_m, abs=40)


def test_a_gpx_without_elevations_has_no_profile():
    track = parse_gpx(gpx_xml([(42.7 + i * 0.001, -0.14) for i in range(20)]))
    assert track.has_elevation is False
    assert track.profile == []
    assert (track.ascent_m, track.descent_m) == (None, None)
    assert track.distance_km > 0  # the line is still measurable and drawable


def test_a_partial_elevation_series_is_no_series_at_all():
    """Half the points having an altitude would make every derived figure a
    guess, so a gap means no profile rather than a made-up one."""
    points = [(42.7, -0.14, 1000), (42.71, -0.14), (42.72, -0.14, 1100)]
    assert parse_gpx(gpx_xml(points)).has_elevation is False


def test_the_profile_is_resampled_evenly_by_distance():
    track = parse_gpx(gpx_xml(ridge(500)))
    assert len(track.profile) == PROFILE_POINTS
    xs = [p[0] for p in track.profile]
    assert xs[0] == 0 and xs[-1] == pytest.approx(track.distance_km, abs=0.002)
    assert xs == sorted(xs)
    steps = [b - a for a, b in zip(xs, xs[1:])]
    assert max(steps) - min(steps) < 0.002  # evenly spaced


def test_a_long_recording_is_simplified_for_the_map_but_not_for_the_figures():
    long_track = parse_gpx(gpx_xml(ridge(4000)))
    assert long_track.point_count == 4000
    assert len(long_track.points) <= MAP_MAX_POINTS
    # the simplification keeps the ends, so the line still starts and finishes
    # where the walk did
    assert long_track.points[0][0] == pytest.approx(42.7, abs=1e-6)
    assert long_track.points[-1][0] == pytest.approx(42.72, abs=1e-6)
    # and the distance is still the full-resolution one
    assert long_track.distance_km == pytest.approx(2.22, abs=0.03)


def test_a_short_track_is_left_alone():
    track = parse_gpx(gpx_xml(ridge(120)))
    assert len(track.points) == 120


def test_bounds_cover_the_track():
    track = parse_gpx(gpx_xml([(42.7, -0.2), (42.9, -0.1), (42.8, -0.3)]))
    assert track.bounds == ((42.7, -0.3), (42.9, -0.1))


# -- the model ---------------------------------------------------------------

def test_a_hike_parses_its_gpx_into_a_track():
    hike = Itinerary.from_dict(hike_doc()).days[0].activities[0]
    assert hike.track is not None
    assert hike.gpx == TRACK_B64


def test_the_track_fills_in_a_missing_distance_and_elevation():
    hike = Itinerary.from_dict(hike_doc()).days[0].activities[0]
    assert hike.distance_km == pytest.approx(2.2, abs=0.1)
    assert hike.elevation_m == pytest.approx(400, abs=15)


def test_explicit_figures_win_over_the_recording():
    """So you can quote the guidebook's round numbers over the GPS's."""
    hike = Itinerary.from_dict(
        hike_doc(distance_km=6, elevation_m=350)).days[0].activities[0]
    assert (hike.distance_km, hike.elevation_m) == (6, 350)


def test_a_gpx_without_elevations_leaves_the_elevation_unset():
    doc = hike_doc(b64(gpx_xml([(42.7 + i * 0.001, -0.14) for i in range(20)])))
    hike = Itinerary.from_dict(doc).days[0].activities[0]
    assert hike.distance_km is not None
    assert hike.elevation_m is None


def test_a_hike_with_no_gpx_has_no_track():
    hike = Itinerary.from_dict(hike_doc(gpx=None)).days[0].activities[0]
    assert hike.track is None and hike.gpx == ""


def test_an_unusable_gpx_is_an_itinerary_error():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict(hike_doc("not base64 at all!"))


def test_include_hike_maps_defaults_on_and_can_be_switched_off():
    assert Itinerary.from_dict(hike_doc()).include_hike_maps is True
    doc = hike_doc()
    doc["defaults"]["include_hike_maps"] = False
    assert Itinerary.from_dict(doc).include_hike_maps is False


# -- the resolved contract ---------------------------------------------------

def _hike_out(doc):
    return to_dict(Itinerary.from_dict(doc))["days"][0]["activities"][0]


def test_the_resolved_hike_carries_the_derived_track_and_the_file():
    out = _hike_out(hike_doc())
    track = out["track"]
    assert "gpx" not in out          # not on the activity …
    assert track["gpx"] == TRACK_B64  # … but inside the track, for the download
    assert len(track["points"]) == 300 and track["points"][0][1] == -0.14
    assert len(track["profile"]) == PROFILE_POINTS
    assert track["ascent_m"] == pytest.approx(400, abs=15)
    assert track["point_count"] == 300
    assert track["bounds"][0][1] == -0.14
    assert track["waypoints"] == []      # this file names nothing


def test_the_resolved_track_carries_the_named_points_for_both_renderers():
    doc = hike_doc(b64(with_wpts(ridge(50), [(42.71, -0.1395, "Col de Riou")])))
    assert _hike_out(doc)["track"]["waypoints"] == [
        {"name": "Col de Riou", "lat": 42.71, "long": -0.1395}]


def test_the_resolved_track_carries_the_distance_marks():
    """Both figures draw them, and the profile needs only the number while the
    map needs the point — so the resolved mark carries both."""
    marks = _hike_out(hike_doc())["track"]["km_marks"]
    assert [m["km"] for m in marks] == [1, 2]
    assert all(set(m) == {"km", "lat", "long", "bearing"} for m in marks)


def test_switching_hike_maps_off_leaves_the_track_out_of_the_payload():
    """Kilobytes of geometry (and the file behind them) shouldn't ride into a
    consumer that won't draw or offer either."""
    doc = hike_doc()
    doc["defaults"]["include_hike_maps"] = False
    assert _hike_out(doc)["track"] is None
    # …but the figures it measured are still the hike's own
    assert _hike_out(doc)["distance_km"] == pytest.approx(2.2, abs=0.1)


def test_the_file_rides_along_verbatim_however_it_was_encoded():
    """The viewer's "(Get GPX track)" link hands back what was attached, so the
    payload must not normalise the blob on the way through — a gzipped one stays
    gzipped and the browser inflates it."""
    gzipped = base64.b64encode(gzip.compress(gpx_xml(ridge(50)).encode())).decode()
    assert _hike_out(hike_doc(gzipped))["track"]["gpx"] == gzipped


def test_a_hike_with_no_gpx_resolves_to_a_null_track():
    assert _hike_out(hike_doc(gpx=None))["track"] is None


def test_the_switch_is_reported_alongside_the_other_map_settings():
    data = to_dict(Itinerary.from_dict(hike_doc()))
    assert data["maps"]["include_hike_maps"] is True
    # independent of the trip-wide map switch, which stays off by default
    assert data["maps"]["include_in_render"] is False


# -- validation --------------------------------------------------------------

def _messages(doc, lang="en"):
    import json
    return [f.message for f in validate_text(json.dumps(doc), lang)]


def test_the_validator_reports_a_gpx_it_cannot_decode():
    msgs = _messages(hike_doc("not base64 at all!"))
    assert any("'gpx' is invalid" in m and "not valid base64" in m for m in msgs)


def test_a_long_blob_is_elided_rather_than_quoted_in_full():
    """Quoting a whole base64 track would bury its own message."""
    msgs = _messages(hike_doc("A" * 5000 + "!"))
    bad = next(m for m in msgs if "'gpx' is invalid" in m)
    assert "..." in bad and len(bad) < 400


def test_the_validator_notes_a_gpx_with_no_elevations():
    doc = hike_doc(b64(gpx_xml([(42.7 + i * 0.001, -0.14) for i in range(20)])))
    assert any("carries no elevations" in m for m in _messages(doc))


def test_the_validator_says_when_a_files_named_points_were_all_dropped():
    """Every other filter loses something the file didn't really say; the cap
    loses points it *did*, so this is the one that has to be reported."""
    turns = [(42.71 + 0.0005 * i, -0.14, f"Turn {i}")
             for i in range(MAX_NAMED_POINTS + 1)]
    msgs = _messages(hike_doc(b64(with_wpts(ridge(50), turns))))
    assert any(f"names {MAX_NAMED_POINTS + 1} waypoints" in m
               and "none of them are marked" in m for m in msgs)
    # a file inside the cap says nothing
    inside = _messages(hike_doc(b64(with_wpts(ridge(50), turns[:2]))))
    assert not any("waypoints" in m for m in inside)


def test_the_validator_notes_a_gpx_that_is_switched_off():
    doc = hike_doc()
    doc["defaults"]["include_hike_maps"] = False
    assert any("'include_hike_maps' is off" in m for m in _messages(doc))


def test_a_gpx_answers_the_missing_distance_and_elevation_warning():
    with_gpx = _messages(hike_doc())
    assert not any("should give a duration" in m for m in with_gpx)
    without = _messages(hike_doc(gpx=None))
    warning = next(m for m in without if "should give a duration" in m)
    assert "distance_km" in warning and "elevation_m" in warning


def test_a_gpx_without_elevations_still_leaves_the_elevation_wanted():
    doc = hike_doc(b64(gpx_xml([(42.7 + i * 0.001, -0.14) for i in range(20)])))
    warning = next(m for m in _messages(doc) if "should give a duration" in m)
    assert warning.endswith("missing: elevation_m.")  # the distance came free
