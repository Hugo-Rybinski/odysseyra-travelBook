"""Moon-phase helper + its opt-in wiring into the serialized model."""

from datetime import date
from pathlib import Path

from odysseyra_travelbook.models import Itinerary, moon_phase, to_dict

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
MOON_EMOJI = {"🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"}


def test_known_phases():
    # Reference new moon (the epoch) and a full moon ~15 days later.
    assert moon_phase(date(2000, 1, 6)).key == "moonNew"
    assert moon_phase(date(2000, 1, 21)).key == "moonFull"
    # A well-known full moon.
    assert moon_phase(date(2025, 1, 13)).emoji == "🌕"


def test_phase_shape():
    p = moon_phase(date(2026, 9, 6))
    assert p.emoji in MOON_EMOJI
    assert p.key.startswith("moon") and p.name


def test_serialized_moon_opt_in():
    # france.json sets show_moon_phase → every day carries a moon object.
    it = Itinerary.from_json_file(str(EXAMPLES / "france.json"))
    assert it.show_moon_phase is True
    days = to_dict(it)["days"]
    for d in days:
        assert d["moon"] is not None
        assert d["moon"]["emoji"] in MOON_EMOJI
        assert d["moon"]["key"].startswith("moon")


def test_serialized_moon_on_by_default():
    # pyrenees.json does not set the flag → the default (on) applies, so every
    # dated day carries its phase.
    it = Itinerary.from_json_file(str(EXAMPLES / "pyrenees.json"))
    assert it.show_moon_phase is True
    days = to_dict(it)["days"]
    assert days and all(d["moon"] is not None for d in days if d["date"])


def test_serialized_moon_can_be_switched_off():
    # `show_moon_phase: false` is the opt-out — nothing is emitted then.
    it = Itinerary.from_dict({
        "travel_description": {"title": "T"},
        "defaults": {"show_moon_phase": False},
        "days": [{"title": "D", "date": "2026-06-08", "activities": [
            {"type": "buffer", "duration": "1h"}]}],
    })
    assert it.show_moon_phase is False
    assert all(d["moon"] is None for d in to_dict(it)["days"])
