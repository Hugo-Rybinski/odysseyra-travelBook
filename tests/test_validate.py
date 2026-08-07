import json
import os
from pathlib import Path

from travelbook import format_findings, validate_text
from travelbook.validate import load_with_lines

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
    from travelbook import format_findings

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
    assert "overlaps the previous" in _messages(_errors(validate_text(text)))


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
        "transport": [{"type": "train", "start_date": "2026-06-11",
                       "end_date": "2026-06-10"}],
    })
    assert "transport end_date" in _messages(_errors(validate_text(text)))


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


def test_road_missing_waypoints_is_error():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [{"type": "road", "start": "A"}]}]}
    assert "required field 'waypoints'" in _messages(_errors(validate_text(json.dumps(doc))))


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
               {"type": "road", "start": "A",
                "waypoints": [{"coordinate": {"lat": 1, "long": 2}, "location": "B"}],
                "activities": [{"type": "point_of_interest", "name": "X"}]}]}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "a nested activity 'type' must be one of: meal" in msgs
    # a meal nested under a road is accepted
    ok = {"travel_description": {"title": "T"},
          "days": [{"title": "d", "activities": [
              {"type": "road", "start": "A",
               "waypoints": [{"coordinate": {"lat": 1, "long": 2}, "location": "B"}],
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


def test_hike_missing_distance_warns():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "hike", "name": "H", "duration": "2h"}]}]}
    findings = validate_text(json.dumps(doc))
    assert "optional field 'distance_km' is missing" in _messages(_warnings(findings))
    # and it is a ⚠️ warning, not an ℹ️ info
    assert "distance_km" not in _messages(_infos(findings))


def test_transport_required_fields_and_type_enum():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M"}]}],
           "transport": [{"type": "rocket"}]}
    msgs = _messages(_errors(validate_text(json.dumps(doc))))
    assert "required field 'start'" in msgs
    assert "required field 'start_date'" in msgs
    assert "'type' is invalid" in msgs


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
    assert "'activities' must not be empty" in _messages(_errors(validate_text(json.dumps(doc))))
    # a missing activities array is also flagged
    doc2 = {"travel_description": {"title": "T"}, "days": [{"title": "d"}]}
    assert "'activities' must not be empty" in _messages(_errors(validate_text(json.dumps(doc2))))


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


def test_double_booked_night_is_error():
    doc = {
        "travel_description": {"title": "T"},
        "days": [{"title": "d", "date": "2026-06-08", "activities": []},
                 {"title": "d2", "date": "2026-06-09", "activities": []}],
        "accommodations": [{"name": "H", "arrival": "2026-06-08", "departure": "2026-06-09"}],
        "transport": [{"type": "night train", "start_date": "2026-06-08",
                       "start_time": "22:00", "end_time": "06:00"}],
    }
    assert "sleep in two places" in _messages(_errors(validate_text(json.dumps(doc))))


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
        "transport": [{"type": "train", "start_date": "2026-06-08",
                       "start_time": "11:00", "end_time": "13:00"}],
    }
    assert "overlaps the previous item" in _messages(_errors(validate_text(json.dumps(doc))))


def test_day_past_midnight_is_error():
    findings = _one_day([
        {"type": "point_of_interest", "name": "A", "duration": "8h"},
        {"type": "point_of_interest", "name": "B", "duration": "9h"},
    ], default={"start_time": "09:00"})
    assert "past midnight" in _messages(_errors(findings))


def test_nonpositive_distance_and_duration_are_errors():
    findings = _one_day([
        {"type": "road", "start": "A", "distance_km": 0, "duration": "1h",
         "waypoints": [{"coordinate": {"lat": 1, "long": 2}, "location": "B"}]},
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
           "transport": [{"type": "train", "status": "confirmed", "paid": "paid"}]}
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


def test_no_end_time_check_when_default_end_time_absent():
    doc = {
        "travel_description": {"title": "T"},
        "defaults": {"start_time": "09:00"},
        "days": [{"title": "d", "activities": [
            {"type": "point_of_interest", "name": "Late", "duration": "10h"}]}],
    }
    assert "after the day's end_time" not in _messages(validate_text(json.dumps(doc)))


def test_build_surfaces_validation_errors(tmp_path, capsys):
    from travelbook.cli import main

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


def test_road_waypoint_requires_coordinate():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "road", "start": "A",
                "waypoints": [{"location": "no coord"}]}]}]}
    assert "a waypoint needs a 'coordinate'" in _messages(
        _errors(validate_text(json.dumps(doc))))


def test_road_waypoint_durations_exceeding_road_warns():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "road", "start": "A", "duration": "1h",
                "waypoints": [
                    {"coordinate": {"lat": 1, "long": 2}, "duration": "40 min"},
                    {"coordinate": {"lat": 1, "long": 2}, "duration": "40 min"},
                ]}]}]}
    assert "the waypoint segments last" in _messages(
        _warnings(validate_text(json.dumps(doc))))


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
