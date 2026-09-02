"""One place, one pin — ``maps/build.py``'s :func:`fold_pins`.

A day names the same spot more than once as a matter of course: a drive's
junction is the next drive's departure, an out-and-back passes its turning point
twice, the village you park in is also the sight you walk to. Each mention used
to earn its own number, so a place wore two stacked pins and the day's numbering
counted mentions rather than places. These tests pin the merge rule (same name,
within a kilometre) and the two things that must *not* merge.

Offline throughout: the routing seam is stubbed and no tiles are fetched.
"""

import pytest
from PIL import Image

from odysseyra_travelbook.maps import Cache
from odysseyra_travelbook.maps import build as mapbuild
from odysseyra_travelbook.maps.build import _apart_km, _pin_key, _Pt, fold_pins
from odysseyra_travelbook.models import Itinerary

# Pont d'Espagne, and the same car park written a second time ~150 m off.
PDE = (42.8536, -0.1444)
PDE_AGAIN = (42.8523, -0.1432)
GAUBE = (42.8281, -0.1442)
CAUTERETS = (42.8886, -0.1130)


def pt(label, coord):
    return _Pt(label, coord[0], coord[1], act=object())


def labels_of(groups):
    return [[p.label for p in g] for g in groups]


# -- the name key ------------------------------------------------------------

@pytest.mark.parametrize("other", [
    "pont d'espagne",        # a different hand typed it
    "Pont d’Espagne",        # a curly apostrophe, as pasted from a guidebook
    "  Pont   d'Espagne  ",  # stray whitespace
    "Pont dʼEspagne",        # the modifier-letter apostrophe
])
def test_the_same_name_spelled_differently_keys_alike(other):
    assert _pin_key(other) == _pin_key("Pont d'Espagne")


def test_accents_and_dash_variants_are_folded_away():
    """A name lifted out of a GPX filename routinely arrives unaccented, and an
    en dash for a hyphen is a copy-paste away."""
    assert _pin_key("Vezere") == _pin_key("Vézère")
    assert _pin_key("Jeti-Oguz") == _pin_key("Jeti–Oguz")


def test_a_qualified_endpoint_is_not_the_bare_place():
    """`Cauterets — car park` is deliberately its own place: being able to write
    an endpoint out when the neighbouring activity would supply it is the whole
    reason that distinction exists."""
    assert _pin_key("Cauterets — car park") != _pin_key("Cauterets")


def test_a_nameless_point_keys_to_nothing():
    assert _pin_key("") == _pin_key(None) == ""


# -- the merge rule ----------------------------------------------------------

def test_the_same_name_within_a_kilometre_is_one_pin():
    groups = fold_pins([pt("Pont d'Espagne", PDE), pt("Lac de Gaube", GAUBE),
                        pt("Pont d’Espagne", PDE_AGAIN)])
    # the third mention joins the first group; the order of the pins is the order
    # the day first reached each place, so the numbering still reads down the page
    assert labels_of(groups) == [["Pont d'Espagne", "Pont d’Espagne"],
                                 ["Lac de Gaube"]]


def test_the_same_name_far_apart_keeps_its_own_pin():
    """A driving day can pass through two different places of one name — and a
    name alone is no evidence they are the same spot."""
    groups = fold_pins([pt("Sainte-Marie", (43.0, 0.0)),
                        pt("Sainte-Marie", (43.5, 0.6))])
    assert len(groups) == 2


def test_different_names_at_one_spot_keep_their_own_pins():
    """The museum and the café across the square are two stops, and a reader
    following the numbers needs both."""
    groups = fold_pins([pt("Musée", PDE), pt("Café", PDE)])
    assert len(groups) == 2


def test_a_nameless_point_never_merges():
    groups = fold_pins([pt("", PDE), pt("", PDE)])
    assert len(groups) == 2


def test_near_misses_do_not_chain_a_group_across_the_map():
    """Every candidate is measured against the group's **first** point — the one
    the pin is drawn at — so three mentions 900 m apart in a line don't drag one
    pin 1.8 km from where its label sits."""
    a = (43.0, 0.0)
    b = (43.0 + 0.9 / 111.32, 0.0)
    c = (43.0 + 1.8 / 111.32, 0.0)
    assert _apart_km(a, b) < mapbuild.PIN_MERGE_KM < _apart_km(a, c)
    groups = fold_pins([pt("X", a), pt("X", b), pt("X", c)])
    assert [len(g) for g in groups] == [2, 1]


# -- end to end on a day -----------------------------------------------------

def out_and_back():
    """A day that drives up a valley, walks, and drives back down — so `Pont
    d'Espagne` is a junction of both drives."""
    def leg(name, coord):
        return {"end_location": name, "end_coordinate": {"lat": coord[0], "long": coord[1]}}

    up = {"type": "road", "legs": [
        {"start_location": "Cauterets",
         "start_coordinate": {"lat": CAUTERETS[0], "long": CAUTERETS[1]},
         **leg("Pont d'Espagne", PDE)},
        leg("Lac de Gaube", GAUBE)]}
    walk = {"type": "hike", "name": "Lac de Gaube",
            "coordinate": {"lat": GAUBE[0], "long": GAUBE[1]}}
    down = {"type": "road", "legs": [
        {"start_location": "Lac de Gaube",
         "start_coordinate": {"lat": GAUBE[0], "long": GAUBE[1]},
         **leg("Pont d’Espagne", PDE_AGAIN)},
        leg("Cauterets", CAUTERETS)]}
    return Itinerary.from_dict({
        "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
        "defaults": {"include_maps_in_render": True},
        "days": [{"title": "d", "date": "2026-06-01", "city": "Cauterets",
                  "activities": [up, walk, down]}],
    })


@pytest.fixture
def drawn(monkeypatch):
    """Run the day maps offline, capturing what `render_map` was handed."""
    monkeypatch.setattr(mapbuild, "route", lambda a, b, cache, **kw: [a, b])
    calls = []

    def fake_render_map(all_coords, routes, points, accent, tiles_dir, **kw):
        calls.append({"points": list(points), "labels": list(kw.get("labels") or [])})
        return Image.new("RGB", (10, 10))

    monkeypatch.setattr(mapbuild, "render_map", fake_render_map)
    return calls


def test_a_junction_reached_twice_wears_one_number_on_map_and_page(drawn, tmp_path):
    it = out_and_back()
    dm = mapbuild.render_day_maps(it.days[0], it, Cache.open(tmp_path))
    up, down = it.days[0].activities[0], it.days[0].activities[-1]
    walk = next(a for a in it.days[0].activities if a.kind == "hike")

    # the two junctions are one place: one pin, and the hike takes the next number
    assert dm.number_for(up.waypoints[0]) == "1"
    assert dm.number_for(down.waypoints[0]) == "1"
    assert dm.number_for(walk) == "2"
    # the map is handed two pins, not three, and the sequence has no gap in it
    assert drawn[0]["labels"] == ["1", "2"]
    assert len(drawn[0]["points"]) == 2
    # the pin sits at the *first* mention's coordinate
    assert drawn[0]["points"][0] == PDE
    # and the legend names the place once
    assert dm.main.legend == ["Pont d'Espagne", "Lac de Gaube"]


def test_an_areas_lettered_pins_fold_the_same_way(drawn, tmp_path):
    """The rule is about places, not about which map they land on, so an area's
    A/B/C… collapses a repeated stop too."""
    def poi(name, coord):
        return {"type": "point_of_interest", "name": name,
                "coordinate": {"lat": coord[0], "long": coord[1]}}

    it = Itinerary.from_dict({
        "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
        "defaults": {"include_maps_in_render": True},
        "days": [{"title": "d", "date": "2026-06-01", "city": "Cauterets",
                  "activities": [{"type": "place", "name": "Valley", "activities": [
                      poi("Pont d'Espagne", PDE),
                      poi("Lac de Gaube", GAUBE),
                      poi("Pont d’Espagne", PDE_AGAIN),
                  ]}]}],
    })
    dm = mapbuild.render_day_maps(it.days[0], it, Cache.open(tmp_path))
    nested = it.days[0].activities[0].activities
    assert [dm.number_for(a) for a in nested] == ["A", "B", "A"]
    _title, area = dm.areas[0]
    assert area.legend == ["Pont d'Espagne", "Lac de Gaube"]
