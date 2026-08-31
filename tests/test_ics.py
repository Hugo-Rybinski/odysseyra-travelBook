"""Tests for the iCalendar (.ics) export (`odysseyra_travelbook.build_ics`)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from odysseyra_travelbook import Itinerary, build_ics
from odysseyra_travelbook.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _ics(name: str, lang: str = "en") -> str:
    return build_ics(Itinerary.from_json_file(EXAMPLES / name), lang=lang, now=NOW)


def _events(ics: str) -> list[str]:
    return re.findall(r"BEGIN:VEVENT.*?END:VEVENT", ics, re.S)


def _unfold(text: str) -> str:
    """Reverse RFC 5545 line folding (CRLF + leading space) for substring checks."""
    return text.replace("\r\n ", "")


def test_well_formed_calendar():
    ics = _ics("france.json")
    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert ics.rstrip("\r\n").endswith("END:VCALENDAR")
    assert "\r\n" in ics and "PRODID:" in ics and "VERSION:2.0" in ics
    events = _events(ics)
    assert events, "the flagship trip yields events"
    for e in events:
        for prop in ("UID:", "DTSTAMP:", "DTSTART", "DTEND", "SUMMARY:"):
            assert prop in e, f"every VEVENT carries {prop}"


def test_buffers_are_excluded():
    # France uses defaults.buffer, so the resolved timeline has buffers; none of
    # them should become calendar events.
    ics = _ics("france.json")
    assert "SUMMARY:Buffer" not in ics


def test_every_content_line_is_folded_to_75_octets():
    ics = _ics("france.json")  # has long descriptions / accented text
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75, repr(line)


def test_uids_are_unique():
    ics = _ics("france.json")
    uids = re.findall(r"UID:(.+)", ics)
    assert uids and len(uids) == len(set(uids))


def test_summaries_are_prefixed_with_type_emoji():
    summaries = _unfold("\n".join(_events(_ics("france.json"))))
    # roads, planes, trains, hikes, meals and accommodation each get a glyph.
    assert "SUMMARY:🚗 " in summaries       # a road/drive
    assert "SUMMARY:✈️ Plane:" in summaries  # a flight
    assert "SUMMARY:🚆 Train:" in summaries  # a train
    assert "SUMMARY:🥾 " in summaries       # a hike
    assert "SUMMARY:🍽️ " in summaries       # a meal
    assert "SUMMARY:🛏️ " in summaries       # an accommodation night


def test_transport_emoji_covers_all_types():
    data = {
        "travel_description": {"title": "T"},
        "defaults": {"timezone": "Z"},
        "days": [{"title": "D1", "date": "2026-05-01"}],
        "transport": [
            {"type": t, "start": "A", "end": "B", "start_date": "2026-05-01",
             "start_time": "08:00", "duration": "1h"}
            for t in ("bus", "taxi", "ferry", "other")
        ],
    }
    u = _unfold(build_ics(Itinerary.from_dict(data), now=NOW))
    assert "SUMMARY:🚌 Bus:" in u
    assert "SUMMARY:🚕 Taxi:" in u
    assert "SUMMARY:⛴️ Ferry:" in u
    assert "SUMMARY:Other: A → B" in u  # 'other' stays unprefixed


def test_cross_timezone_transport_keeps_both_offsets():
    # The NY→Paris flight departs UTC-4 and arrives UTC+2.
    ics = _ics("france.json")
    flight = next(e for e in _events(ics) if "New York JFK → Paris CDG" in e)
    assert "DTSTART;TZID=GMT-0400:" in flight
    assert "DTEND;TZID=GMT+0200:" in flight
    # both offsets get a self-contained VTIMEZONE block
    assert "TZID:GMT-0400" in ics and "TZID:GMT+0200" in ics


def test_return_flight_stays_a_timed_same_day_event():
    # Regression: the Toulouse→JFK leg departs 18:30 (+02) and lands 22:05 (−04)
    # the same day; both ends must fall on 2026-09-11 (not a ~33h multi-day band).
    ics = _ics("france.json")
    leg = _unfold(next(e for e in _events(ics)
                       if "Toulouse-Blagnac → New York JFK" in _unfold(e)))
    start = re.search(r"DTSTART[^:]*:(\d{8})T", leg).group(1)
    end = re.search(r"DTEND[^:]*:(\d{8})T", leg).group(1)
    assert start == "20260911" and end == "20260911"


def _stay_events(ics: str, name: str) -> list[str]:
    # A booking's own events — their SUMMARY is the bed glyph + the accommodation
    # name (not the drive that merely ends there).
    return [e for e in _events(ics) if f"SUMMARY:🛏️ {name}" in _unfold(e)]


def test_accommodation_emits_one_event_per_night():
    # The Paris stay covers 2 nights (arrival Sep 5, departure Sep 7): each night
    # runs 22:00 → 07:00 the next morning.
    nights = _stay_events(_ics("france.json"), "Hôtel des Grands Boulevards")
    assert len(nights) == 2
    starts = sorted(re.search(r"DTSTART[^:]*:(\S+)", e).group(1) for e in nights)
    ends = sorted(re.search(r"DTEND[^:]*:(\S+)", e).group(1) for e in nights)
    assert starts == ["20260905T220000", "20260906T220000"]
    # default accommodation_end_time is midnight → each night ends 00:00 next day
    assert ends == ["20260906T000000", "20260907T000000"]
    assert all("TZID=GMT+0200" in e for e in nights)


def test_accommodation_window_is_customizable():
    data = {
        "travel_description": {"title": "T"},
        "defaults": {
            "timezone": "Z",
            "accommodation_start_time": "18:30",
            "accommodation_end_time": "09:15",
        },
        "days": [{"title": "D1", "date": "2026-05-01"}],
        "accommodations": [
            {"name": "Inn", "arrival": "2026-05-01", "departure": "2026-05-02",
             "city": "Town"}
        ],
    }
    ics = build_ics(Itinerary.from_dict(data), now=NOW)
    nights = _stay_events(ics, "Inn")
    assert len(nights) == 1  # a single-night stay is one event
    assert "DTSTART;TZID=GMT:20260501T183000" in nights[0]
    assert "DTEND;TZID=GMT:20260502T091500" in nights[0]


def test_descriptions_carry_detail():
    nights = [_unfold(e) for e in
              _stay_events(_ics("france.json"), "Hôtel des Grands Boulevards")]
    assert all("Night: " in e for e in nights)  # "Night: 1/2", "Night: 2/2"
    assert any("Night: 1/2" in e for e in nights)
    assert all("Breakfast included: Yes" in e for e in nights)
    assert all("Price: " in e for e in nights)


def test_guidebook_pages_reach_the_event_description():
    # An activity's guidebook pages ride along in its event detail, so the
    # calendar entry points at the same page the book does.
    louvre = _unfold(next(e for e in _events(_ics("france.json"))
                          if "Musée du Louvre" in e))
    assert "Guidebook: p. 44-47" in louvre
    fr = _unfold(next(e for e in _events(_ics("france_fr.json", lang="fr"))
                      if "Musée du Louvre" in e))
    assert "Guide: p. 44-47" in fr


def test_booking_notes_reach_the_event_description():
    # The short note a leg / stay / rental carries is packed as a `Description:`
    # detail — the same label activities already use — on every event it belongs
    # to, including each night of a multi-night stay.
    ics = _ics("france.json")
    flight = _unfold(next(e for e in _events(ics) if "AF23" in e))
    assert "Description: Seats 24A/24B" in flight

    nights = [_unfold(e) for e in
              _stay_events(ics, "Hôtel des Grands Boulevards")]
    assert nights and all("Description: Check-in from 15:00" in e for e in nights)

    # Both car events, since the rental's note is copied onto each.
    car = [_unfold(e) for e in _events(ics) if "Hertz" in e]
    assert len(car) == 2
    assert all("Description: Full-to-full fuel policy" in e for e in car)


def test_french_localizes_labels():
    ics = _ics("france_fr.json", lang="fr")
    flight = _unfold(next(e for e in _events(ics) if "Avion:" in e))
    assert "Départ:" in flight and "Arrivée:" in flight
    assert "Numéro de vol:" in flight


def test_text_values_are_escaped():
    # Addresses contain commas, which must be backslash-escaped in ICS text.
    ics = _unfold(_ics("france.json"))
    assert "\\, 75002 Paris" in ics


def test_cli_writes_ics(tmp_path):
    out = tmp_path / "trip.ics"
    rc = main(["ics", str(EXAMPLES / "france.json"), "-o", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("BEGIN:VCALENDAR")
    assert "BEGIN:VEVENT" in text


def test_cli_default_output_path(tmp_path):
    src = tmp_path / "mini.json"
    src.write_text(
        '{"travel_description":{"title":"Mini"},'
        '"days":[{"title":"D1","date":"2026-05-01",'
        '"activities":[{"type":"place","name":"Somewhere"}]}]}',
        encoding="utf-8",
    )
    rc = main(["ics", str(src)])
    assert rc == 0
    assert (tmp_path / "mini.ics").exists()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
