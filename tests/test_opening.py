"""A point of interest's ``opening_days`` / ``opening_hours``: parsing, the
folded/localized display both renderers draw, and the validator warning when a
visit lands on a closed day or outside the hours."""

from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

import pytest

from odysseyra_travelbook import Itinerary, ItineraryError, build_ics, build_pdf
from odysseyra_travelbook import validate_text
from odysseyra_travelbook.lang import fmt_weekday_runs, weekday_name
from odysseyra_travelbook.lang.dates import _WEEKDAY_FULL
from odysseyra_travelbook.models import to_dict
from odysseyra_travelbook.models.opening import (
    WEEKDAYS,
    Opening,
    OpeningRule,
    _parse_opening_days,
    _parse_opening_hours,
    parse_opening,
)
from odysseyra_travelbook.pdf import TravelPDF

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE = EXAMPLES / "pyrenees.json"


def _raw(**poi):
    """pyrenees.json with ``poi`` merged into day 4's cathedral — a top-level
    point of interest whose resolved visit is Thursday 11:20 → 12:20."""
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    raw["days"][3]["activities"][1].update(poi)
    return raw


def _findings(raw, lang="en"):
    return validate_text(json.dumps(raw, ensure_ascii=False), lang)


def _messages(raw, level="warning", lang="en"):
    return [f.message for f in _findings(raw, lang) if f.level == level]


# -- the canonical weekday keys -------------------------------------------

def test_the_weekday_keys_are_the_lowercased_english_names():
    """``lang/dates.py`` derives its index table from its own English weekday
    names, so the two lists have to name the same days in the same order."""
    assert WEEKDAYS == tuple(n.lower() for n in _WEEKDAY_FULL["en"])


# -- parsing the days -----------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("monday", ("monday",)),
    ("mon", ("monday",)),
    ("Mon.", ("monday",)),
    ("thurs", ("thursday",)),
    ("tue-sun", ("tuesday", "wednesday", "thursday", "friday", "saturday",
                 "sunday")),
    ("monday-friday, sunday", ("monday", "tuesday", "wednesday", "thursday",
                               "friday", "sunday")),
    ("tue–sun", ("tuesday", "wednesday", "thursday", "friday", "saturday",
                 "sunday")),  # an en dash, as pasted from a book
    ("sun, mon", ("monday", "sunday")),  # any order in, week order out
    ("mon, monday, mon", ("monday",)),  # duplicates collapse
])
def test_opening_days_parse(value, expected):
    assert _parse_opening_days(value) == expected


def test_a_day_range_may_wrap_the_week():
    assert _parse_opening_days("sat-mon") == ("monday", "saturday", "sunday")


def test_no_days_means_every_day():
    assert _parse_opening_days(None) == ()
    assert _parse_opening_days("") == ()
    assert _parse_opening_days("   ") == ()


@pytest.mark.parametrize("value", ["funday", "mon-", "mo", "mon-tue-wed", "12"])
def test_bad_opening_days_are_rejected(value):
    with pytest.raises(ItineraryError, match="Invalid opening_days"):
        _parse_opening_days(value)


# -- parsing the hours ----------------------------------------------------

def test_opening_hours_parse_one_range():
    # A plain value is one default rule (no weekdays), which is what keeps every
    # file written before per-day hours parsing identically.
    assert _parse_opening_hours("09:30-18:00") == (
        OpeningRule(hours=((time(9, 30), time(18, 0)),)),)


def test_opening_hours_keep_a_midday_closure_as_two_ranges():
    assert _parse_opening_hours("09:30-12:30, 14:00-18:00") == (
        OpeningRule(hours=((time(9, 30), time(12, 30)),
                           (time(14, 0), time(18, 0)))),)


def test_no_hours_means_all_day():
    assert _parse_opening_hours(None) == ()
    assert _parse_opening_hours("") == ()


@pytest.mark.parametrize("value", ["09:30", "09:30-", "25:00-18:00",
                                   "09:00-10:00-11:00", "morning"])
def test_bad_opening_hours_are_rejected(value):
    with pytest.raises(ItineraryError, match="Invalid opening_hours"):
        _parse_opening_hours(value)


def test_a_range_that_opens_and_closes_at_once_is_rejected():
    with pytest.raises(ItineraryError, match="same time"):
        _parse_opening_hours("10:00-10:00")


# -- the Opening object ---------------------------------------------------

def test_neither_field_builds_no_opening():
    assert parse_opening({}) is None
    assert parse_opening({"opening_days": "", "opening_hours": ""}) is None


def test_either_field_alone_builds_one():
    assert parse_opening({"opening_days": "mon"}) == Opening(days=("monday",))
    assert parse_opening({"opening_hours": "09:00-17:00"}) == Opening(
        rules=(OpeningRule(hours=((time(9), time(17)),)),))


@pytest.mark.parametrize("days,runs", [
    ("mon-fri", (("monday", "friday"),)),
    ("mon-wed, fri", (("monday", "wednesday"), ("friday", "friday"))),
    ("wednesday", (("wednesday", "wednesday"),)),
    # A run wraps the week rather than being split at the Monday boundary: a
    # place closed on Tuesdays reads "Wed–Mon", the way opening days are printed.
    ("wed-mon", (("wednesday", "monday"),)),
    ("sat-mon", (("saturday", "monday"),)),
    ("mon-sun", (("monday", "sunday"),)),  # open every day
])
def test_day_runs_fold_consecutive_days(days, runs):
    assert Opening(days=_parse_opening_days(days)).day_runs == runs


def test_hours_display_is_digits_only():
    """Language-neutral, so it is computed once in the model and both renderers
    print the one string."""
    opening = parse_opening({"opening_hours": "09:30-12:30, 14:00-18:00"})
    assert opening.hours_display == "09:30–12:30, 14:00–18:00"


def test_day_runs_localize():
    runs = parse_opening({"opening_days": "tue-sun"}).day_runs
    assert fmt_weekday_runs(runs, "en") == "Tue–Sun"
    assert fmt_weekday_runs(runs, "fr") == "mar.–dim."
    assert fmt_weekday_runs(runs, "fr", abbr=False) == "mardi–dimanche"


def test_closed_on() -> None:
    opening = parse_opening({"opening_days": "tue-sun"})
    assert opening.closed_on(date(2026, 9, 7))  # a Monday
    assert not opening.closed_on(date(2026, 9, 8))
    assert not opening.closed_on(None)  # no date: nothing to conclude
    # no stated days is "every day", not "unknown"
    assert not parse_opening({"opening_hours": "09:00-17:00"}).closed_on(
        date(2026, 9, 7))


@pytest.mark.parametrize("start,end,inside", [
    (time(10), time(11), True),
    (time(9, 30), time(12, 30), True),   # exactly the range
    (time(8), time(9), False),           # before it opens
    (time(17), time(19), False),         # past closing
    (time(12), time(15), False),         # straddles the midday closure
    (time(14, 30), None, True),          # an instant inside
    (time(13), None, False),             # an instant in the closure
])
def test_covers_a_visit(start, end, inside):
    opening = parse_opening({"opening_hours": "09:30-12:30, 14:00-18:00"})
    assert opening.covers(start, end) is inside


def test_covers_a_range_that_crosses_midnight():
    opening = parse_opening({"opening_hours": "18:00-02:00"})
    assert opening.covers(time(23), time(0, 30))   # over the midnight itself
    assert opening.covers(time(0, 30), time(1))    # the small hours
    assert not opening.covers(time(17), time(19))  # starts before it opens


def test_nothing_stated_always_fits():
    assert parse_opening({"opening_days": "mon"}).covers(time(3), time(4))


# -- the model ------------------------------------------------------------

def test_a_point_of_interest_carries_the_opening():
    itinerary = Itinerary.from_dict(
        _raw(opening_days="tue-sun", opening_hours="09:30-18:00"))
    opening = itinerary.days[3].activities[2].opening
    assert opening.days[0] == "tuesday"
    assert opening.hours == ((time(9, 30), time(18, 0)),)


def test_a_point_of_interest_without_the_fields_has_no_opening():
    itinerary = Itinerary.from_dict(json.loads(EXAMPLE.read_text("utf-8")))
    assert itinerary.days[3].activities[2].opening is None


# -- serialization --------------------------------------------------------

def test_the_resolved_doc_carries_the_folded_and_displayable_forms():
    """The viewer only names the weekdays; the folding into runs and the
    (language-neutral) hours string are done here, once."""
    itinerary = Itinerary.from_dict(
        _raw(opening_days="mon-wed, fri", opening_hours="09:30-12:30, 14:00-18:00"))
    poi = to_dict(itinerary)["days"][3]["activities"][2]
    assert poi["opening"] == {
        "days": ["monday", "tuesday", "wednesday", "friday"],
        "day_runs": [["monday", "wednesday"], ["friday", "friday"]],
        "hours": [["09:30", "12:30"], ["14:00", "18:00"]],
        "hours_display": "09:30–12:30, 14:00–18:00",
        # One default rule, so `per_day` is false and the viewer draws the
        # days-then-hours line rather than one part per rule.
        "per_day": False,
        "rules": [{
            "days": [],
            "day_runs": [],
            "hours": [["09:30", "12:30"], ["14:00", "18:00"]],
            "hours_display": "09:30–12:30, 14:00–18:00",
        }],
    }


def test_a_point_of_interest_with_no_opening_serializes_null():
    itinerary = Itinerary.from_dict(json.loads(EXAMPLE.read_text("utf-8")))
    poi = to_dict(itinerary)["days"][3]["activities"][2]
    assert poi["opening"] is None


# -- the validator --------------------------------------------------------

def test_a_visit_on_a_closed_day_warns():
    # the cathedral is visited on Thursday 2026-06-11
    messages = _messages(_raw(opening_days="mon-wed"))
    assert any("falls on a Thursday" in m and "Cathédrale Sainte-Marie" in m
               and "Monday–Wednesday" in m for m in messages), messages


def test_an_open_day_does_not_warn():
    assert not any("falls on a" in m for m in _messages(_raw(opening_days="mon-fri")))


def test_a_visit_outside_the_hours_warns():
    messages = _messages(_raw(opening_hours="14:00-18:00"))
    assert any("falls outside the opening hours" in m and "14:00–18:00" in m
               for m in messages), messages


def test_a_visit_straddling_the_midday_closure_warns():
    """The 11:20 → 12:20 visit sits inside neither range, which is the point of
    keeping the closure as two ranges rather than one 09:00-18:00 span."""
    messages = _messages(_raw(opening_hours="09:00-12:00, 14:00-18:00"))
    assert any("falls outside the opening hours" in m for m in messages), messages


def test_a_visit_inside_the_hours_does_not_warn():
    messages = _messages(_raw(opening_hours="09:00-18:00", opening_days="mon-sun"))
    assert not any("opening hours" in m or "falls on a" in m for m in messages)


def test_the_check_reads_the_resolved_times_not_the_stated_ones():
    """The cathedral states no ``start_time`` — its 11:20 start is inferred from
    the drive before it, so a check against the raw JSON would see nothing."""
    raw = _raw(opening_hours="14:00-18:00")
    assert "start_time" not in raw["days"][3]["activities"][1]
    assert any("falls outside the opening hours" in m for m in _messages(raw))


def test_a_nested_visit_is_checked_too():
    """A nested stop is never put on the timeline, so it has no resolved time —
    but the day it falls on is still known."""
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    # day 2 (Tuesday) — a point of interest nested in the old-town place
    raw["days"][1]["activities"][2]["activities"] = [
        {"type": "point_of_interest", "name": "Closed chapel",
         "opening_days": "wednesday", "duration": "20 min"}
    ]
    assert any("Closed chapel" in m and "falls on a Tuesday" in m
               for m in _messages(raw))


def test_an_invalid_value_is_an_error():
    errors = _messages(_raw(opening_days="funday"), level="error")
    assert any("'opening_days' is invalid" in m for m in errors), errors


def test_the_warnings_localize():
    messages = _messages(_raw(opening_days="mon-wed"), lang="fr")
    assert any("jeudi" in m and "lundi–mercredi" in m for m in messages), messages


def test_the_field_errors_localize():
    errors = _messages(_raw(opening_hours="10:00-10:00"), level="error", lang="fr")
    assert any("ouvre et ferme à la même heure" in m for m in errors), errors


# -- the PDF --------------------------------------------------------------

def _opening_row(itinerary, lang="en"):
    """The text the opening row draws, in the order the cells are written."""
    pdf = TravelPDF(itinerary, lang, False, "google")
    pdf.add_page()
    written = []
    real_cell, real_multi = pdf.cell, pdf.multi_cell
    pdf.cell = lambda w, h, text="", *a, **kw: (written.append(text),
                                               real_cell(w, h, text, *a, **kw))[1]
    pdf.multi_cell = lambda w, h, text="", *a, **kw: (
        written.append(text), real_multi(w, h, text, *a, **kw))[1]
    pdf._opening_line(itinerary.days[3].activities[2], 20, 150)
    return [t for t in written if t]


def test_the_pdf_draws_the_label_then_the_days_and_hours():
    itinerary = Itinerary.from_dict(
        _raw(opening_days="tue-sun", opening_hours="09:30-12:30, 14:00-18:00"))
    assert _opening_row(itinerary) == ["Open  ",
                                       "Tue–Sun  ·  09:30–12:30, 14:00–18:00"]


def test_the_pdf_row_localizes():
    itinerary = Itinerary.from_dict(_raw(opening_days="tue-sun"))
    assert _opening_row(itinerary, "fr") == ["Ouvert  ", "mar.–dim."]


def test_the_pdf_draws_nothing_without_an_opening():
    itinerary = Itinerary.from_dict(json.loads(EXAMPLE.read_text("utf-8")))
    assert _opening_row(itinerary) == []


@pytest.mark.parametrize("ink_saver", [False, True])
def test_a_book_with_opening_hours_builds(tmp_path, ink_saver):
    itinerary = Itinerary.from_dict(
        _raw(opening_days="tue-sun", opening_hours="09:30-12:30, 14:00-18:00"))
    out = tmp_path / "opening.pdf"
    build_pdf(itinerary, out, "en", ink_saver=ink_saver, maps=False)
    assert out.stat().st_size > 1000


# -- the calendar export --------------------------------------------------

def test_the_ics_packs_the_opening_as_a_detail_line():
    itinerary = Itinerary.from_dict(
        _raw(opening_days="tue-sun", opening_hours="09:30-18:00"))
    text = build_ics(itinerary, lang="en").replace("\r\n ", "")
    # RFC 5545 escapes the comma between the days and the hours
    assert r"Open: Tue–Sun\, 09:30–18:00" in text
