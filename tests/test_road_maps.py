"""A drive's own map pins (``display_*_on_maps``) and a leg's ``gpx``.

Two features that meet on the day map: which of a road's points earn a numbered
pin, and where a leg's drawn line comes from. Both are offline — the routing seam
is stubbed and a GPX travels inside the JSON.
"""

import base64
import json

import pytest

from odysseyra_travelbook.maps import build as mapbuild
from odysseyra_travelbook.models import Itinerary, ItineraryError, gpx_track, route_gpx, to_dict
from odysseyra_travelbook.validate import validate_text


# -- fixtures ----------------------------------------------------------------

def gpx_b64(points) -> str:
    body = "".join(f'<trkpt lat="{lat}" lon="{long}"/>' for lat, long in points)
    xml = ('<?xml version="1.0"?><gpx version="1.1">'
           f"<trk><trkseg>{body}</trkseg></trk></gpx>")
    return base64.b64encode(xml.encode()).decode()


# A recording that bulges well north of the straight A → B line, so "was the
# track used?" is answerable from the geometry alone.
TRACK = gpx_b64([(1.0, 1.0), (1.9, 1.4), (2.0, 2.0)])

LEG_AB = {"start_location": "A", "start_coordinate": {"lat": 1, "long": 1},
          "end_location": "B", "end_coordinate": {"lat": 2, "long": 2}}
LEG_BC = {"end_location": "C", "end_coordinate": {"lat": 3, "long": 3}}
LEG_CD = {"end_location": "D", "end_coordinate": {"lat": 4, "long": 4}}


def doc(*activities, **road):
    """A one-day, maps-on itinerary whose first activity is the road under test."""
    return {
        "travel_description": {"title": "T", "start_date": "2026-01-01"},
        "defaults": {"include_maps_in_render": True},
        "days": [{"title": "D", "activities": [
            {"type": "road", "legs": road.pop("legs", [LEG_AB, LEG_BC, LEG_CD]),
             **road},
            *activities,
        ]}],
    }


def road_of(document):
    return Itinerary.from_dict(document).days[0].activities[0]


@pytest.fixture
def no_network(monkeypatch):
    """Stub the routing seam: a leg with no track draws a straight segment."""
    monkeypatch.setattr(mapbuild, "route", lambda a, b, cache, **kw: [a, b])


def resolved(document):
    it = Itinerary.from_dict(document)
    return it, mapbuild.resolve_day(it.days[0], it, cache=None)


# -- the model ---------------------------------------------------------------

def test_the_two_end_switches_default_off_and_the_junctions_on():
    """Splitting a drive at a place is what says the place matters, so the
    junctions are pinned unless told not to; the two ends are usually the
    activity before/after, already numbered."""
    road = road_of(doc())
    assert (road.display_start_on_maps, road.display_end_on_maps) == (False, False)
    assert road.display_intermediate_point_on_maps is True
    assert [w.location for w in road.pinned_waypoints()] == ["B", "C"]


def test_the_junction_switch_can_be_turned_off():
    road = road_of(doc(display_intermediate_point_on_maps=False))
    assert road.pinned_waypoints() == []


def test_each_switch_selects_its_own_points():
    assert [w.location for w in road_of(
        doc(display_intermediate_point_on_maps=True)).pinned_waypoints()] == ["B", "C"]
    assert [w.location for w in road_of(
        doc(display_end_on_maps=True,
            display_intermediate_point_on_maps=False)).pinned_waypoints()] == ["D"]
    # …and all three together pin every named point of the drive
    every = road_of(doc(display_start_on_maps=True, display_end_on_maps=True,
                        display_intermediate_point_on_maps=True))
    assert every.display_start_on_maps is True
    assert [w.location for w in every.pinned_waypoints()] == ["B", "C", "D"]


def test_a_hidden_coordinate_is_never_pinned():
    """`show_on_map: false` hides a pin wherever it appears — here too."""
    legs = [dict(LEG_AB), dict(LEG_BC, end_coordinate={"lat": 3, "long": 3,
                                                       "show_on_map": False})]
    road = road_of(doc(legs=legs, display_end_on_maps=True,
                       display_intermediate_point_on_maps=True))
    assert [w.location for w in road.pinned_waypoints()] == ["B"]


def test_a_leg_parses_its_gpx_into_a_track():
    road = road_of(doc(legs=[dict(LEG_AB, gpx=TRACK), LEG_BC]))
    first, second = road.named_waypoints
    assert first.gpx == TRACK and first.track is not None
    assert len(first.track.points) == 3
    assert second.gpx == "" and second.track is None


def test_a_leg_track_fills_in_nothing():
    """Unlike a hike's, a leg's recording never substitutes stated figures — the
    source's numbers are the ones printed."""
    road = road_of(doc(legs=[dict(LEG_AB, gpx=TRACK)]))
    assert road.named_waypoints[0].distance_km is None
    assert road.named_waypoints[0].duration_min is None
    assert road.distance_km is None


def test_an_unusable_leg_gpx_is_an_itinerary_error():
    with pytest.raises(ItineraryError):
        road_of(doc(legs=[dict(LEG_AB, gpx="not base64 at all!")]))


# -- the day map -------------------------------------------------------------

def test_a_drive_with_every_switch_off_contributes_no_pin(no_network):
    _it, (main, routes, nodes, _areas) = resolved(
        doc(display_intermediate_point_on_maps=False))
    assert main == []                      # a route, not pins
    assert len(routes) == 1 and len(nodes) == 1


def test_a_drive_left_alone_pins_its_junctions(no_network):
    """The default now: the junctions join the day's numbering, the two ends
    don't — so a 3-leg drive with nothing set contributes B and C."""
    _it, (main, _routes, _nodes, _areas) = resolved(doc())
    assert [p.label for p in main] == ["B", "C"]


def test_pinned_points_join_the_days_numbering_in_timeline_order(no_network):
    sight = {"type": "point_of_interest", "name": "Sight",
             "coordinate": {"lat": 9, "long": 9}}
    it, (main, _routes, _nodes, _areas) = resolved(
        doc(sight, display_start_on_maps=True,
            display_intermediate_point_on_maps=True))
    # the drive's points come first (it opens the day), the sight last
    assert [p.label for p in main] == ["A", "B", "C", "Sight"]

    dm = type("DM", (), {"numbers": {}})()
    for i, p in enumerate(main, start=1):
        dm.numbers[id(p.act)] = str(i)
    road = it.days[0].activities[0]
    # the road object carries its *departure's* label; each waypoint its own
    assert dm.numbers[id(road)] == "1"
    assert [dm.numbers[id(w)] for w in road.pinned_waypoints()] == ["2", "3"]


def test_a_leg_is_drawn_from_its_gpx_and_the_others_are_routed(no_network):
    _it, (_main, routes, _nodes, _areas) = resolved(
        doc(legs=[dict(LEG_AB, gpx=TRACK), LEG_BC]))
    line = routes[0]
    assert (1.9, 1.4) in line, "the recording's bulge is on the drawn line"
    assert line[0] == (1.0, 1.0) and line[-1] == (3.0, 3.0)


def test_without_a_gpx_the_line_is_exactly_the_routed_chain(no_network):
    """The feature is opt-in: a road that carries no recording draws the same
    line it always did, shaping points included."""
    legs = [dict(LEG_AB, waypoints=[{"lat": 1.5, "long": 1.5}]), LEG_BC]
    _it, (_main, routes, _nodes, _areas) = resolved(doc(legs=legs))
    assert routes[0] == [(1.0, 1.0), (1.5, 1.5), (2.0, 2.0), (3.0, 3.0)]


def test_a_recorded_leg_needs_no_departure_coordinate(no_network):
    """The track carries the geometry, so a road can be drawn from it alone."""
    legs = [{"start_location": "A", "end_location": "B",
             "end_coordinate": {"lat": 2, "long": 2}, "gpx": TRACK}]
    it = Itinerary.from_dict(doc(legs=legs))
    assert it.days[0].activities[0].coordinate is None
    _main, routes, _nodes, _areas = mapbuild.resolve_day(it.days[0], it, cache=None)
    assert routes and routes[0][0] == (1.0, 1.0)


# -- the resolved contract ---------------------------------------------------

def _road_out(document):
    return to_dict(Itinerary.from_dict(document))["days"][0]["activities"][0]


def test_the_switches_and_the_leg_gpx_reach_the_resolved_document():
    out = _road_out(doc(legs=[dict(LEG_AB, gpx=TRACK), LEG_BC],
                        display_intermediate_point_on_maps=True))
    assert out["display_intermediate_point_on_maps"] is True
    assert out["display_start_on_maps"] is False
    assert out["display_end_on_maps"] is False
    first, second = out["waypoints"]
    # the blob rides along verbatim, for the viewer's "(Get GPX track)" button…
    assert first["gpx"] == TRACK
    assert second["gpx"] is None
    # …but none of the geometry does: the map render is where the line lives
    assert "points" not in first and "profile" not in first
    # the pin is stamped by the caller (the map render), so it starts empty
    assert first["map_pin"] is None


# -- validation --------------------------------------------------------------

def _messages(document, level=None):
    findings = validate_text(json.dumps(document))
    return [f.message for f in findings if level is None or f.level == level]


def test_a_bad_switch_value_is_an_error():
    msgs = _messages(doc(display_start_on_maps="yes please"), "error")
    assert any("'display_start_on_maps' is invalid" in m for m in msgs)


def test_a_bad_leg_gpx_is_an_error():
    msgs = _messages(doc(legs=[dict(LEG_AB, gpx="not base64 at all!")]), "error")
    assert any("'gpx' is invalid" in m for m in msgs)


def test_a_leg_gpx_with_maps_off_is_noted():
    document = doc(legs=[dict(LEG_AB, gpx=TRACK)])
    document["defaults"]["include_maps_in_render"] = False
    assert any("no map is drawn from it" in m
               for m in _messages(document, "info"))
    # …and nothing is said when maps are on
    assert not any("no map is drawn from it" in m
                   for m in _messages(doc(legs=[dict(LEG_AB, gpx=TRACK)])))


def test_a_leg_gpx_neither_fills_nor_silences_the_figures_warning():
    """A hike's GPX answers the missing-distance warning; a leg's must not —
    the figures it would measure are never used."""
    warning = next(m for m in _messages(doc(legs=[dict(LEG_AB, gpx=TRACK)]), "warning")
                   if "should give a duration" in m)
    assert "distance_km" in warning


# -- the PDF's leg list ------------------------------------------------------

def _pdf_for(document, pins=None, road_pin=None):
    """A `TravelPDF` on a blank page, with `pin_label` stubbed: `pins` maps a
    waypoint's location to the label the rendered map gave it, and `road_pin` is
    the road's own (its departure's)."""
    from odysseyra_travelbook.pdf import TravelPDF

    it = Itinerary.from_dict(document)
    road = it.days[0].activities[0]
    pdf = TravelPDF(it, "en", False, "google")
    pdf.add_page()
    labels = {id(wp): (pins or {}).get(wp.location) for wp in road.waypoints}
    labels[id(road)] = road_pin
    pdf.pin_label = lambda obj: labels.get(id(obj))
    return pdf, road


def _transcribe(pdf):
    """Capture what `pdf` draws as a flat list of pieces, a pin disc coming
    through as ``(label)``. A route is drawn as a run of cells with the discs
    between them, so what the reader sees is the concatenation — hence the
    transcript rather than one string per `cell` call. Returns
    ``(pieces, discs)``."""
    pieces, discs = [], []

    def disc(x, y, label):
        pieces.append(f"({label})")
        discs.append(label)
        return 6.0

    pdf.cell = lambda w, h=0, text="", *a, **k: pieces.append(text)
    pdf.multi_cell = lambda w, h=0, text="", *a, **k: pieces.append(text)
    pdf._pin_disc = disc
    return pieces, discs


def _via_rows(document, pins=None, road_pin=None):
    """The rows `_road_waypoints` draws for the document's road, one string each
    (split on the bullet that leads every row)."""
    pdf, road = _pdf_for(document, pins, road_pin)
    pieces, discs = _transcribe(pdf)
    pdf._road_waypoints(pdf.l_margin, pdf.content_width, road)
    text = "".join(pieces)
    rows = [f"•{r}".strip() for r in text.split("•")[1:]]
    return rows, discs


def _title(document, pins=None, road_pin=None):
    """The two-ended title `_road_title` draws for the document's road."""
    pdf, road = _pdf_for(document, pins, road_pin)
    pieces, _discs = _transcribe(pdf)
    assert pdf._road_title(road, pdf.l_margin, pdf.content_width, 20.0, road_pin)
    return "".join(pieces).strip()


def test_a_one_leg_drive_lists_its_leg_only_once_it_is_pinned():
    """A pin number is unreadable without the name beside it, so a pinned
    arrival earns the row a plain one-leg drive doesn't get. Mirrors the
    viewer's RoadVia."""
    rows, discs = _via_rows(doc(legs=[LEG_AB]))
    assert rows == [] and discs == []      # a plain A → B drive: the title says it

    rows, discs = _via_rows(doc(legs=[LEG_AB], display_end_on_maps=True),
                            pins={"B": "2"})
    assert len(rows) == 1 and "A" in rows[0] and "B" in rows[0]
    assert discs == ["2"]                  # the arrival's pin, beside its name


def test_each_leg_row_pins_both_of_its_ends():
    """A junction ends one leg and starts the next, so its disc shows on both
    rows — the numbers chain (2)→(3) and each sits against its own name, rather
    than one disc leading a row that names two places."""
    rows, discs = _via_rows(doc(display_intermediate_point_on_maps=True),
                            pins={"B": "2", "C": "3"}, road_pin="1")
    assert len([r for r in rows if "→" in r]) == 3   # three legs, three rows
    assert rows[0].startswith("•  (1)A") and "(2)B" in rows[0]
    assert rows[1].startswith("•  (2)B") and "(3)C" in rows[1]
    assert rows[2].startswith("•  (3)C") and "D" in rows[2]
    # D is unpinned, so the last row's arrival carries no disc
    assert discs == ["1", "2", "2", "3", "3"]


def test_the_road_title_pins_both_ends_when_the_arrival_is_pinned():
    """`(1) Amboise → (4) Sarlat` — the arrival's number belongs beside the
    arrival. Mirrors the viewer's `ActivityTitle`."""
    assert _title(doc(display_end_on_maps=True), pins={"D": "4"},
                  road_pin="1") == "(1)A  →  (4)D"


def test_the_road_title_stays_a_plain_line_without_an_arrival_pin():
    """Nothing to split: one disc leads the title, as for every other activity
    (which is also what a road with an *unnamed* arrival falls back to)."""
    pdf, road = _pdf_for(doc(display_start_on_maps=True), road_pin="1")
    assert pdf._road_title(road, pdf.l_margin, pdf.content_width, 20.0, "1") is False


# -- building a GPX for a leg that has none ----------------------------------
#
# The viewer's "(Build GPX file)" link (distinct from "(Get GPX track)", which
# hands back an attached recording) goes through the bridge to these two seams.

def test_route_gpx_writes_a_route_not_a_track():
    """A computed line is a `<rte>`; `<trk>` would claim it was recorded."""
    doc = route_gpx([(42.48, 78.40), (42.35, 78.23)], "Karakol → Jeti-Oguz")
    assert "<rte>" in doc and "<trkpt" not in doc
    assert doc.count("<rtept") == 2
    assert "<name>Karakol → Jeti-Oguz</name>" in doc
    assert doc.startswith('<?xml version="1.0" encoding="UTF-8"?>')


def test_route_gpx_escapes_the_name_and_needs_two_points():
    assert "&amp;" in route_gpx([(1, 1), (2, 2)], "A & B")
    with pytest.raises(ValueError):
        route_gpx([(1, 1)], "nowhere")


def test_route_gpx_round_trips_through_our_own_reader():
    """What we write, we can read — the reader takes route points when there is
    no track (models/gpx.py), so a built file behaves like any other GPX."""
    doc = route_gpx([(42.0, 1.0), (42.1, 1.1), (42.2, 1.2)])
    track = gpx_track(base64.b64encode(doc.encode()).decode())
    assert track.points == [(42.0, 1.0), (42.1, 1.1), (42.2, 1.2)]
    assert track.has_elevation is False   # a route carries no elevations


def test_a_legs_geometry_is_the_line_the_map_draws(no_network):
    it = Itinerary.from_dict(doc())
    road = it.days[0].activities[0]
    first = mapbuild.road_leg_geometry(road, it.days[0], it, None, 0)
    assert first is not None
    wp, line = first
    assert wp.location == "B"
    assert line[0] == (1.0, 1.0) and line[-1] == (2.0, 2.0)
    # …and the second leg starts where the first ended
    _wp2, second = mapbuild.road_leg_geometry(road, it.days[0], it, None, 1)
    assert second[0] == (2.0, 2.0) and second[-1] == (3.0, 3.0)


def test_a_recorded_legs_geometry_is_its_recording(no_network):
    it = Itinerary.from_dict(doc(legs=[dict(LEG_AB, gpx=TRACK), LEG_BC]))
    road = it.days[0].activities[0]
    _wp, line = mapbuild.road_leg_geometry(road, it.days[0], it, None, 0)
    assert (1.9, 1.4) in line


def test_an_unroutable_leg_yields_nothing_rather_than_a_straight_line(monkeypatch):
    """A crow-flight line is fine to *draw* but wrong to hand a GPS as a route,
    so the export path asks for the real geometry or nothing."""
    monkeypatch.setattr(mapbuild, "route",
                        lambda a, b, cache, fallback=True: [a, b] if fallback else None)
    it = Itinerary.from_dict(doc())
    road = it.days[0].activities[0]
    assert mapbuild.road_leg_geometry(road, it.days[0], it, None, 0) is None
    # the *drawing* path still gets its straight line, unchanged
    _main, routes, _nodes, _areas = mapbuild.resolve_day(it.days[0], it, cache=None)
    assert routes and routes[0][0] == (1.0, 1.0)


def test_a_leg_index_off_the_end_yields_nothing(no_network):
    it = Itinerary.from_dict(doc())
    road = it.days[0].activities[0]
    assert mapbuild.road_leg_geometry(road, it.days[0], it, None, 9) is None
