"""Tests for the resolved-model serializer (`odysseyra_travelbook.models.to_dict`).

The serializer is the contract the PWA renders from, so these assert that it
(a) is pure JSON, (b) carries *resolved* values (inferred times/dates, meal
categories, converted prices) rather than raw input, and (c) precomputes the
per-day associations the renderer needs.
"""

import json
from pathlib import Path

from odysseyra_travelbook import Itinerary, to_dict

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
PYRENEES = EXAMPLES / "pyrenees.json"
KYRGYZSTAN = EXAMPLES / "kyrgyzstan.json"


def _load(path):
    return to_dict(Itinerary.from_json_file(path))


def _all_activities(day):
    """Every activity of a day, flattening one level of nesting."""
    for act in day["activities"]:
        yield act
        for sub in act.get("activities", []):
            yield sub


def test_output_is_pure_json():
    # dumps() would raise on any non-serializable value (date/time/dataclass).
    for path in (PYRENEES, KYRGYZSTAN):
        blob = json.dumps(_load(path))
        assert json.loads(blob)  # round-trips


def test_trip_level_dates_are_inferred_and_iso():
    d = _load(PYRENEES)
    # pyrenees has no manual start/end date — both are inferred from content.
    assert d["start_date"] and d["end_date"]
    assert d["start_date"] <= d["end_date"]
    # ISO YYYY-MM-DD strings, not date objects.
    assert d["start_date"] == "2026-06-07"
    assert d["day_count"] == len(d["days"]) == 4


def test_day_dates_are_filled_from_the_trip_start():
    d = _load(PYRENEES)
    dates = [day["date"] for day in d["days"]]
    assert all(dates), "every day should have a resolved date"
    assert dates == sorted(dates), "day dates run in order"


def test_activity_timeline_is_resolved():
    d = _load(PYRENEES)
    day0 = d["days"][0]
    assert day0["activities"], "day 0 has a timeline"
    for act in day0["activities"]:
        # scheduling filled in concrete times and a duration for each item.
        assert act["start_time"] is not None
        assert act["end_time"] is not None
        assert act["duration_min"] is not None
        assert act["type"]  # kind is always present


def test_meal_categories_are_resolved():
    # Every meal (top-level or nested) gets a concrete category after scheduling.
    d = _load(PYRENEES)
    meals = [a for day in d["days"] for a in _all_activities(day)
             if a["type"] == "meal"]
    assert meals, "the example contains meals"
    for meal in meals:
        assert meal["category"] in (
            "breakfast", "lunch", "dinner", "brunch", "snack", "picnic", "meal"
        )


def test_prices_are_converted_to_the_default_currency():
    d = _load(PYRENEES)
    assert d["default_currency"] == "EUR"
    # find the USD-priced transport and check it is converted to EUR.
    priced = [t for t in d["transports"]
              if t["price"] and t["price"]["currency"] == "USD"]
    assert priced, "the example has a USD-priced transport"
    price = priced[0]["price"]
    # 667 USD at a 1.09 USD-per-EUR rate ≈ 611.93 EUR.
    assert abs(price["in_default"] - 667 / 1.09) < 1e-6
    # secondary conversions are present and round-trip back to the original.
    usd = next(s for s in price["secondaries"] if s["currency"] == "USD")
    assert abs(usd["amount"] - 667) < 1e-6


def test_per_day_associations_are_precomputed():
    d = _load(PYRENEES)
    # at least one night has a resolved stay carrying a sleep_city.
    stays = [day for day in d["days"] if day["stay"]]
    assert stays, "at least one night should resolve to an accommodation"
    for day in stays:
        assert day["stay"]["name"]
        assert day["sleep_city"]
        # the night index within the stay is 1-based and within the total.
        assert day["stay_night"] is not None
        total = day["stay"]["nights"]
        if total:
            assert 1 <= day["stay_night"] <= total
    # day_number is 1-based and matches order.
    assert [day["day_number"] for day in d["days"]] == list(
        range(1, len(d["days"]) + 1)
    )


def test_coordinates_are_carried_through():
    # kyrgyzstan is the maps-on example with explicit coordinates.
    d = _load(KYRGYZSTAN)
    located = [a for day in d["days"] for a in _all_activities(day)
               if a.get("coordinate")]
    assert located, "kyrgyzstan has explicitly located activities"
    c = located[0]["coordinate"]
    assert set(c) == {"lat", "long", "show_on_map"}
    assert isinstance(c["lat"], (int, float))
    assert isinstance(c["long"], (int, float))


def test_scheduled_tz_keys_do_not_clobber_place_names():
    # Regression: the timeline UTC offsets serialize as start_tz/end_tz, never
    # as start/end — so a leg keeps its departure/arrival place names.
    d = _load(PYRENEES)
    assert d["transports"], "the example has transports"
    legs = [leg for t in d["transports"] for leg in t["legs"]]
    assert legs, "every booking carries at least one leg"
    for leg in legs:
        assert isinstance(leg["start"], str) and leg["start"], "start is a place"
        assert isinstance(leg["end"], str), "end is a place name"
        # tz travels under its own keys (int minutes or None) + a label string.
        assert "start_tz" in leg and "end_tz" in leg
        assert isinstance(leg["start_tz_label"], str)


def test_road_legs_serialize_as_the_waypoint_chain():
    """The input's `legs` are lowered before serialization: the resolved document
    carries the departure plus the ordered waypoints, which is what both
    renderers read — so moving the input onto legs moved no renderer."""
    d = _load(PYRENEES)
    roads = [a for day in d["days"] for a in _all_activities(day)
             if a["type"] == "road"]
    assert roads, "the example contains road activities"
    road = roads[0]
    assert road["start"], "the first leg's departure"
    assert road["waypoints"], "one entry per leg (plus its route-shaping points)"
    assert road["destination"], "destination resolves from the last leg's arrival"
    assert "legs" not in road, "the resolved road is the chain, not the input legs"
    assert "description" in road, "a road carries its optional free prose"


def test_road_description_is_optional_and_round_trips():
    # A road's `description` holds what the structured fields can't say. It
    # defaults to "" (so the renderers simply skip it) and survives to_dict.
    base = {"type": "road", "legs": [
        {"start_location": "Sarlat", "end_location": "Cauterets",
         "end_coordinate": {"lat": 43.0, "long": 0.1}}]}
    it = Itinerary.from_dict({"travel_description": {"title": "T"},
                              "days": [{"title": "D", "activities": [base]}]})
    assert to_dict(it)["days"][0]["activities"][0]["description"] == ""

    with_desc = dict(base, description="Narrow above Pierrefitte; slow in season.")
    it2 = Itinerary.from_dict({"travel_description": {"title": "T"},
                               "days": [{"title": "D", "activities": [with_desc]}]})
    road2 = to_dict(it2)["days"][0]["activities"][0]
    assert road2["description"] == "Narrow above Pierrefitte; slow in season."


def test_guidebook_pages_on_every_described_type():
    # `guidebook_pages` rides along with `description`: the same four types carry
    # it, it defaults to "" and it reaches the serialized dict verbatim (the
    # renderers add the "p." themselves), whitespace-trimmed.
    acts = [
        {"type": "road", "guidebook_pages": " 132 ", "legs": [
            {"start_location": "Sarlat", "end_location": "Cauterets",
             "end_coordinate": {"lat": 43.0, "long": 0.1}}]},
        {"type": "point_of_interest", "name": "Louvre",
         "guidebook_pages": "44-47"},
        {"type": "place", "name": "Latin Quarter",
         "guidebook_pages": "16, 23, 25-30"},
        {"type": "hike", "name": "Lac de Gaube"},  # none given → ""
    ]
    it = Itinerary.from_dict({"travel_description": {"title": "T"},
                              "days": [{"title": "D", "activities": acts}]})
    pages = [a["guidebook_pages"] for a in to_dict(it)["days"][0]["activities"]
             if a["type"] != "buffer"]
    assert pages == ["132", "44-47", "16, 23, 25-30", ""]


def test_guidebook_pages_on_a_nested_activity():
    # A stop nested under a container keeps its own pages (the area's are
    # independent), so the viewer's nested rows can show them.
    it = Itinerary.from_dict({"travel_description": {"title": "T"},
                              "days": [{"title": "D", "activities": [
                                  {"type": "place", "name": "Area",
                                   "guidebook_pages": "52",
                                   "activities": [
                                       {"type": "point_of_interest",
                                        "name": "Panthéon",
                                        "guidebook_pages": "56"}]}]}]})
    place = to_dict(it)["days"][0]["activities"][0]
    assert place["guidebook_pages"] == "52"
    assert place["activities"][0]["guidebook_pages"] == "56"


def _booked_itinerary(**notes) -> dict:
    """A one-day trip with a leg, a stay and a rental, each optionally carrying a
    `description` — the three sections that share the short-note field."""
    return {
        "travel_description": {"title": "T"},
        "days": [{"title": "D", "date": "2026-06-08"}],
        "transport": [{"legs": [dict({"start": "Paris", "end": "Pau",
                                      "start_date": "2026-06-08",
                                      "start_time": "13:50",
                                      "duration": "4h20"},
                                     **({"description": notes["transport"]}
                                        if "transport" in notes else {}))]}],
        "accommodations": [dict({"name": "Gîte", "city": "Pau",
                                 "arrival": "2026-06-08",
                                 "departure": "2026-06-09"},
                                **({"description": notes["accommodation"]}
                                   if "accommodation" in notes else {}))],
        "car_rentals": [dict({"pickup_location": "Pau Airport",
                              "booking_start_date": "2026-06-08",
                              "booking_start_time": "18:00",
                              "booking_end_date": "2026-06-09",
                              "booking_end_time": "20:00",
                              "pickup_date": "2026-06-08",
                              "pickup_time": "18:15",
                              "dropoff_date": "2026-06-09",
                              "dropoff_time": "19:30"},
                             **({"description": notes["car_rental"]}
                                if "car_rental" in notes else {}))],
    }


def test_booking_descriptions_default_to_empty_and_round_trip():
    # Transport, accommodation and car rental each carry a short free-text note
    # for whatever their structured fields don't. It defaults to "" (so both
    # renderers simply skip it) and reaches the serialized dict verbatim.
    plain = to_dict(Itinerary.from_dict(_booked_itinerary()))
    # On transport the note is the leg's; the booking itself carries none.
    assert plain["transports"][0]["legs"][0]["description"] == ""
    assert plain["accommodations"][0]["description"] == ""
    assert plain["car_rentals"][0]["description"] == ""

    filled = to_dict(Itinerary.from_dict(_booked_itinerary(
        transport="Coach 12, seats 41/42.",
        accommodation="Keypad code 4589B.",
        car_rental="Full-to-full fuel policy.")))
    assert (filled["transports"][0]["legs"][0]["description"]
            == "Coach 12, seats 41/42.")
    assert filled["accommodations"][0]["description"] == "Keypad code 4589B."
    assert filled["car_rentals"][0]["description"] == "Full-to-full fuel policy."


def test_a_days_stay_and_leg_carry_their_note():
    # The day's own copies (used by the stay bar and the day's transport row) are
    # the same objects, so the note reaches them too.
    day = to_dict(Itinerary.from_dict(_booked_itinerary(
        transport="Coach 12.", accommodation="Keypad code 4589B.")))["days"][0]
    assert day["stay"]["description"] == "Keypad code 4589B."
    assert day["transports"][0]["description"] == "Coach 12."


def test_a_car_event_carries_its_rentals_note():
    # A resolved CarRentalEvent has no way back to its rental, so the note is
    # copied onto *both* events — that's where the day's row reads it.
    day = to_dict(Itinerary.from_dict(
        _booked_itinerary(car_rental="Desk at level -1.")))["days"][0]
    assert day["car_events"], "the pick-up lands on its day"
    assert all(ev["description"] == "Desk at level -1."
               for ev in day["car_events"])


def test_map_pin_defaults_to_none_and_reflects_stamp():
    # Every activity/accommodation carries a `map_pin` key; it is None unless a
    # caller (the PWA bridge, from the rendered day maps) stamps `_map_pin` on
    # the model object.
    it = Itinerary.from_json_file(KYRGYZSTAN)
    plain = to_dict(it)
    for day in plain["days"]:
        for act in _all_activities(day):
            assert act["map_pin"] is None
        if day["stay"]:
            assert day["stay"].get("map_pin") is None

    # Stamping the model object surfaces the label in the serialized dict.
    first_act = it.days[0].activities[0]
    first_act._map_pin = "1"
    stamped = to_dict(it)
    assert stamped["days"][0]["activities"][0]["map_pin"] == "1"
