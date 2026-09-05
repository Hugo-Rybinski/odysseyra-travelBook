"""``show_map`` — the per-object twin of the trip's map switches.

Three maps, three owners: the **day** owns its overview map, a **place** owns its
zoomed area map, a **hike** owns its trail map. With maps on globally, each of
those can be switched off on its own object without touching the other two.

The two traps these tests exist for:

* the day's overview map is what the numbered pin discs are a *legend* for, so
  switching it off has to take the numbers with it — and must **not** take the
  area maps, which are a different map with a different owner;
* ``show_map`` is not ``coordinate.show_on_map``. That one hides an object's pin
  on a map something else draws; this one drops the map the object draws itself.
  A place with ``show_map: false`` still wears its number on the day map.

Offline throughout: the routing seam is stubbed and no tiles are fetched.
"""

import base64

import pytest
from PIL import Image

from odysseyra_travelbook.maps import Cache
from odysseyra_travelbook.maps import build as mapbuild
from odysseyra_travelbook.models import Itinerary, to_dict
from odysseyra_travelbook.pdf import TravelPDF
from odysseyra_travelbook.validate import validate_text

LOUVRE = (48.8606, 2.3376)
ORSAY = (48.8600, 2.3266)
TOWER = (48.8584, 2.2945)
HOTEL = (48.8656, 2.3212)


def poi(name, coord):
    return {"type": "point_of_interest", "name": name, "duration": "1h",
            "coordinate": {"lat": coord[0], "long": coord[1]}}


def trip(days, **defaults):
    # `auto_sized_buffer` off so a day's `activities` are the ones written here:
    # an inserted buffer would shift every index below without changing a thing
    # about the maps (`resolve_day` skips buffers outright).
    return Itinerary.from_dict({
        "travel_description": {"title": "T", "cover_color": "#2f6b4f"},
        "defaults": {"include_maps_in_render": True,
                     "auto_sized_buffer": False, **defaults},
        "days": days,
        "accommodations": [{
            "name": "Hôtel", "city": "Paris",
            "arrival": "2026-06-01", "departure": "2026-06-02",
            "coordinate": {"lat": HOTEL[0], "long": HOTEL[1]},
        }],
    })


def paris_day(*, day_map=None, place_map=None):
    """One day: a place holding two located sights, plus a standalone one. Both
    ``show_map`` flags are left out of the JSON entirely when not given, so the
    default path is what a `None` exercises."""
    place = {"type": "place", "name": "Rive gauche",
             "activities": [poi("Musée d'Orsay", ORSAY), poi("Tour Eiffel", TOWER)]}
    if place_map is not None:
        place["show_map"] = place_map
    day = {"title": "Paris", "date": "2026-06-01", "city": "Paris",
           "activities": [poi("Louvre", LOUVRE), place]}
    if day_map is not None:
        day["show_map"] = day_map
    return trip([day])


@pytest.fixture
def drawn(monkeypatch):
    """Run the day maps offline, capturing one entry per map actually drawn."""
    monkeypatch.setattr(mapbuild, "route", lambda a, b, cache, **kw: [a, b])
    calls = []

    def fake_render_map(all_coords, routes, points, accent, tiles_dir, **kw):
        calls.append({"points": list(points), "labels": list(kw.get("labels") or [])})
        return Image.new("RGB", (10, 10))

    monkeypatch.setattr(mapbuild, "render_map", fake_render_map)
    return calls


# -- the model ---------------------------------------------------------------

def test_both_levels_default_to_drawing_their_map():
    it = paris_day()
    assert it.days[0].show_map is True
    assert [a.show_map for a in it.days[0].activities] == [True, True]


@pytest.mark.parametrize("written,expected", [
    (False, False), ("false", False), ("no", False), (True, True), ("yes", True),
])
def test_the_flag_is_parsed_like_every_other_boolean(written, expected):
    it = paris_day(day_map=written, place_map=written)
    assert it.days[0].show_map is expected
    assert it.days[0].activities[1].show_map is expected


def test_a_nested_activity_carries_it_too():
    """A nested hike draws a trail map exactly like a top-level one, so the flag
    has to survive the nesting — it is parsed on the shared `Activity` base."""
    it = trip([{"title": "d", "date": "2026-06-01", "activities": [
        {"type": "place", "name": "Vallée", "activities": [
            {"type": "hike", "name": "Crête", "duration": "3h", "show_map": False},
        ]},
    ]}])
    assert it.days[0].activities[0].activities[0].show_map is False


def test_both_levels_reach_the_resolved_document():
    data = to_dict(paris_day(day_map=False, place_map=False))
    day = data["days"][0]
    assert day["show_map"] is False
    assert [a["show_map"] for a in day["activities"]] == [True, False]


# -- the day's overview map --------------------------------------------------

def test_the_day_map_is_drawn_by_default(drawn, tmp_path):
    dm = mapbuild.render_day_maps(paris_day().days[0], paris_day(), Cache.open(tmp_path))
    assert dm.main is not None
    assert len(dm.areas) == 1


def test_switching_the_day_map_off_drops_it_with_its_pin_numbers(drawn, tmp_path):
    it = paris_day(day_map=False)
    day = it.days[0]
    dm = mapbuild.render_day_maps(day, it, Cache.open(tmp_path))

    assert dm.main is None
    louvre, place = day.activities
    # the numbered discs were that map's legend, so they go with it — including
    # the night's ★, which is a pin on the same map
    assert dm.number_for(louvre) is None
    assert dm.number_for(place) is None
    assert dm.number_for(it.accommodations[0]) is None
    # and only the area map was handed to the renderer
    assert [c["labels"] for c in drawn] == [["A", "B", "★"]]


def test_the_day_map_off_still_draws_its_places_zoom_maps(drawn, tmp_path):
    """The two maps have different owners: a day saying nothing useful at trip
    scale is not a day whose *areas* say nothing."""
    it = paris_day(day_map=False)
    dm = mapbuild.render_day_maps(it.days[0], it, Cache.open(tmp_path))
    assert [t for t, _ in dm.areas] == ["Rive gauche"]
    nested = it.days[0].activities[1].activities
    assert [dm.number_for(a) for a in nested] == ["A", "B"]


def test_the_day_map_off_resolves_nothing_it_would_have_needed(monkeypatch):
    """The point of the switch is a page without that map, so the geocoding and
    routing behind it is work thrown away — `resolve_day(main=False)` skips it."""
    routed = []
    monkeypatch.setattr(mapbuild, "route",
                        lambda a, b, cache, **kw: routed.append((a, b)) or [a, b])
    it = trip([{"title": "d", "date": "2026-06-01", "show_map": False,
                "activities": [
                    {"type": "road", "legs": [{
                        "start_location": "A", "end_location": "B",
                        "start_coordinate": {"lat": LOUVRE[0], "long": LOUVRE[1]},
                        "end_coordinate": {"lat": ORSAY[0], "long": ORSAY[1]},
                    }]},
                    poi("Louvre", LOUVRE),
                ]}])
    main, routes, nodes, areas = mapbuild.resolve_day(it.days[0], it, cache=None,
                                                      main=False)
    assert (main, routes, nodes, areas) == ([], [], [], [])
    assert routed == []


# -- a place's area map ------------------------------------------------------

def test_a_place_can_drop_its_own_zoom_map(drawn, tmp_path):
    it = paris_day(place_map=False)
    dm = mapbuild.render_day_maps(it.days[0], it, Cache.open(tmp_path))
    assert dm.areas == []
    # the nested points lose their letters, since the map that lettered them is
    # gone — but the day map is untouched
    nested = it.days[0].activities[1].activities
    assert [dm.number_for(a) for a in nested] == [None, None]
    assert dm.main is not None
    assert [c["labels"] for c in drawn] == [["1", "2", "★"]]


def test_a_place_that_drops_its_map_keeps_its_pin_on_the_days(drawn, tmp_path):
    """`show_map` is not `coordinate.show_on_map`: the place is still somewhere
    you go, so it is still a numbered stop on the day's map."""
    it = paris_day(place_map=False)
    dm = mapbuild.render_day_maps(it.days[0], it, Cache.open(tmp_path))
    assert dm.number_for(it.days[0].activities[1]) == "2"


# -- the whole-trip map ------------------------------------------------------

def test_the_trip_map_keeps_a_day_that_switched_its_own_map_off(monkeypatch):
    """A pin there carries the *day*, and the map belongs to the trip: dropping
    the day would leave a hole in the trip's shape rather than tidy a page."""
    monkeypatch.setattr(mapbuild, "route", lambda a, b, cache, **kw: [a, b])
    it = paris_day(day_map=False)
    points, labels, _routes, _legs = mapbuild.resolve_trip(it, cache=None)
    assert labels and set(labels) == {"1"}
    assert LOUVRE in points


# -- a hike's trail map ------------------------------------------------------

GPX = base64.b64encode(
    b'<?xml version="1.0"?><gpx version="1.1"><trk><trkseg>'
    b'<trkpt lat="42.70" lon="-0.14"><ele>1000</ele></trkpt>'
    b'<trkpt lat="42.71" lon="-0.14"><ele>1200</ele></trkpt>'
    b'<trkpt lat="42.72" lon="-0.14"><ele>1100</ele></trkpt>'
    b"</trkseg></trk></gpx>"
).decode()


def hike_trip(**hike):
    return trip([{"title": "d", "date": "2026-06-01", "activities": [
        {"type": "hike", "name": "Crête", "duration": "3h", "gpx": GPX, **hike},
    ]}])


def _figure(it, monkeypatch):
    """What ``hike_track`` drew, as ``(map?, profile?)`` — both halves stubbed so
    nothing is fetched and the gate is all that's under test."""
    pdf = TravelPDF(it, "en", False, "google")
    drew = []
    monkeypatch.setattr(TravelPDF, "_hike_map",
                        lambda self, *a, **k: drew.append("map") or None)
    monkeypatch.setattr(TravelPDF, "_hike_profile",
                        lambda self, *a, **k: drew.append("profile"))
    pdf.hike_track(it.days[0].activities[0], 10, 100)
    return drew


def test_a_hike_draws_map_then_profile_by_default(monkeypatch):
    assert _figure(hike_trip(), monkeypatch) == ["map", "profile"]


def test_a_hike_can_drop_the_trail_map_and_keep_the_profile(monkeypatch):
    """The field says *map*, and the profile is a chart of figures the hike
    already states — `defaults.include_hike_maps` is the switch for the pair."""
    assert _figure(hike_trip(show_map=False), monkeypatch) == ["profile"]


def test_the_trail_map_is_independent_of_the_day_map(monkeypatch):
    """`include_hike_maps` is deliberately not gated behind
    `include_maps_in_render`, and the same holds one level down."""
    it = hike_trip()
    it.days[0].show_map = False
    assert _figure(it, monkeypatch) == ["map", "profile"]


def test_a_hike_that_drops_its_map_keeps_its_track_to_download():
    """The geometry still ships: the profile is drawn from it, and the viewer's
    "(Get GPX track)" hands the file back. Only `include_hike_maps` withholds it."""
    data = to_dict(hike_trip(show_map=False))
    track = data["days"][0]["activities"][0]["track"]
    assert track is not None and track["gpx"] == GPX


# -- the validator -----------------------------------------------------------

def _messages(doc, level=None):
    import json
    findings = validate_text(json.dumps(doc))
    return [f.message for f in findings if level is None or f.level == level]


def _doc(day=None, place=None, hike=None, nested_hike=None):
    place_act = {"type": "place", "name": "Vallée", "activities": [
        {"type": "point_of_interest", "name": "Cascade", "duration": "30 min"},
    ]}
    if place is not None:
        place_act["show_map"] = place
    if nested_hike is not None:
        place_act["activities"].append(
            {"type": "hike", "name": "Boucle", "show_map": nested_hike})
    hike_act = {"type": "hike", "name": "Crête", "duration": "3h"}
    if hike is not None:
        hike_act["show_map"] = hike
    d = {"title": "d", "date": "2026-06-01", "activities": [place_act, hike_act]}
    if day is not None:
        d["show_map"] = day
    return {"travel_description": {"title": "T"}, "days": [d]}


@pytest.mark.parametrize("kwargs,quoted", [
    ({"day": "sometimes"}, "'sometimes'"),
    ({"place": "no thanks"}, "'no thanks'"),
    ({"hike": 1.5}, "1.5"),
    # A nested hike is checked for *values* even though its optional fields are
    # skipped, so a typo there is reported like any other.
    ({"nested_hike": "oui"}, "'oui'"),
])
def test_a_non_boolean_is_an_error_at_every_level(kwargs, quoted):
    errors = _messages(_doc(**kwargs), "error")
    assert any("'show_map' is invalid" in m and quoted in m
               and "must be true or false" in m for m in errors)


def test_each_level_states_its_own_default():
    """Three maps, three wordings: a reader wants to know *which* map the switch
    they left out would have drawn."""
    infos = [m for m in _messages(_doc(), "info") if "'show_map'" in m]
    assert len(infos) == 3
    assert any("overview map" in m and "the day's overview map is drawn" in m
               for m in infos)
    assert any("zoomed area map" in m and "the area map is drawn" in m
               for m in infos)
    assert any("trail map of its GPX" in m and "the trail map is drawn" in m
               for m in infos)


def test_it_is_not_offered_where_there_is_no_map_to_switch_off():
    """Only a place and a hike draw a map of their own, so only those two are
    asked about — an info on every meal would be noise about nothing."""
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "meal", "restaurant": "R", "duration": "1h"},
               {"type": "point_of_interest", "name": "P", "duration": "1h"},
           ]}]}
    infos = [m for m in _messages(doc, "info") if "'show_map'" in m]
    assert len(infos) == 1 and "overview map" in infos[0]  # the day's, only
