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


def _sky(src: str, lang: str = "en"):
    """Each day's ``(sun/moon line, moon left to the stay bar)`` as the day page
    would draw it — the line sits in the day's body, above the intro."""
    from odysseyra_travelbook.pdf import TravelPDF

    it = Itinerary.from_json_file(str(EXAMPLES / src))
    pdf = TravelPDF(it, lang, False, "google")
    pdf.add_page()
    out = []
    for day in it.days:
        moon = moon_phase(day.date) if it.show_moon_phase and day.date else None
        text, shown = pdf._sun_moon_line(it.sun_for(day), moon)
        out.append((text, None if shown else moon))
    return out


def test_the_moon_phase_closes_the_suntimes_line():
    # Both switches on: the phase joins the sun times, and leaves the stay bar.
    rows = _sky("france.json")
    named = [t for t, stay_moon in rows if "Sunrise" in t and stay_moon is None]
    assert named, "france.json has days with both"
    for text, stay_moon in rows:
        if "Sunrise" in text:
            assert stay_moon is None, "shown on the line → not repeated in the bar"


def test_the_stay_bar_keeps_the_moon_without_sun_times():
    # france.json day 1 is the Atlantic crossing: its only reference sits hours
    # of solar time from the day's clock, so there are no sun times to append
    # to — the phase stays where it has always been.
    text, stay_moon = _sky("france.json")[0]
    assert text == "", "no sun line on the crossing day"
    assert stay_moon is not None, "so the bar still carries the phase"


def test_the_phase_is_always_named_now_that_the_line_owns_its_row():
    """Regression for the move out of the header band: the line used to share a
    row with the band's kicker, so a long city + a long French phase name had to
    fall back to the emoji alone. In the body it has the full width, so every
    phase is named — in both languages."""
    for src, lang in (("france.json", "en"), ("france_fr.json", "fr"),
                      ("pyrenees.json", "en")):
        for text, _ in _sky(src, lang):
            if not text or "," not in text:
                continue
            tail = text.split(", ")[-1]
            assert " " in tail, f"{src}: {tail!r} should name the phase"


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
