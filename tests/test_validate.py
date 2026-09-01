import json
import os
from pathlib import Path

from odysseyra_travelbook import format_findings, validate_text
from odysseyra_travelbook.validate import load_with_lines

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE = EXAMPLES / "pyrenees.json"
BROKEN = EXAMPLES / "broken.json"
BROKEN_OUTPUT = EXAMPLES / "broken_validator_output.txt"


def _errors(findings):
    return [f for f in findings if f.level == "error"]


def _warnings(findings):
    return [f for f in findings if f.level == "warning"]


def _infos(findings):
    return [f for f in findings if f.level == "info"]


def _messages(findings):
    return "\n".join(f.message for f in findings)


# A complete one-hop road leg (A → B, both ends located), so a fixture that is
# about something else doesn't collect endpoint findings of its own.
_LEG = {"start_location": "A", "start_coordinate": {"lat": 1, "long": 2},
        "end_location": "B", "end_coordinate": {"lat": 3, "long": 4}}


def test_example_has_no_errors():
    findings = validate_text(EXAMPLE.read_text(encoding="utf-8"))
    assert _errors(findings) == []
    assert _warnings(findings)  # optional-missing fields produce warnings


def test_line_numbers_are_tracked():
    text = '{\n  "travel_description": {\n    "title": "T"\n  },\n  "days": []\n}'
    data, lines = load_with_lines(text)
    assert data["travel_description"]["title"] == "T"
    assert lines[("travel_description", "title")] == 3
    assert lines[("days",)] == 5


def test_missing_required_title_is_error():
    findings = validate_text('{"travel_description": {}, "days": [{"title": "d"}]}')
    msgs = _messages(_errors(findings))
    assert "required field 'title' is missing" in msgs


def test_invalid_values_are_errors():
    text = json.dumps({
        "travel_description": {"title": "T", "cover_color": "nope"},
        "defaults": {"timezone": "xyz", "start_time": "9am"},
        "days": [{"title": "d", "date": "bad", "activities": [
            {"type": "point_of_interest", "name": "M"}]}],
    })
    msgs = _messages(_errors(validate_text(text)))
    assert "'cover_color' is invalid" in msgs
    assert "'timezone' is invalid" in msgs
    assert "'start_time' is invalid" in msgs
    assert "'date' is invalid" in msgs


def test_optional_missing_gives_info_with_default():
    findings = validate_text('{"travel_description": {"title": "T"}, '
                             '"days": [{"title": "d", "activities": []}]}')
    infos = _messages(_infos(findings))
    assert "optional field 'subtitle' is missing" in infos
    assert "Defaulting to" in infos
    # it is an info, not a warning
    assert "optional field 'subtitle'" not in _messages(_warnings(findings))


def test_verbose_levels_filter_output():
    from odysseyra_travelbook import format_findings

    findings = validate_text(BROKEN.read_text(encoding="utf-8"))
    lvl1 = format_findings(findings, verbose=1)
    lvl2 = format_findings(findings, verbose=2)
    lvl3 = format_findings(findings, verbose=3)
    assert "❌" in lvl1 and "⚠️" not in lvl1 and "ℹ️" not in lvl1
    assert "❌" in lvl2 and "⚠️" in lvl2 and "ℹ️" not in lvl2
    assert "❌" in lvl3 and "⚠️" in lvl3 and "ℹ️" in lvl3
    assert "hidden (raise --verbose)" in lvl1


def test_unknown_activity_type_is_error():
    text = json.dumps({
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "activities": [{"type": "spaceship"}]}],
    })
    assert "'type' is invalid" in _messages(_errors(validate_text(text)))


def test_time_duration_incompatibility_is_error():
    text = json.dumps({
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "activities": [
            {"type": "point_of_interest", "name": "M", "start_time": "09:00",
             "end_time": "11:00", "duration": "3h"}]}],
    })
    assert "incompatible" in _messages(_errors(validate_text(text)))


def test_overlapping_activities_is_error():
    text = json.dumps({
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "activities": [
            {"type": "point_of_interest", "name": "A", "start_time": "09:00", "end_time": "11:00"},
            {"type": "point_of_interest", "name": "B", "start_time": "10:30", "end_time": "12:00"}]}],
    })
    assert "overlaps an earlier item" in _messages(_errors(validate_text(text)))


def test_overlap_detects_a_non_adjacent_straddling_item():
    # A long item (A, 09:00-18:00) straddles a later, non-adjacent one (C,
    # 17:00-19:00) with a short item (B) sorted between them. A naive
    # compare-to-previous check would miss the A/C collision.
    text = json.dumps({
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "activities": [
            {"type": "point_of_interest", "name": "A", "start_time": "09:00", "end_time": "18:00"},
            {"type": "point_of_interest", "name": "B", "start_time": "09:30", "end_time": "10:00"},
            {"type": "point_of_interest", "name": "C", "start_time": "17:00", "end_time": "19:00"}]}],
    })
    msgs = _messages(_errors(validate_text(text)))
    # C overlaps A even though B (which doesn't overlap C) sits between them.
    assert "overlaps an earlier item" in msgs


def test_overlapping_accommodations_is_error():
    text = json.dumps({
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "activities": []}],
        "accommodations": [
            {"name": "A", "arrival": "2026-06-08", "departure": "2026-06-10"},
            {"name": "B", "arrival": "2026-06-09", "departure": "2026-06-11"}],
    })
    assert "overlap on the same night" in _messages(_errors(validate_text(text)))


def test_transport_reversed_dates_is_error():
    text = json.dumps({
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "activities": [{"type": "point_of_interest", "name": "M"}]}],
        "transport": [{"type": "train", "legs": [
            {"start": "A", "end": "B", "start_date": "2026-06-11",
             "start_time": "09:00", "end_date": "2026-06-10"}]}],
    })
    assert "leg end_date" in _messages(_errors(validate_text(text)))


def test_manual_reversed_trip_dates_is_error():
    doc = {"travel_description": {"title": "T", "start_date": "2026-06-10",
                                  "end_date": "2026-06-08"},
           "days": [{"title": "d", "activities": [{"type": "point_of_interest", "name": "M"}]}]}
    assert "trip end_date" in _messages(_errors(validate_text(json.dumps(doc))))


def test_dates_outside_manual_range_warn():
    doc = {"travel_description": {"title": "T", "start_date": "2026-06-08",
                                  "end_date": "2026-06-10"},
           "days": [{"title": "d", "date": "2026-06-20",
                     "activities": [{"type": "point_of_interest", "name": "M"}]}]}
    assert "outside the trip range" in _messages(_warnings(validate_text(json.dumps(doc))))


def test_manual_range_not_covering_days_warns():
    doc = {"travel_description": {"title": "T", "start_date": "2026-06-10",
                                  "end_date": "2026-06-10"},
           "days": [{"title": "a", "date": "2026-06-08",
                     "activities": [{"type": "point_of_interest", "name": "M"}]},
                    {"title": "b", "date": "2026-06-12",
                     "activities": [{"type": "point_of_interest", "name": "N"}]}]}
    msgs = _messages(_warnings(validate_text(json.dumps(doc))))
    assert "after the first day" in msgs
    assert "before the last day" in msgs


def test_road_missing_legs_is_error():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [{"type": "road"}]}]}
    assert "required field 'legs'" in _messages(_errors(validate_text(json.dumps(doc))))


def test_road_written_on_the_old_waypoint_shape_is_named():
    """The retired keys are unread now, and an unknown key is reported by
    nothing — so each one is named, with where its value has moved to."""
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "road", "start": "A", "coordinate": {"lat": 1, "long": 2},
                "off_road": True,
                "waypoints": [{"coordinate": {"lat": 3, "long": 4}, "location": "B"}]}]}]}
    w = _messages(_warnings(validate_text(json.dumps(doc))))
    for key in ("start", "coordinate", "off_road", "waypoints"):
        assert f"field '{key}' is no longer read on a road" in w


def test_poi_invalid_category_is_error():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M", "category": "alien"}]}]}
    assert "'category' is invalid" in _messages(_errors(validate_text(json.dumps(doc))))


def test_nested_activity_type_is_required_and_checked():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "place", "name": "P", "activities": [
                   "bare string",
                   {"type": "road", "start": "A", "end": "B"}]}]}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "a nested activity must be an object" in msgs
    assert "a nested activity 'type' must be one of" in msgs


def test_road_and_hike_nest_only_meals():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "road", "legs": [_LEG],
                "activities": [{"type": "point_of_interest", "name": "X"}]}]}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "a nested activity 'type' must be one of: meal" in msgs
    # a meal nested under a road is accepted
    ok = {"travel_description": {"title": "T"},
          "days": [{"title": "d", "activities": [
              {"type": "road", "legs": [_LEG],
               "activities": [{"type": "meal", "meal_type": "lunch"}]}]}]}
    assert "nested activity" not in _messages(_errors(validate_text(json.dumps(ok))))


def test_nested_poi_cannot_nest_further_is_error():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "Outer", "activities": [
                   {"type": "point_of_interest", "name": "Inner", "activities": [
                       {"type": "point_of_interest", "name": "Deep"}]}]}]}]}
    assert "only one level deep" in _messages(_errors(validate_text(json.dumps(doc))))


def _hike(**fields):
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               dict(type="hike", name="H", distance_km=5, **fields)]}]}
    return validate_text(json.dumps(doc))


def test_hike_return_route_with_different_end_warns():
    for route in ("loop", "back_and_forth"):
        msgs = _messages(_warnings(_hike(route=route, start="A", end="B")))
        assert "returns to its start" in msgs
    # end omitted or equal to start → no warning
    assert "returns to its start" not in _messages(
        _hike(route="loop", start="A"))
    assert "returns to its start" not in _messages(
        _hike(route="back_and_forth", start="A", end="A"))


def test_hike_one_way_without_distinct_end_warns():
    assert "should have an 'end'" in _messages(_warnings(_hike(route="one_way", start="A")))
    assert "should have an 'end'" in _messages(
        _warnings(_hike(route="one_way", start="A", end="A")))
    # proper one-way with a distinct end → no warning
    assert "should have an 'end'" not in _messages(
        _hike(route="one_way", start="A", end="B"))


def test_activity_without_determinable_duration_warns():
    # a point_of_interest with no duration and no start/end span
    findings = _one_day([{"type": "point_of_interest", "name": "M"}])
    assert "no duration and none can be inferred" in _messages(_warnings(findings))
    # giving both times (duration inferable) silences it
    ok = _one_day([{"type": "point_of_interest", "name": "M",
                    "start_time": "09:00", "end_time": "10:00"}])
    assert "no duration and none can be inferred" not in _messages(_warnings(ok))
    # a place whose nested activity carries a duration is fine
    ok2 = _one_day([{"type": "place", "name": "P", "activities": [
        {"type": "point_of_interest", "name": "inner", "duration": "1h"}]}])
    assert "no duration and none can be inferred" not in _messages(_warnings(ok2))


def test_single_leg_road_warns_for_each_missing_magnitude():
    # a plain A→B drive: neither duration nor distance → both listed
    w = _messages(_warnings(_one_day([{"type": "road", "legs": [_LEG]}])))
    assert "this road (A → B) should give a duration and a 'distance_km'" in w
    assert "missing: duration, distance_km" in w
    # road-level distance present, duration still missing → duration only
    w2 = _messages(_warnings(_one_day([{"type": "road", "distance_km": 12,
                                        "legs": [_LEG]}])))
    assert "missing: duration." in w2
    # both known (duration via times, distance on the road) → no warning
    w3 = _messages(_warnings(_one_day([{"type": "road", "distance_km": 12,
                                        "start_time": "09:00", "end_time": "10:00",
                                        "legs": [_LEG]}])))
    assert "this road should give" not in w3
    # the leg's own duration + distance also satisfy the single-leg drive
    w4 = _messages(_warnings(_one_day([{"type": "road", "legs": [
        dict(_LEG, duration="40 min", distance_km=30)]}])))
    assert "this road should give" not in w4


def test_multi_leg_road_warns_per_named_leg():
    # two named legs; the second lacks its distance → only that leg warns
    day = [{"type": "road", "legs": [
        dict(_LEG, duration="40 min", distance_km=30),
        {"end_location": "C", "end_coordinate": {"lat": 3, "long": 4},
         "duration": "50 min"}]}]
    w = _messages(_warnings(_one_day(day)))
    assert "this road's leg (B → C) should give a duration and a 'distance_km'" in w
    assert "missing: distance_km." in w
    assert "(A → B)" not in w  # the complete leg doesn't warn
    # a leg's route-shaping waypoints carry no figures of their own to miss
    day2 = [{"type": "road", "legs": [
        dict(_LEG, duration="40 min", distance_km=30,
             waypoints=[{"lat": 1.5, "long": 2.5}]),
        {"end_location": "C", "end_coordinate": {"lat": 3, "long": 4},
         "duration": "50 min", "distance_km": 40}]}]
    assert "this road's leg" not in _messages(_warnings(_one_day(day2)))


def test_hike_warns_for_each_missing_magnitude():
    # nothing → all three listed
    w = _messages(_warnings(_one_day([{"type": "hike", "name": "H"}])))
    assert "missing: duration, distance_km, elevation_m" in w
    # duration + distance given, elevation missing → warns for elevation only
    w2 = _messages(_warnings(_one_day([{"type": "hike", "name": "H",
                                        "duration": "2h", "distance_km": 5}])))
    assert "missing: elevation_m." in w2
    # all three present → no warning
    w3 = _messages(_warnings(_one_day([{"type": "hike", "name": "H", "duration": "2h",
                                        "distance_km": 5, "elevation_m": 800}])))
    assert "this hike should give" not in w3


def test_nested_hike_also_warns_for_missing_magnitude():
    # a hike nested inside a place must be checked too
    day = [{"type": "place", "name": "P", "activities": [
        {"type": "hike", "name": "Ridge walk", "distance_km": 4}]}]
    w = _messages(_warnings(_one_day(day)))
    assert "this hike (Ridge walk) should give" in w
    assert "missing: duration, elevation_m" in w
    # a fully-specified nested hike is silent
    ok = [{"type": "point_of_interest", "name": "POI", "activities": [
        {"type": "hike", "name": "Ridge walk", "duration": "3h",
         "distance_km": 4, "elevation_m": 500}]}]
    assert "this hike (" not in _messages(_warnings(_one_day(ok)))


def test_transport_without_determinable_duration_warns():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M"}]}],
           "transport": [{"type": "bus", "legs": [
               {"start": "A", "end": "B", "start_date": "2026-06-08",
                "start_time": "09:00"}]}]}
    findings = validate_text(json.dumps(doc))
    assert "this leg has no duration" in _messages(_warnings(findings))
    # an end_time makes the duration inferable
    doc["transport"][0]["legs"][0]["end_time"] = "12:00"
    assert "this leg has no duration" not in _messages(
        _warnings(validate_text(json.dumps(doc))))


def test_transport_required_fields_and_type_enum():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M"}]}],
           "transport": [{"type": "rocket", "legs": [{}]}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "required field 'start'" in msgs
    assert "required field 'start_date'" in msgs
    assert "'type' is invalid" in msgs


def test_transport_legs_must_be_a_non_empty_array():
    def msgs(transport):
        doc = {"travel_description": {"title": "T"},
               "days": [{"title": "d", "activities": [
                   {"type": "point_of_interest", "name": "M"}]}],
               "transport": [transport]}
        return _messages(_errors(validate_text(json.dumps(doc))))

    assert "required field 'legs' is missing" in msgs({"type": "train"})
    assert "at least one leg" in msgs({"type": "train", "legs": []})
    assert "'legs' must be an array" in msgs({"type": "train", "legs": "nope"})


def test_a_transport_field_on_the_wrong_level_is_named():
    # Neither the model nor the field tables would say anything about a key
    # written on the wrong side of the booking/leg split — it is simply unread.
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M"}]}],
           "transport": [{"type": "train", "start": "A",
                          "legs": [{"start": "A", "end": "B",
                                    "start_date": "2026-06-08",
                                    "start_time": "09:00", "duration": "1h",
                                    "price": 30}]}]}
    warnings = _messages(_warnings(validate_text(json.dumps(doc))))
    assert "field 'start' belongs on a transport leg" in warnings
    assert "field 'price' belongs on the transport booking" in warnings


def test_accommodation_required_fields_and_type_enum():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M"}]}],
           "accommodations": [{"name": "H", "type": "yurt"}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "required field 'arrival'" in msgs
    assert "required field 'city'" in msgs
    assert "'type' is invalid" in msgs


def _car(**fields):
    base = {
        "booking_start_date": "2026-06-08", "booking_start_time": "09:00",
        "booking_end_date": "2026-06-11", "booking_end_time": "20:00",
        "pickup_date": "2026-06-08", "pickup_time": "10:00",
        "dropoff_date": "2026-06-11", "dropoff_time": "18:00",
        "pickup_location": "Pau Airport",
    }
    base.update(fields)
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M"}]}],
           "car_rentals": [base]}
    return validate_text(json.dumps(doc))


def test_car_rental_missing_required_and_bad_enum_are_errors():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M"}]}],
           "car_rentals": [{"car_type": "spaceship", "additional_drivers": -1}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "required field 'booking_start_date'" in msgs
    assert "required field 'pickup_location'" in msgs
    assert "'car_type' is invalid" in msgs
    assert "'additional_drivers' is invalid" in msgs


def test_car_rental_pickup_outside_booking_period_is_error():
    msgs = _messages(_errors(_car(pickup_date="2026-06-07")))
    assert "pick-up (2026-06-07 10:00) is outside the booking period" in msgs


def test_car_rental_dropoff_outside_and_before_pickup_are_errors():
    msgs = _messages(_errors(_car(dropoff_date="2026-06-07", dropoff_time="08:00")))
    assert "drop-off (2026-06-07 08:00) is outside the booking period" in msgs
    assert "drop-off (2026-06-07 08:00) is before the pick-up" in msgs


def test_car_rental_reversed_booking_window_is_error():
    findings = _car(booking_start_date="2026-06-11", booking_end_date="2026-06-08")
    msgs = _messages(_errors(findings))
    assert "booking end (2026-06-08 20:00) must be after booking start" in msgs
    # the window is invalid, so the within-period checks are suppressed
    assert "outside the booking period" not in msgs


def test_valid_car_rental_has_no_errors():
    assert _errors(_car()) == []


def test_car_rental_pickup_conflicting_with_activity_warns():
    doc = {
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "date": "2026-06-08", "activities": [
            {"type": "point_of_interest", "name": "M",
             "start_time": "09:00", "end_time": "12:00"}]}],
        "car_rentals": [{
            "booking_start_date": "2026-06-08", "booking_start_time": "08:00",
            "booking_end_date": "2026-06-09", "booking_end_time": "20:00",
            "pickup_date": "2026-06-08", "pickup_time": "10:00",
            "pickup_duration": "30 min",
            "dropoff_date": "2026-06-09", "dropoff_time": "18:00",
            "pickup_location": "Airport"}],
    }
    msgs = _messages(_warnings(validate_text(json.dumps(doc))))
    assert "pick-up (10:00) overlaps an activity or transport" in msgs


def test_car_rental_pickup_not_conflicting_does_not_warn():
    doc = {
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "date": "2026-06-08", "activities": [
            {"type": "point_of_interest", "name": "M",
             "start_time": "09:00", "end_time": "12:00"}]}],
        "car_rentals": [{
            "booking_start_date": "2026-06-08", "booking_start_time": "08:00",
            "booking_end_date": "2026-06-09", "booking_end_time": "20:00",
            "pickup_date": "2026-06-08", "pickup_time": "12:00",
            "pickup_duration": "30 min",
            "dropoff_date": "2026-06-09", "dropoff_time": "18:00",
            "pickup_location": "Airport"}],
    }
    # pick-up 12:00–12:30 begins exactly when the activity ends → no overlap
    assert "overlaps an activity or transport" not in _messages(
        validate_text(json.dumps(doc)))


def test_empty_days_is_error():
    for days in ([], None):
        doc = {"travel_description": {"title": "T"}}
        if days is not None:
            doc["days"] = days
        assert _errors(validate_text(json.dumps(doc)))


def test_empty_activities_is_error():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": []}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "'activities' must not be empty" in msgs
    # …and only that: an empty array *is* present, so the required-field check
    # has nothing to say about it.
    assert "required field 'activities' is missing" not in msgs


def test_missing_activities_is_the_standard_required_field_error():
    # `activities` is a required field like `title` (DAY_SPECS), so an absent key
    # reads the same as any other missing one rather than as "must not be empty".
    doc = {"travel_description": {"title": "T"}, "days": [{"title": "d"}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "required field 'activities' is missing" in msgs
    assert "'activities' must not be empty" not in msgs


def _one_day(activities, **extra):
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "date": "2026-06-08", "activities": activities}]}
    doc.update(extra)
    return validate_text(json.dumps(doc))


def test_night_without_stay_warns():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d1", "date": "2026-06-08", "activities": []},
                    {"title": "d2", "date": "2026-06-09", "activities": []}]}
    msgs = _messages(_warnings(validate_text(json.dumps(doc))))
    assert "night of 2026-06-08 has no accommodation" in msgs  # d1, not the last day


def test_double_booked_night_is_info_and_prefers_accommodation():
    doc = {
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "date": "2026-06-08", "activities": []},
                 {"title": "d2", "date": "2026-06-09", "activities": []}],
        "accommodations": [{"name": "H", "arrival": "2026-06-08", "departure": "2026-06-09"}],
        "transport": [{"type": "train", "legs": [
            {"start": "A", "end": "B", "start_date": "2026-06-08",
             "start_time": "22:00", "end_time": "06:00"}]}],
    }
    findings = validate_text(json.dumps(doc))
    # the accommodation is kept; the clash is reported at info level, not error
    assert "using the accommodation" in _messages(_infos(findings))
    assert not any("accommodation and an overnight" in m for m in _messages(_errors(findings)))


def test_duplicate_and_out_of_order_day_dates_are_errors():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "a", "date": "2026-06-09", "activities": []},
                    {"title": "b", "date": "2026-06-08", "activities": []}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "earlier than the previous day" in msgs
    doc["days"][1]["date"] = "2026-06-09"
    assert "duplicated" in _messages(_errors(validate_text(json.dumps(doc))))


def test_transport_overlaps_activity_is_error():
    doc = {
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "date": "2026-06-08", "activities": [
            {"type": "point_of_interest", "name": "M", "start_time": "09:00", "end_time": "12:00"}]}],
        "transport": [{"type": "train", "legs": [
            {"start": "A", "end": "B", "start_date": "2026-06-08",
             "start_time": "11:00", "end_time": "13:00"}]}],
    }
    assert "overlaps an earlier item" in _messages(_errors(validate_text(json.dumps(doc))))


def test_day_past_midnight_is_error():
    findings = _one_day([
        {"type": "point_of_interest", "name": "A", "duration": "8h"},
        {"type": "point_of_interest", "name": "B", "duration": "9h"},
    ], default={"start_time": "09:00"})
    assert "past midnight" in _messages(_errors(findings))


def test_nonpositive_distance_and_duration_are_errors():
    findings = _one_day([
        {"type": "road", "distance_km": 0, "duration": "1h", "legs": [_LEG]},
        {"type": "hike", "name": "H", "duration": "0 min"},
    ])
    msgs = _messages(_errors(findings))
    assert "distance_km must be a positive number" in msgs
    assert "duration must be a positive length" in msgs


def test_zero_minute_buffer_is_info():
    findings = _one_day([{"type": "buffer", "duration": "0 min"}])
    assert "zero-minute buffer" in _messages(_infos(findings))
    assert "zero-minute buffer" not in _messages(_warnings(findings))


def test_paid_without_price_and_status_without_ref_warn():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": []}],
           "transport": [{"type": "train", "status": "confirmed", "paid": "paid",
                          "legs": [{"start": "A", "end": "B",
                                    "start_date": "2026-06-08",
                                    "start_time": "09:00", "duration": "1h"}]}]}
    msgs = _messages(_warnings(validate_text(json.dumps(doc))))
    assert "'status' is set but 'booking_number' is missing" in msgs
    assert "'paid' is set but 'price' is missing" in msgs


def test_accommodation_city_mismatch_warns():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "city": "Lyon", "date": "2026-06-08", "activities": []},
                    {"title": "d2", "date": "2026-06-09", "activities": []}],
           "accommodations": [{"name": "H", "city": "Paris", "arrival": "2026-06-08",
                               "departure": "2026-06-09"}]}
    assert "doesn't match the accommodation city" in _messages(_warnings(validate_text(json.dumps(doc))))


def test_nonpositive_duration_allowed_for_buffer():
    # a 0-min buffer is a warning (#11), not a duration error (#8)
    findings = _one_day([{"type": "buffer", "duration": "0 min"}])
    assert "duration must be a positive length" not in _messages(_errors(findings))


def test_activity_after_default_end_time_warns():
    doc = {
        "travel_description": {"title": "T"},
        "defaults": {"start_time": "09:00", "end_time": "17:00"},
        "days": [{"title": "d", "activities": [
            {"type": "point_of_interest", "name": "Late", "duration": "10h"}]}],
    }
    # 09:00 + 10h = 19:00, which is after the 17:00 end_time
    assert "after the day's end_time (17:00)" in _messages(
        _warnings(validate_text(json.dumps(doc))))


def test_end_of_day_check_falls_back_to_the_18h_default():
    doc = {
        "travel_description": {"title": "T"},
        "defaults": {"start_time": "09:00"},
        "days": [{"title": "d", "activities": [
            {"type": "point_of_interest", "name": "Late", "duration": "10h"}]}],
    }
    # no end_time given, so the 18:00 default is what 09:00 + 10h is checked
    # against — the check is always on now.
    assert "after the day's end_time (18:00)" in _messages(
        _warnings(validate_text(json.dumps(doc))))


def _buffer_doc(**defaults):
    doc = {"travel_description": {"title": "T"},
           "defaults": defaults,
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "A", "duration": "1h"}]}]}
    return validate_text(json.dumps(doc))


def test_fixed_buffer_with_auto_sizing_on_warns():
    msg = "'buffer' is ignored"
    # auto-sizing is on by default, so a fixed buffer alone is already a clash
    assert msg in _messages(_warnings(_buffer_doc(buffer="15 min")))
    assert msg in _messages(_warnings(_buffer_doc(buffer="15 min",
                                                  auto_sized_buffer=True)))
    # …and no clash once one of the two is out of the way
    assert msg not in _messages(_buffer_doc(buffer="15 min",
                                            auto_sized_buffer=False))
    assert msg not in _messages(_buffer_doc(auto_sized_buffer=True))


def test_missing_auto_sized_buffer_states_that_it_is_on():
    infos = _messages([f for f in _buffer_doc() if f.level == "info"])
    assert "'auto_sized_buffer' is missing" in infos
    assert "Defaulting to true (buffers are auto-sized)." in infos


def test_build_surfaces_validation_errors(tmp_path, capsys):
    from odysseyra_travelbook.cli import main

    # overlapping activities: a validator error, but the model still builds
    doc = {
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "date": "2026-06-08", "activities": [
            {"type": "point_of_interest", "name": "A", "start_time": "09:00", "end_time": "12:00"},
            {"type": "point_of_interest", "name": "B", "start_time": "10:00", "end_time": "11:00"}]}],
    }
    src = tmp_path / "t.json"
    src.write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "t.pdf"

    rc = main(["build", str(src), "-o", str(out)])
    err = capsys.readouterr().err
    assert "Validation errors" in err
    assert "❌" in err  # errors shown
    assert "ℹ️" not in err  # verbose 1 — no info
    assert out.exists() and rc == 0  # still builds


def test_malformed_json_reports_error():
    findings = validate_text('{"travel_description": {"title": "T",}')
    assert _errors(findings)
    assert "invalid JSON" in _messages(findings)


def test_road_leg_endpoints_must_be_deducible():
    """Whichever endpoint no leg names is an error, on the leg that needs it."""
    def errs(legs):
        doc = {"travel_description": {"title": "T"},
               "days": [{"title": "d", "activities": [
                   {"type": "road", "legs": legs}]}]}
        return _messages(_errors(validate_text(json.dumps(doc))))

    # the first leg must name its own departure, the last its own arrival
    assert "required field 'start_location'" in errs(
        [{"end_location": "B", "end_coordinate": {"lat": 3, "long": 4}}])
    assert "required field 'end_location'" in errs(
        [{"start_location": "A", "end_coordinate": {"lat": 3, "long": 4}}])
    assert "required field 'end_coordinate'" in errs(
        [{"start_location": "A", "end_location": "B"}])
    # a junction the next leg names is fine, and reported nowhere
    quiet = errs([{"start_location": "A", "end_coordinate": {"lat": 3, "long": 4}},
                  {"start_location": "B", "end_location": "C",
                   "end_coordinate": {"lat": 5, "long": 6}}])
    assert "end_location" not in quiet and "start_location" not in quiet
    # …but one neither side names is reported once, on the earlier leg
    lonely = errs([{"start_location": "A", "end_coordinate": {"lat": 3, "long": 4}},
                   {"end_location": "C", "end_coordinate": {"lat": 5, "long": 6}}])
    assert lonely.count("required field 'end_location'") == 1


def test_road_leg_junction_mismatch_warns():
    """Both sides may name a junction, and then they must agree — the chain uses
    the earlier leg's end, so a disagreement silently drops this leg's values."""
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "road", "legs": [
                   {"start_location": "A", "start_coordinate": {"lat": 1, "long": 2},
                    "end_location": "B", "end_coordinate": {"lat": 3, "long": 4}},
                   {"start_location": "Bee", "start_coordinate": {"lat": 9, "long": 4},
                    "end_location": "C", "end_coordinate": {"lat": 5, "long": 6}}]}]}]}
    w = _messages(_warnings(validate_text(json.dumps(doc))))
    assert "this leg departs from 'Bee' but the previous one arrives at 'B'" in w
    assert "'start_coordinate' is a kilometre or more from" in w


def test_road_leg_waypoints_are_bare_coordinates():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "road", "legs": [dict(
                   _LEG, waypoints=[{"coordinate": {"lat": 1, "long": 2}}])]}]}]}
    assert "each of a leg's 'waypoints' must be a coordinate" in _messages(
        _errors(validate_text(json.dumps(doc))))


def test_road_leg_durations_exceeding_the_road_warns():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "road", "duration": "1h", "legs": [
                   dict(_LEG, duration="40 min"),
                   {"end_location": "C", "end_coordinate": {"lat": 5, "long": 6},
                    "duration": "40 min"},
               ]}]}]}
    assert "the legs last" in _messages(_warnings(validate_text(json.dumps(doc))))


def _place_doc(nested, **fields):
    return _one_day([{"type": "place", "name": "Town",
                      "activities": nested, **fields}])


_NESTED_2H = [{"type": "point_of_interest", "name": "A", "duration": "1h"},
              {"type": "point_of_interest", "name": "B", "duration": "1h"}]


def test_place_duration_below_the_nested_total_warns():
    findings = _place_doc(_NESTED_2H, duration="1h30")
    assert ("the nested activities last 2h in total, longer than this "
            "activity's 1h30") in _messages(_warnings(findings))
    # a duration that fits, and an omitted one (it becomes the total), are quiet
    for ok in (_place_doc(_NESTED_2H, duration="3h"), _place_doc(_NESTED_2H)):
        assert "the nested activities last" not in _messages(_warnings(ok))


def test_a_missing_place_duration_states_the_nested_total_as_its_default():
    infos = _messages(_infos(_place_doc(_NESTED_2H)))
    assert ("optional field 'duration' is missing" in infos
            and "the nested activities' total" in infos)
    # every other activity keeps the generic wording
    poi = _messages(_infos(_one_day([{"type": "point_of_interest", "name": "M"}])))
    assert "Defaulting to inferred from end_time, else 0." in poi


def _pages_doc(kind: str, pages):
    extra = {"road": {"legs": [_LEG]}}
    act = {"type": kind, "name": "N", "guidebook_pages": pages}
    act.update(extra.get(kind, {}))
    return json.dumps({"travel_description": {"title": "T"},
                       "days": [{"title": "d", "activities": [act]}]})


def test_guidebook_pages_accepts_pages_and_ranges():
    # A page, a range, a comma-separated list, and a range typed with the
    # en-dash a book would print — all valid, on every type that has the field.
    for kind in ("road", "point_of_interest", "place", "hike"):
        for pages in ("14", "15-18", "16, 23, 25-30", "88–91"):
            findings = validate_text(_pages_doc(kind, pages))
            assert _errors(findings) == [], (kind, pages, _messages(_errors(findings)))


def test_guidebook_pages_rejects_prose():
    # The value holds page numbers only — the renderers add the "p." themselves,
    # so a pasted "see pp. 12-14" is an error, not silently printed.
    for pages in ("see pp. 12-14", "p. 12", "chapter 4", "12-", "1-2-3"):
        messages = _messages(_errors(validate_text(
            _pages_doc("point_of_interest", pages))))
        assert "must be page numbers like '14', '15-18' or '16, 23, 25-30'" in messages, pages


def test_booking_description_is_free_text_and_only_noted_when_absent():
    # `description` on transport / accommodation / car rental is a note: any
    # text is accepted (so it never errors), and its absence is only an info
    # stating the default — the same shape as the activities' own description.
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M"}]}],
           "transport": [{"legs": [
               {"start": "A", "end": "B", "start_date": "2026-06-08",
                "start_time": "10:00", "duration": "1h"}]}],
           "accommodations": [{"name": "H", "city": "B", "arrival": "2026-06-08",
                               "departure": "2026-06-09"}]}
    infos = _messages(_infos(validate_text(json.dumps(doc))))
    assert "optional field 'description' is missing" in infos
    assert "a short note for whatever the other fields don't cover" in infos

    doc["transport"][0]["legs"][0]["description"] = "Coach 12; platform posted late."
    doc["accommodations"][0]["description"] = "Keypad code 4589B."
    findings = validate_text(json.dumps(doc))
    assert _errors(findings) == [], _messages(_errors(findings))


def test_kyrgyzstan_example_has_no_errors():
    findings = validate_text((EXAMPLES / "kyrgyzstan.json").read_text(encoding="utf-8"))
    assert _errors(findings) == []


def test_bad_coordinate_and_inference_country_are_errors():
    doc = {"travel_description": {"title": "T"},
           "defaults": {"inference_countries": ["France", "KG"]},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M",
                "coordinate": {"lat": 999, "long": 0}}]}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "field 'coordinate' is invalid" in msgs
    assert "inference country 'France' is invalid" in msgs


def test_maps_coherence_info_and_warning():
    doc = {"travel_description": {"title": "T"},
           "defaults": {"include_maps_in_render": True,
                        "infer_coordinates_from_address": False,
                        "inference_countries": ["FR"]},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "No coord here"}]}]}
    findings = validate_text(json.dumps(doc))
    assert "won't appear on the day map" in _messages(_infos(findings))
    # inference_countries set but inference off -> warning
    assert "'inference_countries' is set but" in _messages(_warnings(findings))


def test_maps_coherence_silent_when_maps_off():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "No coord"}]}]}
    assert "won't appear on the day map" not in _messages(validate_text(json.dumps(doc)))


def test_place_without_coordinate_is_centroid_pinned():
    # a place with no coordinate of its own, but with located sub-activities,
    # is pinned at their average -> an info, not a "won't appear" warning.
    doc = {"travel_description": {"title": "T"},
           "defaults": {"include_maps_in_render": True,
                        "infer_coordinates_from_address": False},
           "days": [{"title": "d", "activities": [
               {"type": "place", "name": "Old town", "activities": [
                   {"type": "point_of_interest", "name": "A",
                    "coordinate": {"lat": 1.0, "long": 2.0}},
                   {"type": "point_of_interest", "name": "B",
                    "coordinate": {"lat": 3.0, "long": 4.0}}]}]}]}
    infos = _messages(_infos(validate_text(json.dumps(doc))))
    assert "will be placed at the average position" in infos
    assert "won't appear on the day map" not in infos


def test_place_without_located_subs_wont_appear():
    # a place with neither its own coordinate nor any located sub-activity
    # falls back to the plain "won't appear" info.
    doc = {"travel_description": {"title": "T"},
           "defaults": {"include_maps_in_render": True,
                        "infer_coordinates_from_address": False},
           "days": [{"title": "d", "activities": [
               {"type": "place", "name": "Old town", "activities": [
                   {"type": "point_of_interest", "name": "A"}]}]}]}
    infos = _messages(_infos(validate_text(json.dumps(doc))))
    assert "won't appear on the day map" in infos
    assert "will be placed at the average position" not in infos


def test_broken_example_output_snapshot():
    """The committed validator output for examples/broken.json must match the
    current validator. Regenerate it with `UPDATE_SNAPSHOTS=1 pytest` whenever
    the JSON format or messages change."""
    current = format_findings(validate_text(BROKEN.read_text(encoding="utf-8")),
                              verbose=3)
    if os.environ.get("UPDATE_SNAPSHOTS"):
        BROKEN_OUTPUT.write_text(current + "\n", encoding="utf-8")
    expected = BROKEN_OUTPUT.read_text(encoding="utf-8").rstrip("\n")
    assert current == expected, (
        "examples/broken_validator_output.txt is stale — regenerate with "
        "`UPDATE_SNAPSHOTS=1 pytest`"
    )
