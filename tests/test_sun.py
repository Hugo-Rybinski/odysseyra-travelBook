"""Sunrise/sunset computation, the day's reference coordinate, and the
opt-out wiring (``defaults.show_sun_times``) into the serialized model."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from odysseyra_travelbook.lang import tr
from odysseyra_travelbook.models import (
    Itinerary,
    activity_from_dict,
    sun_times,
    to_dict,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _hhmm(t):
    return f"{t:%H:%M}"


# Published sunrise/sunset for well-known places, in local wall time. The NOAA
# equation is good to about a minute at these latitudes, so allow ±2.
@pytest.mark.parametrize(
    "day,lat,long,tz,rise,fall",
    [
        (date(2026, 6, 21), 51.5074, -0.1278, 60, "04:43", "21:21"),    # London, solstice
        (date(2026, 12, 21), 51.5074, -0.1278, 0, "08:04", "15:53"),    # London, solstice
        (date(2026, 6, 21), 48.8566, 2.3522, 120, "05:47", "21:58"),    # Paris
        (date(2026, 6, 21), 35.6762, 139.6503, 540, "04:25", "19:00"),  # Tokyo
        (date(2026, 6, 21), -33.8688, 151.2093, 600, "07:00", "16:54"), # Sydney (winter)
        (date(2026, 3, 20), -0.1807, -78.4678, -300, "06:19", "18:26"), # Quito, equinox
    ],
)
def test_matches_published_times(day, lat, long, tz, rise, fall):
    s = sun_times(day, lat, long, tz)
    assert s is not None
    for got, want in ((_hhmm(s.sunrise), rise), (_hhmm(s.sunset), fall)):
        got_min = int(got[:2]) * 60 + int(got[3:])
        want_min = int(want[:2]) * 60 + int(want[3:])
        assert abs(got_min - want_min) <= 2, f"{got} vs {want}"


def test_hhmm_pairs_the_two_times_for_the_display_template():
    s = sun_times(date(2026, 6, 21), 48.8566, 2.3522, 120)
    assert s.hhmm == (_hhmm(s.sunrise), _hhmm(s.sunset))


# The display string is language-dependent, so it lives in the renderers. This
# pins the PDF's template; the viewer keys the same English source in
# render/format.ts.
DISPLAY = "☀️ Sunrise: {sunrise}, Sunset: {sunset}"


def test_display_template_is_localized():
    filled = {"sunrise": "07:12", "sunset": "20:27"}
    assert tr(DISPLAY, "en").format(**filled) == "☀️ Sunrise: 07:12, Sunset: 20:27"
    assert tr(DISPLAY, "fr").format(**filled) == "☀️ Lever : 07:12, Coucher : 20:27"


def test_display_glyphs_are_in_the_bundled_font():
    # DejaVu carries the sun and the emoji variation selector, so "☀️" renders
    # without a missing-glyph box — no emoji fallback font needed here (unlike
    # the moon phases).
    from fontTools.ttLib import TTFont
    fonts = Path(__file__).resolve().parent.parent / "src/odysseyra_travelbook/fonts"
    cmap = TTFont(str(fonts / "DejaVuSans.ttf")).getBestCmap()
    for lang in ("en", "fr"):
        for ch in tr(DISPLAY, lang):
            if ch not in "{}":
                assert ord(ch) in cmap or ch.isalnum(), f"U+{ord(ch):04X} missing"


def test_polar_day_and_night_have_no_times():
    # Longyearbyen: midnight sun in June, polar night in December.
    assert sun_times(date(2026, 6, 21), 78.2232, 15.6469, 120) is None
    assert sun_times(date(2026, 12, 21), 78.2232, 15.6469, 60) is None


def test_timezone_shifts_the_clock_not_the_event():
    utc = sun_times(date(2026, 6, 21), 48.8566, 2.3522, 0)
    local = sun_times(date(2026, 6, 21), 48.8566, 2.3522, 120)
    assert local.sunrise.hour - utc.sunrise.hour == 2


def _trip(**defaults):
    """A two-day trip with a located stay on the first night only."""
    return Itinerary.from_dict({
        "travel_description": {"title": "Sun", "start_date": "2026-06-21"},
        "defaults": {"timezone": "+02:00", **defaults},
        "days": [{"title": "One"}, {"title": "Two"}],
        "accommodations": [{
            "name": "Hôtel du Soleil",
            "arrival": "2026-06-21",
            "departure": "2026-06-22",
            "city": "Paris",
            "coordinate": {"lat": 48.8566, "long": 2.3522},
        }],
    })


def test_on_by_default_from_the_stay_coordinate():
    it = _trip()
    assert it.show_sun_times is True
    day = it.days[0]
    assert it.sun_reference(day.date) is it.accommodations[0].coordinate
    assert it.sun_for(day).hhmm == sun_times(day.date, 48.8566, 2.3522, 120).hhmm


def test_falls_back_to_the_nearest_located_stay():
    # The second night has no stay of its own and nothing located of its own
    # either; it borrows the first's coordinate rather than showing nothing.
    it = _trip()
    second = it.days[1]
    assert it.stay_for(second.date) is None
    assert it.sun_for(second) is not None
    assert it.sun_reference(second.date, second) is it.accommodations[0].coordinate


def test_a_stayless_day_prefers_its_own_location():
    # No stay covers night two, but the day itself happens somewhere known —
    # that beats a hotel elsewhere. Both are in the same clock here, so the
    # times are shown either way; only the reference differs.
    it = _trip()
    it.days[1].activities.insert(0, activity_from_dict({
        "type": "point_of_interest", "name": "Chartres cathedral",
        "coordinate": {"lat": 48.4477, "long": 1.4879},
    }))
    ref = it.sun_reference(it.days[1].date, it.days[1])
    assert (ref.lat, ref.long) == (48.4477, 1.4879)
    assert it.sun_for(it.days[1]) is not None


def test_nested_activities_can_locate_the_day():
    it = _trip()
    it.days[1].activities.insert(0, activity_from_dict({
        "type": "place", "name": "Chartres", "activities": [
            {"type": "point_of_interest", "name": "The cathedral",
             "coordinate": {"lat": 48.4477, "long": 1.4879}},
        ],
    }))
    ref = it.sun_reference(it.days[1].date, it.days[1])
    assert (ref.lat, ref.long) == (48.4477, 1.4879)


def test_a_reference_outside_the_days_clock_shows_nothing():
    # A New York day printed on Paris time: the honest answer there is
    # "☀ 12:57 → 01:33", which reads as a bug, so nothing is shown at all.
    it = _trip()
    day = it.days[1]
    day.activities.insert(0, activity_from_dict({
        "type": "point_of_interest", "name": "Times Square",
        "coordinate": {"lat": 40.758, "long": -73.9855},
    }))
    assert it.day_timezone(day) == 120  # the trip's clock, +02:00
    assert it.sun_reference(day.date, day).long == -73.9855
    assert it.sun_for(day) is None
    # Tag the day with its real zone and the times come back.
    day.activities[0].start_tz = -240
    assert it.sun_for(day) is not None


def test_france_day_one_is_a_new_york_day_on_paris_time():
    # The flagship example: day 1 is spent in New York and the night is aboard
    # the flight, so no times are printed — rather than Paris's.
    it = Itinerary.from_json_file(str(EXAMPLES / "france.json"))
    assert it.days[0].city == "New York"
    assert it.sun_for(it.days[0]) is None
    assert all(it.sun_for(d) is not None for d in it.days[1:])


def _moving_trip():
    """Three nights, three towns: you wake somewhere different each morning."""
    return Itinerary.from_dict({
        "travel_description": {"title": "Sun", "start_date": "2026-06-21"},
        "defaults": {"timezone": "+02:00"},
        "days": [{"title": "One"}, {"title": "Two"}, {"title": "Three"}],
        "accommodations": [
            {"name": "A", "city": "Strasbourg", "arrival": "2026-06-21",
             "departure": "2026-06-22", "coordinate": {"lat": 48.5734, "long": 7.7521}},
            {"name": "B", "city": "Brest", "arrival": "2026-06-22",
             "departure": "2026-06-23", "coordinate": {"lat": 48.3904, "long": -4.4861}},
            {"name": "C", "city": "Nice", "arrival": "2026-06-23",
             "departure": "2026-06-24", "coordinate": {"lat": 43.7102, "long": 7.2620}},
        ],
    })


def test_sunrise_comes_from_where_you_woke():
    # Day 2: woke in Strasbourg (east), sleeps in Brest (west) — 800 km apart, so
    # the two ends must not share a reference.
    it = _moving_trip()
    day = it.days[1]
    strasbourg, brest = it.accommodations[0].coordinate, it.accommodations[1].coordinate
    assert it.wake_reference(day.date, day) is strasbourg
    assert it.sun_reference(day.date, day) is brest

    got = it.sun_for(day)
    assert got.sunrise == sun_times(day.date, strasbourg.lat, strasbourg.long, 120).sunrise
    assert got.sunset == sun_times(day.date, brest.lat, brest.long, 120).sunset
    # Sanity: pinning both ends to one town would have been visibly wrong.
    single = sun_times(day.date, brest.lat, brest.long, 120)
    assert got.sunrise != single.sunrise


def test_a_day_that_stays_put_is_unaffected():
    it = _moving_trip()
    # Give night 1 and night 2 the same hotel, so you wake where you'll sleep.
    it.accommodations[1].coordinate = it.accommodations[0].coordinate
    day = it.days[1]
    got = it.sun_for(day)
    one = sun_times(day.date, it.accommodations[0].coordinate.lat,
                    it.accommodations[0].coordinate.long, 120)
    assert (got.sunrise, got.sunset) == (one.sunrise, one.sunset)


def test_the_first_morning_has_no_preceding_stay():
    # Nothing precedes night one and the day locates nothing of its own, so the
    # morning chain lands on its last resort — the nearest dated stay, which here
    # is that same night's — and both ends agree.
    it = _moving_trip()
    day = it.days[0]
    a = it.accommodations[0].coordinate
    assert it.wake_reference(day.date, day) is a
    assert it.sun_for(day).hhmm == sun_times(day.date, a.lat, a.long, 120).hhmm


def test_a_night_spent_travelling_wakes_at_the_days_first_stop():
    # france.json day 2: the night before was spent aboard the transatlantic
    # flight, so there's no stay to wake at. The morning falls to the day's own
    # first located activity — in Paris — rather than reaching back to New York
    # for a nonsense "12:27".
    it = Itinerary.from_json_file(str(EXAMPLES / "france.json"))
    day = it.days[1]
    assert it.stay_for(day.date - timedelta(days=1)) is None
    woke = it.wake_reference(day.date, day)
    assert woke is not None
    # Roissy/CDG, where the flight lands — the Paris region, not New York.
    assert 48 < woke.lat < 50 and 1 < woke.long < 4
    got = it.sun_for(day)
    tz = it.day_timezone(day)
    assert got.sunrise == sun_times(day.date, woke.lat, woke.long, tz).sunrise


def test_the_sunset_uses_the_days_last_stop_not_its_first():
    # A stayless day that drives east to west: the sunset belongs at the far end.
    it = _moving_trip()
    it.accommodations = []  # no stay anywhere, so both chains use the activities
    day = it.days[1]
    day.activities = [
        activity_from_dict({"type": "point_of_interest", "name": "Strasbourg",
                            "coordinate": {"lat": 48.5734, "long": 7.7521}}),
        activity_from_dict({"type": "point_of_interest", "name": "Brest",
                            "coordinate": {"lat": 48.3904, "long": -4.4861}}),
    ]
    assert it.sun_reference(day.date, day).long == -4.4861  # sunset: last stop
    assert it.wake_reference(day.date, day).long == 7.7521  # sunrise: first stop
    got = it.sun_for(day)
    assert got.sunrise == sun_times(day.date, 48.5734, 7.7521, 120).sunrise
    assert got.sunset == sun_times(day.date, 48.3904, -4.4861, 120).sunset


def test_a_roads_final_waypoint_can_close_the_day():
    # A drive's own coordinate is its departure and its waypoints the stops
    # through to the arrival, so the last waypoint is where the day ends up.
    it = _moving_trip()
    it.accommodations = []
    day = it.days[1]
    day.activities = [activity_from_dict({
        "type": "road", "start": "Strasbourg",
        "coordinate": {"lat": 48.5734, "long": 7.7521},
        "waypoints": [
            {"location": "Orléans", "coordinate": {"lat": 47.9029, "long": 1.9093}},
            {"location": "Brest", "coordinate": {"lat": 48.3904, "long": -4.4861}},
        ],
    })]
    assert it.sun_reference(day.date, day).long == -4.4861  # the arrival
    assert it.wake_reference(day.date, day).long == 7.7521  # the departure


def test_a_morning_outside_the_days_clock_falls_back_to_the_evening():
    # Woke in New York, spends the day in Paris on Paris time: the morning
    # reference fails the clock guard, so the sunrise comes from Paris too —
    # the line still shows rather than vanishing.
    it = _moving_trip()
    it.accommodations[0].coordinate.lat = 40.758
    it.accommodations[0].coordinate.long = -73.9855
    day = it.days[1]
    assert it.wake_reference(day.date, day) is it.accommodations[0].coordinate
    brest = it.accommodations[1].coordinate
    got = it.sun_for(day)
    assert got is not None
    assert got.hhmm == sun_times(day.date, brest.lat, brest.long, 120).hhmm


def test_hidden_pins_still_locate_the_sun():
    # show_on_map only hides a pin — it doesn't move where you are.
    it = _trip()
    it.accommodations[0].coordinate.show_on_map = False
    assert it.sun_for(it.days[0]) is not None


def test_no_coordinate_anywhere_means_no_times():
    it = _trip()
    it.accommodations[0].coordinate = None
    assert it.sun_reference(it.days[0].date) is None
    assert it.sun_for(it.days[0]) is None


def test_opt_out():
    it = _trip(show_sun_times=False)
    assert it.show_sun_times is False
    assert it.sun_for(it.days[0]) is None
    assert all(d["sun"] is None for d in to_dict(it)["days"])


def test_day_timezone_prefers_an_explicit_activity_zone():
    it = Itinerary.from_dict({
        "travel_description": {"title": "Sun", "start_date": "2026-06-21"},
        "defaults": {"timezone": "+02:00"},
        "days": [{"title": "One", "activities": [
            {"type": "point_of_interest", "name": "Dawn watch", "start_tz": "+07:00"},
        ]}],
        "accommodations": [{
            "name": "Yurt", "arrival": "2026-06-21", "departure": "2026-06-22",
            "city": "Bishkek",
            "coordinate": {"lat": 42.8746, "long": 74.5698},
        }],
    })
    assert it.day_timezone(it.days[0]) == 420
    assert it.sun_for(it.days[0]).hhmm == sun_times(
        date(2026, 6, 21), 42.8746, 74.5698, 420).hhmm


def test_serialized_shape():
    it = Itinerary.from_dict({
        "travel_description": {"title": "Sun", "start_date": "2026-06-21"},
        "defaults": {"timezone": "+02:00"},
        "days": [{"title": "One"}],
        "accommodations": [{
            "name": "Hôtel", "arrival": "2026-06-21", "departure": "2026-06-22",
            "city": "Paris",
            "coordinate": {"lat": 48.8566, "long": 2.3522},
        }],
    })
    sun = to_dict(it)["days"][0]["sun"]
    assert sun["sunrise"] == "05:47"
    assert sun["sunset"] == "21:58"


def test_examples_carry_sun_times():
    # pyrenees.json is dated with a located stay every night → times throughout.
    it = Itinerary.from_json_file(str(EXAMPLES / "pyrenees.json"))
    assert it.show_sun_times is True
    for d in to_dict(it)["days"]:
        assert d["sun"] is not None and d["sun"].keys() == {"sunrise", "sunset"}


def test_undated_trip_has_no_sun_times():
    # kyrgyzstan.json carries no dates at all — nothing to compute from.
    it = Itinerary.from_json_file(str(EXAMPLES / "kyrgyzstan.json"))
    assert all(d["sun"] is None for d in to_dict(it)["days"])
