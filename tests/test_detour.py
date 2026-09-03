"""An activity's ``detour`` flag: a stop kept in the book but left off the day's
timeline — parsing, scheduling, serialization, validation and the two markers
the renderers draw."""

import json
from datetime import time
from pathlib import Path

import pytest

from odysseyra_travelbook import Itinerary, build_pdf, validate_text
from odysseyra_travelbook.models import to_dict
from odysseyra_travelbook.pdf import TravelPDF

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
FRANCE = EXAMPLES / "france.json"


def _t(hhmm):
    h, m = hhmm.split(":")
    return time(int(h), int(m))


def _doc(activities, **defaults):
    """A one-day trip made of ``activities``, with a fixed 15-minute buffer so
    "no buffer before a detour" is observable (the auto-sized default would
    stretch the gaps to the day's end instead)."""
    base = {"start_time": "09:00", "end_time": "18:00",
            "auto_sized_buffer": False, "buffer": "15 min"}
    base.update(defaults)
    return {
        "travel_description": {"title": "T", "start_date": "2026-06-01"},
        "defaults": base,
        "days": [{"title": "D1", "activities": activities}],
    }


def _poi(name, **extra):
    return {"type": "point_of_interest", "name": name, **extra}


def _timeline(activities, **defaults):
    """``(title, start, end, duration_min)`` per resolved item of the day."""
    day = Itinerary.from_dict(_doc(activities, **defaults)).days[0]
    return [(a.title, a.start_time, a.end_time, a.duration_min)
            for a in day.activities]


# -- the model -------------------------------------------------------------

def test_the_flag_defaults_to_false():
    day = Itinerary.from_dict(_doc([_poi("A", duration="1h")])).days[0]
    assert day.activities[0].detour is False


@pytest.mark.parametrize("given,expected", [
    (True, True), (False, False), ("yes", True), ("no", False), ("true", True),
])
def test_the_flag_is_parsed_like_every_other_bool(given, expected):
    day = Itinerary.from_dict(_doc([_poi("A", duration="1h", detour=given)])).days[0]
    assert day.activities[0].detour is expected


def test_a_detour_keeps_its_place_in_the_day_but_takes_no_time():
    # The detour sits where it was written — between A and the buffer that
    # separates A from B — and B still starts 15 minutes after A ends.
    assert _timeline([
        _poi("A", duration="1h"),
        _poi("Maybe", duration="2h", detour=True),
        _poi("B", duration="1h"),
    ]) == [
        ("A", _t("09:00"), _t("10:00"), 60),
        ("Maybe", None, None, 120),
        ("Buffer", _t("10:00"), _t("10:15"), 15),
        ("B", _t("10:15"), _t("11:15"), 60),
    ]


def test_no_buffer_is_inserted_before_a_detour():
    titles = [t for t, *_ in _timeline([
        _poi("A", duration="1h"),
        _poi("Maybe", duration="2h", detour=True),
        _poi("Also maybe", duration="1h", detour=True),
        _poi("B", duration="1h"),
    ])]
    # one buffer only — the one between the two *scheduled* stops
    assert titles == ["A", "Maybe", "Also maybe", "Buffer", "B"]


def test_a_detour_written_first_stays_first():
    titles = [t for t, *_ in _timeline([
        _poi("Maybe", duration="1h", detour=True),
        _poi("A", duration="1h"),
    ])]
    assert titles == ["Maybe", "A"]


def test_a_day_of_nothing_but_detours_schedules_nothing():
    assert _timeline([_poi("Maybe", duration="1h", detour=True)]) == [
        ("Maybe", None, None, 60),
    ]


def test_stated_times_are_folded_into_the_duration_and_dropped():
    # 10:00 → 11:30 says how long the stop takes; it can't say *when*, since a
    # detour isn't on the timeline. So the span survives as the duration.
    assert _timeline([_poi("Maybe", start_time="10:00", end_time="11:30",
                           detour=True)]) == [("Maybe", None, None, 90)]


def test_a_stated_duration_wins_over_the_stated_times():
    assert _timeline([_poi("Maybe", start_time="10:00", end_time="11:30",
                           duration="20 min", detour=True)]) == [
        ("Maybe", None, None, 20),
    ]


def test_auto_sized_buffers_ignore_a_detour():
    # The day still spreads to `end_time` over the scheduled stops only: the
    # detour's two hours must not be counted as room already taken.
    rows = _timeline([
        _poi("A", duration="1h"),
        _poi("Maybe", duration="2h", detour=True),
        _poi("B", duration="1h"),
    ], auto_sized_buffer=True, buffer=None)
    assert rows[-1][2] == _t("18:00")
    assert [t for t, *_ in rows] == ["A", "Maybe", "Buffer", "B"]


def test_a_nested_detour_loses_its_times_too():
    day = Itinerary.from_dict(_doc([
        {"type": "place", "name": "Town", "duration": "3h", "activities": [
            _poi("Planned", duration="30 min"),
            _poi("Maybe", start_time="15:00", end_time="16:00", detour=True),
        ]},
    ])).days[0]
    nested = day.activities[0].activities
    assert [(a.title, a.start_time, a.end_time, a.duration_min) for a in nested] == [
        ("Planned", None, None, 30),
        ("Maybe", None, None, 60),
    ]


def test_a_nested_detour_does_not_lengthen_its_container():
    # A place with no duration lasts its nested activities' total — what you
    # plan to do there, so the detour contributes nothing.
    day = Itinerary.from_dict(_doc([
        {"type": "place", "name": "Town", "activities": [
            _poi("Planned", duration="30 min"),
            _poi("Maybe", duration="2h", detour=True),
        ]},
    ])).days[0]
    assert day.activities[0].duration_min == 30


# -- serialization ---------------------------------------------------------

def test_the_flag_reaches_the_viewer():
    doc = to_dict(Itinerary.from_dict(_doc([
        _poi("A", duration="1h"),
        _poi("Maybe", duration="1h", detour=True),
    ])))
    acts = doc["days"][0]["activities"]
    assert [(a["title"], a["detour"], a["start_time"]) for a in acts] == [
        ("A", False, "09:00"),
        ("Maybe", True, None),
    ]


def test_a_detour_is_left_out_of_the_calendar_export():
    # A calendar entry is a time, and a detour has none — so it can't be one.
    from odysseyra_travelbook.ics import build_ics

    ics = build_ics(Itinerary.from_dict(_doc([
        _poi("A", duration="1h"),
        _poi("Maybe", duration="1h", detour=True),
    ])))
    assert "SUMMARY" in ics and "A" in ics
    assert "Maybe" not in ics


# -- the validator ---------------------------------------------------------

def _messages(doc, level):
    return [f.message for f in validate_text(json.dumps(doc)) if f.level == level]


def test_a_non_boolean_flag_is_an_error():
    doc = _doc([_poi("A", duration="1h", detour="perhaps")])
    assert any("'detour'" in m and "true or false" in m
               for m in _messages(doc, "error"))


def test_the_missing_flag_states_its_default():
    doc = _doc([_poi("A", duration="1h")])
    assert any("'detour' is missing" in m and "false" in m
               for m in _messages(doc, "info"))


def test_a_dropped_clock_time_is_reported():
    doc = _doc([_poi("A", duration="1h", detour=True, start_time="10:00")])
    warnings = _messages(doc, "warning")
    assert any("'start_time' is ignored" in m and "detour" in m for m in warnings)


def test_a_dropped_pair_of_times_says_the_span_is_kept():
    doc = _doc([_poi("A", detour=True, start_time="10:00", end_time="11:00")])
    assert any("only the span between them is kept" in m
               for m in _messages(doc, "warning"))


def test_a_detour_with_a_duration_and_times_reports_each_ignored_key():
    doc = _doc([_poi("A", detour=True, duration="1h", start_time="10:00",
                     end_time="11:00")])
    warnings = [m for m in _messages(doc, "warning") if "is ignored" in m]
    assert len(warnings) == 2


def test_nothing_is_reported_for_a_detour_with_no_times():
    doc = _doc([_poi("A", duration="1h", detour=True)])
    assert not [m for m in _messages(doc, "warning") if "detour" in m]


def test_a_nested_detour_does_not_count_against_its_container():
    # 30 min planned + a 2h detour inside a 1h place: nothing overruns, because
    # the detour isn't competing for the place's hour.
    doc = _doc([{"type": "place", "name": "Town", "duration": "1h",
                 "activities": [_poi("Planned", duration="30 min"),
                                _poi("Maybe", duration="2h", detour=True)]}])
    assert not [m for m in _messages(doc, "warning") if "can't all fit" in m]


# -- the PDF ---------------------------------------------------------------

def _detour_tags(itinerary, lang="en"):
    """The OPTIONAL DETOUR pills the day pages draw, in page order."""
    pdf = TravelPDF(itinerary, lang, False, "google")
    drawn = []
    real = pdf._detour_tag
    pdf._detour_tag = lambda x, y, size=6.5: (drawn.append(pdf.t("OPTIONAL DETOUR"))
                                              or real(x, y, size))
    for i, day in enumerate(itinerary.days, 1):
        pdf.day(i, day)
    return drawn


def test_the_pill_marks_every_detour_row_and_nothing_else():
    it = Itinerary.from_dict(_doc([
        _poi("A", duration="1h"),
        _poi("Maybe", duration="1h", detour=True),
        {"type": "place", "name": "Town", "duration": "2h", "activities": [
            _poi("Nested maybe", duration="1h", detour=True),
        ]},
    ]))
    assert _detour_tags(it) == ["OPTIONAL DETOUR", "OPTIONAL DETOUR"]


def test_no_pill_when_no_activity_is_a_detour():
    assert _detour_tags(Itinerary.from_json_file(str(FRANCE.parent / "pyrenees.json"))) == []


def test_the_pill_is_localized():
    it = Itinerary.from_dict(_doc([_poi("Maybe", duration="1h", detour=True)]))
    assert _detour_tags(it, lang="fr") == ["DÉTOUR OPTIONNEL"]


def test_a_detour_is_never_a_day_highlight():
    # The cover advertises the day; a stop you probably won't make isn't part of
    # what it promises.
    it = Itinerary.from_dict(_doc([
        _poi("Planned sight", duration="1h"),
        _poi("Maybe sight", duration="1h", detour=True),
    ]))
    pdf = TravelPDF(it, "en", False, "google")
    assert pdf._day_highlights(it.days[0]) == "Planned sight"


def test_the_row_keeps_its_map_pin():
    # A detour is still a place you may end up at, so it stays on the map — it
    # is drawn dimmer, not hidden.
    it = Itinerary.from_json_file(str(FRANCE))
    detours = [a for d in it.days for a in d.activities if a.detour]
    assert detours, "france.json carries a detour"
    assert all(a.coordinate is not None for a in detours)


@pytest.mark.parametrize("ink_saver", [False, True])
def test_a_book_with_detours_still_builds(tmp_path, ink_saver):
    it = Itinerary.from_dict(_doc([
        _poi("A", duration="1h"),
        _poi("Maybe", duration="1h", detour=True),
        {"type": "meal", "restaurant": "Optional", "meal_type": "snack",
         "duration": "30 min", "detour": True},
        {"type": "hike", "name": "Optional walk", "distance_km": 4,
         "elevation_m": 120, "duration": "2h", "detour": True},
        {"type": "road", "duration": "1h", "distance_km": 40, "detour": True,
         "legs": [{"start_location": "A", "end_location": "B",
                   "end_coordinate": {"lat": 1, "long": 2}}]},
    ]))
    out = build_pdf(it, tmp_path / "detours.pdf", ink_saver=ink_saver)
    assert out.read_bytes().startswith(b"%PDF")
    assert out.stat().st_size > 1000

