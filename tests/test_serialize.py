"""Tests for the resolved-model serializer (`travelbook.models.to_dict`).

The serializer is the contract the PWA renders from, so these assert that it
(a) is pure JSON, (b) carries *resolved* values (inferred times/dates, meal
categories, converted prices) rather than raw input, and (c) precomputes the
per-day associations the renderer needs.
"""

import json
from pathlib import Path

from travelbook import Itinerary, to_dict

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
    # as start/end — so a transport keeps its departure/arrival place names.
    d = _load(PYRENEES)
    assert d["transports"], "the example has transports"
    for t in d["transports"]:
        assert isinstance(t["start"], str) and t["start"], "start is a place name"
        assert isinstance(t["end"], str), "end is a place name"
        # tz travels under its own keys (int minutes or None) + a label string.
        assert "start_tz" in t and "end_tz" in t
        assert isinstance(t["start_tz_label"], str)


def test_road_waypoints_and_legs_are_serialized():
    d = _load(PYRENEES)
    roads = [a for day in d["days"] for a in _all_activities(day)
             if a["type"] == "road"]
    assert roads, "the example contains road activities"
    road = roads[0]
    assert road["start"]
    assert road["waypoints"], "a road serializes its ordered waypoints"
    assert road["destination"], "destination resolves from the last named waypoint"
