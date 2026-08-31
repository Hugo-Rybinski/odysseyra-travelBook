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


def _band(src: str, lang: str = "en"):
    """Each day's ``(kicker, meta line, moon left to the stay bar)`` as the day
    page would draw it."""
    from odysseyra_travelbook.pdf import TravelPDF

    it = Itinerary.from_json_file(str(EXAMPLES / src))
    pdf = TravelPDF(it, lang, False, "google")
    pdf.add_page()
    out = []
    for i, day in enumerate(it.days, 1):
        kicker = pdf.t("DAY {index}").format(index=i)
        head = [b for b in (day.city, pdf.d(day.date, "wd_full_md")) if b]
        moon = moon_phase(day.date) if it.show_moon_phase and day.date else None
        text, in_band = pdf._sun_moon_text(kicker, head, it.sun_for(day), moon)
        out.append((kicker, text, None if in_band else moon))
    return out


def test_the_moon_phase_closes_the_suntimes_line():
    # Both switches on: the phase joins the sun times, and leaves the stay bar.
    rows = _band("france.json")
    named = [t for _, t, stay_moon in rows if "Sunrise" in t and stay_moon is None]
    assert named, "france.json has days with both"
    assert any(t.endswith("Full moon") or "🌕" in t or "🌘" in t for t in named)
    for kicker, text, stay_moon in rows:
        if "Sunrise" in text:
            assert stay_moon is None, "shown in the band → not repeated in the bar"


def test_the_stay_bar_keeps_the_moon_without_sun_times():
    # france.json day 1 is the Atlantic crossing: its only reference sits hours
    # of solar time from the day's clock, so there are no sun times to append
    # to — the phase stays where it has always been.
    _, text, stay_moon = _band("france.json")[0]
    assert text == "", "no sun line on the crossing day"
    assert stay_moon is not None, "so the bar still carries the phase"


def test_a_too_wide_band_falls_back_to_the_emoji_then_to_the_bar():
    # The kicker and the meta line share a row, so the phase name is dropped
    # when it wouldn't fit. pyrenees day 4's city is long enough to trigger it.
    rows = _band("pyrenees.json")
    tails = [t.split(", ")[-1] for _, t, _ in rows if "Sunrise" in t]
    assert any(" " in tail for tail in tails), "most days name the phase"
    assert any(" " not in tail for tail in tails), "a long line keeps the emoji only"
    # Whatever the fallback, a phase in the band never also reaches the bar.
    assert all(stay_moon is None for _, text, stay_moon in rows if "🌒" in text
               or "🌘" in text or "🌗" in text)


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
