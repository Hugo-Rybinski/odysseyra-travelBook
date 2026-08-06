from pathlib import Path

import pytest

from travelbook import (
    Accommodation,
    CarRental,
    Hike,
    Itinerary,
    ItineraryError,
    Meal,
    PointOfInterest,
    Road,
    Place,
    Transport,
    build_pdf,
)

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "pyrenees.json"


def test_grouped_default_and_travel_description():
    it = Itinerary.from_dict(
        {
            "travel_description": {
                "title": "Grouped Trip",
                "cover_color": "#123456",
            },
            "default": {
                "start_time": "10:00",
                "buffer": "20 min",
                "timezone": "+01:00",
            },
            "days": [{"title": "d", "activities": [
                {"type": "point_of_interest", "name": "M", "duration": "1h"}]}],
        }
    )
    assert it.title == "Grouped Trip"
    assert it.cover_color == "#123456"
    assert it.default_timezone == 60
    assert it.default_buffer_min == 20
    assert it.days[0].activities[0].start_time.strftime("%H:%M") == "10:00"


def test_flat_layout_still_supported():
    # legacy top-level keys keep working
    it = Itinerary.from_dict(
        {
            "title": "Flat Trip",
            "default_start_time": "08:00",
            "timezone": "+02:00",
            "days": [{"title": "d", "activities": []}],
        }
    )
    assert it.title == "Flat Trip"
    assert it.default_timezone == 120


def test_loads_example():
    it = Itinerary.from_json_file(EXAMPLE)
    assert it.title == "Pyrenees Road Trip"
    assert len(it.days) == 4
    assert it.date_range
    # first activity of day 1 is a road
    assert isinstance(it.days[0].activities[0], Road)
    # accommodation is a top-level section now, not on the days
    assert len(it.accommodations) == 2
    assert not hasattr(it.days[0], "accommodation")


def test_accommodation_fields_and_nights():
    it = Itinerary.from_json_file(EXAMPLE)
    hotel = it.accommodations[0]
    assert isinstance(hotel, Accommodation)
    assert hotel.name == "Hôtel Gallia & Londres"
    assert hotel.nights == 2
    assert hotel.date_range == "Jun 08 → Jun 10"
    assert hotel.booking_source == "Booking.com"
    assert hotel.city == "Lourdes"
    assert hotel.paid_online is True
    assert hotel.breakfast_included is True
    assert it.accommodations[1].paid_online is False
    assert it.accommodations[1].city == "Gavarnie"


def test_stay_lookup_and_night_index():
    it = Itinerary.from_json_file(EXAMPLE)
    hotel, refuge = it.accommodations
    # 2-night Lourdes hotel covers day 1 and day 2
    assert it.stay_for(it.days[0].date) is hotel
    assert hotel.night_of(it.days[0].date) == 1
    assert it.stay_for(it.days[1].date) is hotel
    assert hotel.night_of(it.days[1].date) == 2
    # day 3 is the refuge (1 night)
    assert it.stay_for(it.days[2].date) is refuge
    assert refuge.night_of(it.days[2].date) == 1
    # day 4 is the checkout / departure day — no stay
    assert it.stay_for(it.days[3].date) is None


def test_covers_excludes_departure_day():
    acc = Accommodation.from_dict(
        {"name": "H", "city": "X", "arrival": "2026-06-08",
         "departure": "2026-06-10"}
    )
    from datetime import date

    assert acc.covers(date(2026, 6, 8)) is True
    assert acc.covers(date(2026, 6, 9)) is True
    assert acc.covers(date(2026, 6, 10)) is False  # checkout morning
    assert acc.night_of(date(2026, 6, 7)) is None


def test_accommodation_requires_name():
    with pytest.raises(ItineraryError):
        Accommodation.from_dict({"arrival": "2026-06-08"})


def test_accommodations_optional():
    it = Itinerary.from_dict(
        {"title": "t", "days": [{"title": "d", "activities": []}]}
    )
    assert it.accommodations == []


def test_activity_types_parse():
    it = Itinerary.from_dict(
        {
            "title": "t",
            "days": [
                {
                    "title": "d",
                    "activities": [
                        {"type": "road", "start": "A", "end": "B", "distance_km": 10, "off_road": True},
                        {"type": "point_of_interest", "name": "M", "category": "museum"},
                        {"type": "place", "name": "T", "activities": [
                            {"type": "point_of_interest", "name": "x", "category": "castle"},
                            {"type": "hike", "name": "y", "route": "loop"}]},
                        {"type": "hike", "name": "H", "elevation_m": 300, "route": "loop"},
                    ],
                }
            ],
        }
    )
    acts = it.days[0].activities
    assert isinstance(acts[0], Road) and acts[0].off_road is True
    assert acts[0].distance_km == 10.0
    assert isinstance(acts[1], PointOfInterest) and acts[1].category == "museum"
    assert isinstance(acts[2], Place)
    assert [m.name for m in acts[2].activities] == ["x", "y"]
    assert isinstance(acts[2].activities[0], PointOfInterest)
    assert acts[2].activities[0].category == "castle"
    assert isinstance(acts[2].activities[1], Hike)
    assert isinstance(acts[3], Hike) and acts[3].route == "loop"


def test_road_title():
    r = Road(start="Pau", end="Lourdes")
    assert r.title == "Pau → Lourdes"


def test_hike_route_normalization():
    it = Itinerary.from_dict(
        {"title": "t", "days": [{"title": "d", "activities": [
            {"type": "hike", "name": "H", "route": "back-and-forth"}]}]}
    )
    hike = it.days[0].activities[0]
    assert hike.route == "back_and_forth"
    assert hike.route_label == "Back and forth"


def test_unknown_activity_type_rejected():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict(
            {"title": "t", "days": [{"title": "d", "activities": [{"type": "flight"}]}]}
        )


def test_missing_type_rejected():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict(
            {"title": "t", "days": [{"title": "d", "activities": [{"name": "x"}]}]}
        )


def test_monument_requires_name():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict(
            {"title": "t", "days": [{"title": "d", "activities": [{"type": "point_of_interest"}]}]}
        )


def test_bad_route_rejected():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict(
            {"title": "t", "days": [{"title": "d", "activities": [
                {"type": "hike", "name": "H", "route": "zigzag"}]}]}
        )


def test_road_requires_start_and_end():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
            {"type": "road", "start": "A"}]}]})


def test_poi_category_default_and_enum():
    it = Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
        {"type": "point_of_interest", "name": "M"}]}]})
    assert it.days[0].activities[0].category == "other"
    with pytest.raises(ItineraryError):
        Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
            {"type": "point_of_interest", "name": "M", "category": "alien"}]}]})


def test_hike_route_one_way():
    it = Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
        {"type": "hike", "name": "H", "route": "one-way"}]}]})
    hike = it.days[0].activities[0]
    assert hike.route == "one_way"
    assert hike.route_label == "One way"


def test_hike_requires_name_and_route_default():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
            {"type": "hike"}]}]})
    it = Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
        {"type": "hike", "name": "H"}]}]})
    assert it.days[0].activities[0].route == "back_and_forth"


def test_nested_activities_require_a_valid_type():
    with pytest.raises(ItineraryError):  # a bare name string is no longer allowed
        Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
            {"type": "place", "name": "P", "activities": ["x"]}]}]})
    with pytest.raises(ItineraryError):  # a road may not be nested in a place
        Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
            {"type": "place", "name": "P", "activities": [
                {"type": "road", "start": "A", "end": "B"}]}]}]})
    with pytest.raises(ItineraryError):  # a road accepts only nested meals
        Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
            {"type": "road", "start": "A", "end": "B", "activities": [
                {"type": "point_of_interest", "name": "X"}]}]}]})


def test_point_of_interest_nests_a_hike():
    it = Itinerary.from_dict({"title": "t", "days": [{"title": "d", "activities": [
        {"type": "point_of_interest", "name": "Park", "activities": [
            {"type": "hike", "name": "Trail", "route": "loop"}]}]}]})
    poi = it.days[0].activities[0]
    assert isinstance(poi, PointOfInterest)
    assert isinstance(poi.activities[0], Hike)
    assert poi.activities[0].name == "Trail"


def test_meal_nests_under_road_hike_place_and_poi():
    meal = {"type": "meal", "meal_type": "picnic", "area": "somewhere"}
    for container in (
        {"type": "road", "start": "A", "end": "B", "activities": [meal]},
        {"type": "hike", "name": "H", "activities": [meal]},
        {"type": "place", "name": "P", "activities": [meal]},
        {"type": "point_of_interest", "name": "PoI", "activities": [meal]},
    ):
        it = Itinerary.from_dict(
            {"title": "t", "days": [{"title": "d", "activities": [container]}]})
        nested = it.days[0].activities[0].activities
        assert isinstance(nested[0], Meal)
        assert nested[0].type == "picnic"


def test_missing_title_rejected():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict({"days": [{"title": "x"}]})


def test_empty_days_rejected():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict({"title": "t", "days": []})


def _one_day(activities, **trip):
    return Itinerary.from_dict(
        {"title": "t", "days": [{"title": "d", "activities": activities}], **trip}
    ).days[0].activities


def test_first_activity_uses_default_start_time():
    acts = _one_day(
        [{"type": "point_of_interest", "name": "M", "duration": "1h"}],
        default_start_time="10:00",
    )
    assert acts[0].start_time.strftime("%H:%M") == "10:00"
    assert acts[0].end_time.strftime("%H:%M") == "11:00"


def test_default_start_time_defaults_to_8am():
    acts = _one_day([{"type": "point_of_interest", "name": "M", "duration": "30 min"}])
    assert acts[0].start_time.strftime("%H:%M") == "08:00"
    assert acts[0].end_time.strftime("%H:%M") == "08:30"


def test_default_timezone_is_gmt():
    it = Itinerary.from_dict(
        {"title": "t", "days": [{"title": "d", "activities": []}]}
    )
    assert it.default_timezone == 0


def test_dates_inferred_from_earliest_and_latest():
    it = Itinerary.from_dict(
        {
            "title": "t",
            "days": [
                {"title": "a", "date": "2026-06-10", "activities": []},
                {"title": "b", "activities": []},  # date inferred → 2026-06-11
            ],
            "transport": [
                {"type": "plane", "start": "A", "end": "B",
                 "start_date": "2026-06-08",
                 "start_time": "20:00", "end_time": "23:00"}
            ],
            "accommodations": [
                {"name": "H", "city": "X", "arrival": "2026-06-10",
                 "departure": "2026-06-13"}
            ],
        }
    )
    from datetime import date

    assert it.days[1].date == date(2026, 6, 11)  # inferred: day 0 (06-10) + index 1
    assert it.start_date == date(2026, 6, 8)  # earliest (the plane)
    assert it.end_date == date(2026, 6, 13)  # latest (accommodation departure)


def test_day_date_inferred_from_trip_start_and_index():
    it = Itinerary.from_dict(
        {
            "title": "t",
            "default": {},
            "days": [
                {"title": "d1", "date": "2026-07-01", "activities": []},
                {"title": "d2", "activities": []},
                {"title": "d3", "activities": []},
            ],
        }
    )
    from datetime import date

    assert [d.date for d in it.days] == [
        date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)]


def test_manual_start_end_dates_override_inference():
    it = Itinerary.from_dict(
        {
            "travel_description": {"title": "t", "start_date": "2026-06-01",
                                   "end_date": "2026-06-30"},
            "days": [{"title": "a", "date": "2026-06-10", "activities": []}],
        }
    )
    from datetime import date

    # manual dates win over the inferred earliest/latest (2026-06-10)
    assert it.start_date == date(2026, 6, 1)
    assert it.end_date == date(2026, 6, 30)


def test_day_requires_title():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict({"title": "t", "days": [{"city": "Paris",
                                                     "activities": []}]})


def test_subsequent_activity_starts_at_previous_end():
    acts = _one_day(
        [
            {"type": "point_of_interest", "name": "A", "duration": "1h"},
            {"type": "point_of_interest", "name": "B", "duration": "30 min"},
        ],
        default_start_time="09:00",
    )
    assert acts[1].start_time.strftime("%H:%M") == "10:00"
    assert acts[1].end_time.strftime("%H:%M") == "10:30"


def test_duration_inferred_from_end_time():
    acts = _one_day(
        [{"type": "point_of_interest", "name": "M", "end_time": "11:30"}],
        default_start_time="09:00",
    )
    assert acts[0].duration_min == 150
    assert acts[0].duration_display == "2h30"


def test_explicit_start_time_overrides_chain():
    acts = _one_day(
        [
            {"type": "point_of_interest", "name": "A", "duration": "1h"},
            {"type": "point_of_interest", "name": "B", "start_time": "15:00", "duration": "1h"},
        ]
    )
    # A ends 10:00; B is pinned to 15:00, so a gap buffer fills the interval.
    assert [a.kind for a in acts] == ["point_of_interest", "buffer", "point_of_interest"]
    assert acts[2].start_time.strftime("%H:%M") == "15:00"


def test_duration_parsing_formats():
    from travelbook.models import _format_duration, _parse_duration

    assert _parse_duration("1h30") == 90
    assert _parse_duration("2h") == 120
    assert _parse_duration("50 min") == 50
    assert _parse_duration("1:30") == 90
    assert _parse_duration("90m") == 90
    assert _format_duration(270) == "4h30"
    assert _format_duration(45) == "45 min"
    assert _format_duration(120) == "2h"


def test_default_buffer_inserted_between_activities():
    acts = _one_day(
        [
            {"type": "point_of_interest", "name": "A", "duration": "1h"},
            {"type": "point_of_interest", "name": "B", "duration": "1h"},
        ],
        default_start_time="09:00",
        default_buffer="15 min",
    )
    assert [a.kind for a in acts] == ["point_of_interest", "buffer", "point_of_interest"]
    assert acts[1].duration_min == 15
    assert acts[1].auto is True
    assert acts[2].start_time.strftime("%H:%M") == "10:15"


def test_manual_buffer_honored_and_suppresses_default():
    acts = _one_day(
        [
            {"type": "point_of_interest", "name": "A", "duration": "1h"},
            {"type": "buffer", "duration": "40 min"},
            {"type": "point_of_interest", "name": "B", "duration": "1h"},
        ],
        default_start_time="09:00",
        default_buffer="15 min",
    )
    kinds = [a.kind for a in acts]
    assert kinds == ["point_of_interest", "buffer", "point_of_interest"]  # no extra default buffer
    assert acts[1].duration_min == 40 and acts[1].auto is False
    assert acts[2].start_time.strftime("%H:%M") == "10:40"


def test_gap_from_explicit_start_becomes_buffer():
    acts = _one_day(
        [
            {"type": "point_of_interest", "name": "A", "duration": "1h"},
            {"type": "point_of_interest", "name": "B", "start_time": "11:00", "duration": "1h"},
        ],
        default_start_time="09:00",
    )
    assert [a.kind for a in acts] == ["point_of_interest", "buffer", "point_of_interest"]
    buf = acts[1]
    assert buf.start_time.strftime("%H:%M") == "10:00"
    assert buf.end_time.strftime("%H:%M") == "11:00"
    assert buf.duration_min == 60


def test_default_and_gap_buffers_merge():
    acts = _one_day(
        [
            {"type": "point_of_interest", "name": "A", "duration": "1h"},
            {"type": "point_of_interest", "name": "B", "start_time": "11:00", "duration": "1h"},
        ],
        default_start_time="09:00",
        default_buffer="15 min",
    )
    # 15-min default + 45-min gap merge into a single 60-min buffer.
    assert [a.kind for a in acts] == ["point_of_interest", "buffer", "point_of_interest"]
    assert acts[1].duration_min == 60


def test_no_leading_buffer_before_first_activity():
    acts = _one_day(
        [{"type": "point_of_interest", "name": "A", "start_time": "10:00", "duration": "1h"}],
        default_start_time="09:00",
    )
    assert [a.kind for a in acts] == ["point_of_interest"]  # no buffer before the first
    assert acts[0].start_time.strftime("%H:%M") == "10:00"


def test_zero_manual_buffer_suppresses_default_and_hides_line():
    acts = _one_day(
        [
            {"type": "point_of_interest", "name": "A", "duration": "1h"},
            {"type": "buffer", "duration": "0 min"},
            {"type": "point_of_interest", "name": "B", "duration": "1h"},
        ],
        default_start_time="09:00",
        default_buffer="15 min",
    )
    # no visible buffer line, and the default buffer is not applied either
    assert [a.kind for a in acts] == ["point_of_interest", "point_of_interest"]
    assert acts[1].start_time.strftime("%H:%M") == "10:00"


def test_buffer_requires_duration():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict(
            {"title": "t", "days": [{"title": "d", "activities": [{"type": "buffer"}]}]}
        )


def test_transport_example_section():
    it = Itinerary.from_json_file(EXAMPLE)
    assert len(it.transports) == 3
    plane, train, night = it.transports
    assert isinstance(plane, Transport)
    assert plane.type == "plane"
    assert plane.title == "New York JFK → Paris CDG"
    assert plane.status == "confirmed"
    assert plane.paid is True
    assert train.paid is False and train.status == "booked"
    assert night.type == "train" and night.overnight is True


def test_transport_slots_into_day_and_night_lookup():
    from datetime import date

    it = Itinerary.from_json_file(EXAMPLE)
    # the day-2 train departs Jun 08 and is a same-day leg
    assert len(it.transports_on(date(2026, 6, 8))) == 1
    assert it.night_transport(date(2026, 6, 8)) is None
    # the night train departs Jun 11 → overnight, used as that night's stay
    night = it.night_transport(date(2026, 6, 11))
    assert night is not None and night.end == "Paris Austerlitz"
    assert night.start_date == date(2026, 6, 11)
    assert night.end_date == date(2026, 6, 12)
    assert night.end_day_offset == 1


def test_transport_date_alias_accepted():
    # legacy "date" key still maps to start_date
    it = Itinerary.from_dict(
        {
            "title": "t",
            "days": [{"title": "d", "activities": []}],
            "transport": [{"type": "bus", "start": "A", "end": "B",
                           "date": "2026-06-08", "start_time": "09:00",
                           "duration": "1h"}],
        }
    )
    from datetime import date

    assert it.transports[0].start_date == date(2026, 6, 8)


def test_transport_end_date_same_day_when_not_overnight():
    it = Itinerary.from_dict(
        {
            "title": "t",
            "days": [{"title": "d", "activities": []}],
            "transport": [
                {"type": "bus", "start": "A", "end": "B", "date": "2026-06-08",
                 "start_time": "09:00", "duration": "2h"}
            ],
        }
    )
    t = it.transports[0]
    assert t.end_date == t.start_date and t.overnight is False
    assert t.end_day_offset == 0


def test_transport_overnight_crosses_midnight():
    from datetime import date

    it = Itinerary.from_dict(
        {
            "title": "t",
            "days": [{"title": "d", "activities": []}],
            "transport": [
                {"type": "train", "start": "A", "end": "B", "date": "2026-06-11",
                 "start_time": "22:10", "end_time": "06:45"}
            ],
        }
    )
    t = it.transports[0]
    assert t.end_date == date(2026, 6, 12) and t.overnight is True


def test_transport_duration_inferred_across_timezones():
    # 22:30 (UTC-4) → 11:45 (UTC+2) = 7h15 of actual flight time
    it = Itinerary.from_dict(
        {
            "title": "t",
            "days": [{"title": "d", "activities": []}],
            "transport": [
                {
                    "type": "plane",
                    "start": "A", "end": "B", "start_date": "2026-06-08",
                    "start_time": "22:30",
                    "start_tz": "-04:00",
                    "end_time": "11:45",
                    "end_tz": "+02:00",
                }
            ],
        }
    )
    assert it.transports[0].duration_min == 7 * 60 + 15


def test_transport_end_inferred_uses_default_timezone():
    it = Itinerary.from_dict(
        {
            "title": "t",
            "timezone": "+02:00",
            "days": [{"title": "d", "activities": []}],
            "transport": [
                {"type": "train", "start": "A", "end": "B",
                 "start_date": "2026-06-08", "start_time": "13:50",
                 "duration": "4h20"}
            ],
        }
    )
    tr = it.transports[0]
    assert tr.end_time.strftime("%H:%M") == "18:10"
    assert tr.start_tz == 120 and tr.end_tz == 120  # inherited global tz


def test_transport_requires_core_fields_and_type_enum():
    base = {"start": "A", "end": "B", "start_date": "2026-06-08",
            "start_time": "09:00", "type": "train"}
    for drop in ("start", "end", "start_date", "start_time"):
        d = {k: v for k, v in base.items() if k != drop}
        with pytest.raises(ItineraryError):
            Itinerary.from_dict({"title": "t", "days": [{"title": "d",
                "activities": []}], "transport": [d]})
    with pytest.raises(ItineraryError):
        Itinerary.from_dict({"title": "t", "days": [{"title": "d",
            "activities": []}], "transport": [{**base, "type": "rocket"}]})
    # type defaults to "other"
    it = Itinerary.from_dict({"title": "t", "days": [{"title": "d",
        "activities": []}], "transport": [{k: v for k, v in base.items()
                                            if k != "type"}]})
    assert it.transports[0].type == "other"


def test_accommodation_requires_fields_and_type_enum():
    base = {"name": "H", "city": "X", "arrival": "2026-06-08",
            "departure": "2026-06-09"}
    for drop in ("name", "city", "arrival", "departure"):
        with pytest.raises(ItineraryError):
            Accommodation.from_dict({k: v for k, v in base.items() if k != drop})
    with pytest.raises(ItineraryError):
        Accommodation.from_dict({**base, "type": "yurt"})
    assert Accommodation.from_dict(base).type == "hotel"  # default


def test_car_rental_example_section():
    it = Itinerary.from_json_file(EXAMPLE)
    assert len(it.car_rentals) == 1
    cr = it.car_rentals[0]
    assert isinstance(cr, CarRental)
    assert cr.company == "Europcar"
    assert cr.car_type == "suv" and cr.car_type_label == "SUV"
    assert cr.paid is True
    assert cr.additional_drivers == 1
    assert cr.pickup_duration_display == "30 min"
    # all four offsets inherit the trip's +02:00 default
    assert cr.pickup_tz == 120 and cr.dropoff_tz == 120


def test_car_rental_requires_core_fields():
    base = {
        "booking_start_date": "2026-06-08", "booking_start_time": "09:00",
        "booking_end_date": "2026-06-11", "booking_end_time": "20:00",
        "pickup_date": "2026-06-08", "pickup_time": "10:00",
        "dropoff_date": "2026-06-11", "dropoff_time": "18:00",
        "pickup_location": "Pau Airport",
    }
    for drop in base:
        with pytest.raises(ItineraryError):
            CarRental.from_dict({k: v for k, v in base.items() if k != drop})
    assert CarRental.from_dict(base).car_type == "regular"  # default


def test_car_rental_type_enum_and_dropoff_defaults_to_pickup():
    base = {
        "booking_start_date": "2026-06-08", "booking_start_time": "09:00",
        "booking_end_date": "2026-06-11", "booking_end_time": "20:00",
        "pickup_date": "2026-06-08", "pickup_time": "10:00",
        "dropoff_date": "2026-06-11", "dropoff_time": "18:00",
        "pickup_location": "Pau Airport",
    }
    with pytest.raises(ItineraryError):
        CarRental.from_dict({**base, "car_type": "spaceship"})
    with pytest.raises(ItineraryError):
        CarRental.from_dict({**base, "additional_drivers": "many"})
    cr = CarRental.from_dict({**base, "car_type": "4x4"})
    assert cr.car_type == "4x4" and cr.car_type_label == "4x4"
    # drop-off location defaults to the pick-up location; drivers default to 0
    assert cr.dropoff_location == "Pau Airport"
    assert cr.additional_drivers == 0


def test_activity_accepts_timezone():
    it = Itinerary.from_dict(
        {
            "title": "t",
            "timezone": "+02:00",
            "days": [
                {
                    "title": "d",
                    "activities": [
                        {
                            "type": "point_of_interest",
                            "name": "M",
                            "start_time": "09:00",
                            "start_tz": "-04:00",
                            "duration": "1h",
                        }
                    ],
                }
            ],
        }
    )
    act = it.days[0].activities[0]
    assert act.start_tz == -240
    assert it.default_timezone == 120


def test_transport_bad_status_rejected():
    with pytest.raises(ItineraryError):
        Itinerary.from_dict(
            {"title": "t", "days": [{"title": "d", "activities": []}],
             "transport": [{"type": "train", "start": "A", "end": "B",
                            "start_date": "2026-06-08", "start_time": "09:00",
                            "status": "maybe"}]}
        )


def test_timezone_parsing_variants():
    from travelbook.models import _parse_tz

    assert _parse_tz("+02:00") == 120
    assert _parse_tz("UTC-3") == -180
    assert _parse_tz("Z") == 0
    assert _parse_tz("+0530") == 330
    assert _parse_tz(None) is None


def test_build_pdf(tmp_path):
    it = Itinerary.from_json_file(EXAMPLE)
    out = build_pdf(it, tmp_path / "trip.pdf")
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF")
    assert out.stat().st_size > 1000


def test_build_pdf_ink_saver(tmp_path):
    it = Itinerary.from_json_file(EXAMPLE)
    out = build_pdf(it, tmp_path / "trip_ink.pdf", ink_saver=True)
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF")
    assert out.stat().st_size > 1000
