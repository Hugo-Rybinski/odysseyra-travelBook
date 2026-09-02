"""A day's ``bank_holiday`` flag: parsing, serialization, validation, and the
call-out banner both renderers open the day with."""

import json
from pathlib import Path

import pytest

from odysseyra_travelbook import Itinerary, build_pdf, validate_text
from odysseyra_travelbook.models import to_dict
from odysseyra_travelbook.pdf import TravelPDF
from odysseyra_travelbook.pdf.base import FONT

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE = EXAMPLES / "pyrenees.json"


def _itinerary(flags):
    """pyrenees.json with ``bank_holiday`` set as ``flags`` says — one entry per
    day, ``None`` leaving the key out entirely."""
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for day, flag in zip(raw["days"], flags):
        if flag is not None:
            day["bank_holiday"] = flag
    return Itinerary.from_dict(raw)


def _notices(itinerary, lang="en"):
    """The ``(label, advice)`` pairs the day pages open with, in page order."""
    pdf = TravelPDF(itinerary, lang, False, "google")
    calls = []
    pdf._notice = lambda label, text="": calls.append((label, text))
    for i, day in enumerate(itinerary.days, 1):
        pdf.day(i, day)
    return calls


# -- the model -------------------------------------------------------------

def test_the_flag_defaults_to_false():
    it = Itinerary.from_json_file(str(EXAMPLE))
    assert [d.bank_holiday for d in it.days] == [False] * len(it.days)


@pytest.mark.parametrize("given,expected", [
    (True, True), (False, False), ("yes", True), ("no", False), ("true", True),
])
def test_the_flag_is_parsed_like_every_other_bool(given, expected):
    it = _itinerary([given])
    assert it.days[0].bank_holiday is expected


def test_the_flag_is_serialized_for_the_viewer():
    days = to_dict(_itinerary([True, None, False]))["days"]
    assert [d["bank_holiday"] for d in days] == [True, False, False, False]


# -- the validator ---------------------------------------------------------

def test_a_non_boolean_flag_is_an_error():
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["days"][0]["bank_holiday"] = "maybe"
    errors = [f.message for f in validate_text(json.dumps(doc)) if f.level == "error"]
    assert any("'bank_holiday'" in m and "true or false" in m for m in errors)


def test_the_missing_flag_states_its_default():
    infos = [f.message for f in validate_text(EXAMPLE.read_text(encoding="utf-8"))
             if f.level == "info"]
    assert any("'bank_holiday' is missing" in m and "false" in m for m in infos)


# -- the PDF banner --------------------------------------------------------

def test_the_banner_opens_only_the_flagged_days():
    assert _notices(_itinerary([False, True, None, True])) == [
        ("⚠️ BANK HOLIDAY", "Expect closures and reduced opening hours."),
        ("⚠️ BANK HOLIDAY", "Expect closures and reduced opening hours."),
    ]


def test_no_banner_when_no_day_is_flagged():
    assert _notices(Itinerary.from_json_file(str(EXAMPLE))) == []


def test_the_banner_is_localized():
    labels = _notices(_itinerary([True]), lang="fr")
    assert labels == [("⚠️ JOUR FÉRIÉ",
                       "Attendez-vous à des fermetures et à des horaires réduits.")]


class _Stop(Exception):
    """Cuts a day's render short once the order under test is known."""


def test_the_banner_precedes_the_sun_line_the_intro_and_the_map():
    # It's a heads-up about what's open, so it must be the first thing on the
    # page below the header band — ahead of the day's sky line, its intro and
    # its map. (The sun/moon line sits between the banner and the intro, which
    # is where the viewer puts it too.)
    it = _itinerary([True])
    pdf = TravelPDF(it, "en", False, "google")
    assert it.days[0].description, "the example day has an intro to come after"

    order = []
    real_multi_cell = pdf.multi_cell
    pdf._notice = lambda *a, **kw: order.append("notice")

    def record(*a, **kw):
        # Both the sky line and the intro are drawn with multi_cell; the sun
        # times are the ones that open with the ☀️.
        text = next((x for x in a if isinstance(x, str)), "")
        order.append("sun" if text.startswith("☀") else "intro")
        return real_multi_cell(*a, **kw)

    pdf.multi_cell = record

    def maps(day):  # the last of the four — stop before the rest of the page
        order.append("maps")
        raise _Stop

    pdf.day_maps = maps
    with pytest.raises(_Stop):
        pdf.day(1, it.days[0])
    assert order == ["notice", "sun", "intro", "maps"]


# -- the strip itself ------------------------------------------------------

def test_the_advice_is_dropped_when_it_would_overrun_the_strip():
    # `_notice` draws one line only, so a sentence too long to sit beside the
    # label is left out rather than spilling past the strip's edge.
    pdf = TravelPDF(Itinerary.from_json_file(str(EXAMPLE)), "en", False, "google")
    pdf.add_page()
    drawn = []
    pdf.cell = lambda w, h, text="", *a, **kw: drawn.append(text)

    pdf._notice("⚠️ BANK HOLIDAY", "Expect closures and reduced opening hours.")
    assert len(drawn) == 2, "both parts fit on the standard A4 content width"

    drawn.clear()
    pdf._notice("⚠️ BANK HOLIDAY", "a really quite wordy piece of advice " * 6)
    assert drawn == ["⚠️ BANK HOLIDAY"]


def test_the_strip_advances_the_cursor_past_itself():
    pdf = TravelPDF(Itinerary.from_json_file(str(EXAMPLE)), "en", False, "google")
    pdf.add_page()
    y = pdf.get_y()
    pdf._notice("⚠️ BANK HOLIDAY")
    assert pdf.get_y() > y + pdf._NOTICE_H


def test_the_label_and_advice_fit_the_page_in_both_languages():
    # The strip has one line: if either wording grows past the content width the
    # advice silently disappears, so measure both languages here instead.
    for src, lang in (("pyrenees.json", "en"), ("france_fr.json", "fr")):
        it = Itinerary.from_json_file(str(EXAMPLES / src))
        pdf = TravelPDF(it, lang, False, "google")
        pdf.add_page()
        label = f"⚠️ {pdf.t('BANK HOLIDAY')}"
        advice = pdf.t("Expect closures and reduced opening hours.")
        pdf.set_font(FONT, "B", 9)
        used = pdf.get_string_width(label)
        pdf.set_font(FONT, "", 9)
        used += pdf.get_string_width(f"  {advice}") + 2 * pdf._NOTICE_PAD
        assert used <= pdf.content_width, f"{lang}: the advice would be dropped"


@pytest.mark.parametrize("ink_saver", [False, True])
def test_a_flagged_book_still_builds(tmp_path, ink_saver):
    out = build_pdf(_itinerary([True, True, True, True]),
                    tmp_path / "holidays.pdf", ink_saver=ink_saver)
    assert out.read_bytes().startswith(b"%PDF")
    assert out.stat().st_size > 1000
