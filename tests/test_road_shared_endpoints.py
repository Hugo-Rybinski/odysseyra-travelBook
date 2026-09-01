"""A drive that shares an end with the activity beside it —
``same_start_as_previous_activity`` / ``same_end_as_next_activity``.

Each flag does two separable things, and the tests are split the same way: it
*fills in* the leg endpoint left blank, and it *shares* the neighbour's map pin
whether or not anything was filled in. Everything here is offline: the pin
numbering is read straight off ``resolve_day`` / ``DayMaps``, no tiles involved.
"""

import pytest

from odysseyra_travelbook.maps import build as mapbuild
from odysseyra_travelbook.models import Itinerary, ItineraryError
from odysseyra_travelbook.validate import validate_text

AMBOISE = {"lat": 47.41, "long": 0.98}
CHENONCEAU = {"lat": 47.32, "long": 1.07}

POI_BEFORE = {"type": "point_of_interest", "name": "Château d'Amboise",
              "coordinate": AMBOISE, "duration": "1h"}
POI_AFTER = {"type": "point_of_interest", "name": "Chenonceau",
             "coordinate": CHENONCEAU, "duration": "1h"}


def doc(*activities, **road):
    """A one-day, maps-on itinerary. ``activities`` is the whole day, with the
    road spliced in wherever the caller put ``...``."""
    legs = road.pop("legs", [{"end_location": "Chenonceau",
                              "end_coordinate": CHENONCEAU}])
    acts = [{"type": "road", "legs": legs, "duration": "1h", **road}
            if a is Ellipsis else a for a in activities]
    return {
        "travel_description": {"title": "T", "start_date": "2026-09-04"},
        "defaults": {"include_maps_in_render": True},
        "days": [{"title": "D", "activities": acts}],
    }


def road_of(document):
    day = Itinerary.from_dict(document).days[0]
    return next(a for a in day.activities if a.kind == "road")


def pins(document):
    """``(road departure pin, road arrival pin)`` as the renderers read them —
    through ``DayMaps.number_for``, so the alias is exercised rather than the
    numbering pass."""
    it = Itinerary.from_dict(document)
    day = it.days[0]
    main, _routes, _nodes, _areas = mapbuild.resolve_day(day, it, cache=None)
    dm = mapbuild.DayMaps(aliases=mapbuild.pin_aliases(day))
    for i, p in enumerate(main, start=1):
        dm.numbers[id(p.act)] = str(i)
    road = next(a for a in day.activities if a.kind == "road")
    return dm.number_for(road), dm.number_for(road.waypoints[-1])


# -- the model: filling the endpoint in --------------------------------------

def test_both_flags_default_off():
    road = road_of(doc(POI_BEFORE, ..., POI_AFTER,
                       legs=[{"start_location": "Amboise",
                              "end_location": "Chenonceau",
                              "end_coordinate": CHENONCEAU}]))
    assert (road.same_start_as_previous_activity,
            road.same_end_as_next_activity) == (False, False)
    assert (road.start_shared_with, road.end_shared_with) == (None, None)


def test_a_blank_departure_is_taken_from_the_previous_activity():
    road = road_of(doc(POI_BEFORE, ..., POI_AFTER,
                       same_start_as_previous_activity=True))
    assert road.start == "Château d'Amboise"
    assert (road.coordinate.lat, road.coordinate.long) == (47.41, 0.98)


def test_a_blank_arrival_is_taken_from_the_next_activity():
    road = road_of(doc(POI_BEFORE, ..., POI_AFTER,
                       same_end_as_next_activity=True,
                       legs=[{"start_location": "Amboise"}]))
    arrival = road.waypoints[-1]
    assert (arrival.location, road.destination) == ("Chenonceau", "Chenonceau")
    assert (arrival.coordinate.lat, arrival.coordinate.long) == (47.32, 1.07)


def test_a_stated_endpoint_wins_over_the_neighbour():
    """The fill-in is a fallback, so the drive may still name its own end — the
    car park, not the château. Only the *pin* is shared unconditionally."""
    road = road_of(doc(POI_BEFORE, ..., POI_AFTER,
                       same_start_as_previous_activity=True,
                       legs=[{"start_location": "Amboise — car park",
                              "start_coordinate": {"lat": 47.40, "long": 0.99},
                              "end_location": "Chenonceau",
                              "end_coordinate": CHENONCEAU}]))
    assert road.start == "Amboise — car park"
    assert road.coordinate.lat == 47.40
    assert road.start_shared_with is not None  # the pin is shared regardless


def test_a_buffer_between_the_two_is_skipped():
    """Free time is a length, not a place: the drive still departs from the
    museum on the other side of the gap."""
    road = road_of(doc(POI_BEFORE, {"type": "buffer", "duration": "30 min"},
                       ..., POI_AFTER, same_start_as_previous_activity=True))
    assert road.start == "Château d'Amboise"


def test_a_meal_lends_its_restaurant_not_its_title():
    road = road_of(doc({"type": "meal", "restaurant": "Chez Bruno",
                        "coordinate": AMBOISE, "duration": "1h"},
                       ..., POI_AFTER, same_start_as_previous_activity=True))
    assert road.start == "Chez Bruno"  # not "Lunch at Chez Bruno"


def test_one_drive_can_hand_its_arrival_to_the_next_drives_departure():
    day = Itinerary.from_dict(doc(
        POI_BEFORE,
        {"type": "road", "duration": "1h", "same_end_as_next_activity": True,
         "legs": [{"start_location": "Amboise"}]},
        {"type": "road", "duration": "1h",
         "legs": [{"start_location": "Tours",
                   "start_coordinate": {"lat": 47.39, "long": 0.69},
                   "end_location": "Chenonceau", "end_coordinate": CHENONCEAU}]},
    )).days[0]
    first = next(a for a in day.activities if a.kind == "road")
    assert first.destination == "Tours"


# -- the model: what it refuses ---------------------------------------------

def test_no_previous_activity_is_an_error():
    with pytest.raises(ItineraryError, match="no previous activity"):
        Itinerary.from_dict(doc(..., POI_AFTER,
                                same_start_as_previous_activity=True))


def test_no_next_activity_is_an_error():
    with pytest.raises(ItineraryError, match="no next activity"):
        Itinerary.from_dict(doc(POI_BEFORE, ..., same_end_as_next_activity=True,
                                legs=[{"start_location": "Amboise"}]))


def test_a_previous_activity_naming_no_place_is_an_error():
    with pytest.raises(ItineraryError, match="names no place to depart from"):
        Itinerary.from_dict(doc({"type": "meal", "duration": "1h"}, ..., POI_AFTER,
                                same_start_as_previous_activity=True,
                                legs=[{"end_location": "Chenonceau",
                                       "end_coordinate": CHENONCEAU}]))


def test_an_unlocated_next_activity_is_an_error():
    """A drive's arrival is a point on the drawn route, so it has to resolve —
    the requirement the last leg's ``end_coordinate`` always carried."""
    with pytest.raises(ItineraryError, match="has no 'coordinate'"):
        Itinerary.from_dict(doc(
            POI_BEFORE, ...,
            {"type": "point_of_interest", "name": "Chenonceau", "duration": "1h"},
            same_end_as_next_activity=True, legs=[{"start_location": "Amboise"}]))


def test_two_drives_pointing_at_each_other_are_an_error():
    with pytest.raises(ItineraryError, match="names no place"):
        Itinerary.from_dict(doc(
            POI_BEFORE,
            {"type": "road", "duration": "1h", "same_end_as_next_activity": True,
             "legs": [{"start_location": "Amboise"}]},
            {"type": "road", "duration": "1h",
             "same_start_as_previous_activity": True,
             "legs": [{"end_location": "Chenonceau",
                       "end_coordinate": CHENONCEAU}]},
        ))


# -- the map: one place, one number -----------------------------------------

def test_without_the_flags_a_drive_takes_no_pin():
    assert pins(doc(POI_BEFORE, ..., POI_AFTER,
                    legs=[{"start_location": "Amboise",
                           "end_location": "Chenonceau",
                           "end_coordinate": CHENONCEAU}])) == (None, None)


def test_a_shared_end_wears_the_neighbours_number():
    assert pins(doc(POI_BEFORE, ..., POI_AFTER,
                    same_start_as_previous_activity=True,
                    same_end_as_next_activity=True,
                    legs=[{"end_location": "Chenonceau",
                           "end_coordinate": CHENONCEAU}])) == ("1", "2")


def test_the_number_is_shared_even_with_the_endpoint_spelled_out():
    """The whole reason the two halves are separate: naming the place yourself
    must not cost you a second pin on it."""
    assert pins(doc(POI_BEFORE, ..., POI_AFTER,
                    same_start_as_previous_activity=True,
                    legs=[{"start_location": "Amboise — car park",
                           "start_coordinate": {"lat": 47.40, "long": 0.99},
                           "end_location": "Chenonceau",
                           "end_coordinate": CHENONCEAU}])) == ("1", None)


def test_the_display_switches_add_no_second_pin_for_a_shared_end():
    """With both `display_*` switches on, a day of three activities still has
    exactly two pins — the drive's ends are the two POIs, not four points."""
    document = doc(POI_BEFORE, ..., POI_AFTER,
                   same_start_as_previous_activity=True,
                   same_end_as_next_activity=True,
                   display_start_on_maps=True, display_end_on_maps=True,
                   legs=[{"end_location": "Chenonceau",
                          "end_coordinate": CHENONCEAU}])
    it = Itinerary.from_dict(document)
    main, _routes, _nodes, _areas = mapbuild.resolve_day(it.days[0], it, cache=None)
    assert [p.label for p in main] == ["Château d'Amboise", "Chenonceau"]
    assert pins(document) == ("1", "2")


def test_an_unpinned_neighbour_lends_no_number():
    """A place nobody pinned lends nothing — the drive's end simply has no
    number, rather than inventing one for a point the map doesn't show."""
    hidden = {**POI_BEFORE, "coordinate": {**AMBOISE, "show_on_map": False}}
    assert pins(doc(hidden, ..., POI_AFTER,
                    same_start_as_previous_activity=True,
                    display_start_on_maps=True))[0] is None


# -- the validator -----------------------------------------------------------

def _findings(document, level=None):
    import json
    out = validate_text(json.dumps(document))
    return [f.message for f in out if level is None or f.level == level]


def test_the_validator_reports_a_missing_neighbour():
    messages = _findings(doc(..., POI_AFTER,
                             same_start_as_previous_activity=True), "error")
    assert any("no previous activity to take the departure from" in m
               for m in messages)


def test_the_validator_reports_an_unlocated_arrival_neighbour():
    messages = _findings(doc(
        POI_BEFORE, ...,
        {"type": "point_of_interest", "name": "Chenonceau", "duration": "1h"},
        same_end_as_next_activity=True, legs=[{"start_location": "Amboise"}]),
        "error")
    assert any("has no 'coordinate'" in m for m in messages)


def test_the_validator_accepts_a_road_neighbour_located_on_its_leg():
    """A road carries no ``coordinate`` of its own — its endpoints live on its
    legs — so the located-arrival check has to look there or call every drive
    unlocated."""
    messages = _findings(doc(
        POI_BEFORE,
        {"type": "road", "duration": "1h", "same_end_as_next_activity": True,
         "legs": [{"start_location": "Amboise"}]},
        {"type": "road", "duration": "1h",
         "legs": [{"start_location": "Tours",
                   "start_coordinate": {"lat": 47.39, "long": 0.69},
                   "end_location": "Chenonceau", "end_coordinate": CHENONCEAU}]},
    ), "error")
    assert not any("has no 'coordinate'" in m for m in messages)


def test_the_validator_calls_a_redundant_display_switch_an_info():
    messages = _findings(doc(POI_BEFORE, ..., POI_AFTER,
                             same_start_as_previous_activity=True,
                             display_start_on_maps=True), "info")
    assert any("'display_start_on_maps' adds nothing here" in m for m in messages)


def test_the_validator_stops_requiring_the_borrowed_endpoint():
    messages = _findings(doc(POI_BEFORE, ..., POI_AFTER,
                             same_end_as_next_activity=True,
                             legs=[{"start_location": "Amboise"}]), "error")
    assert not any("'end_location'" in m or "'end_coordinate'" in m
                   for m in messages)
