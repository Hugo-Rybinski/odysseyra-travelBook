import json
from datetime import date
from pathlib import Path

from odysseyra_travelbook import Itinerary, build_pdf, format_findings, validate_text
from odysseyra_travelbook.lang import LANGUAGES, fmt_date, tr

EXAMPLE_FR = Path(__file__).resolve().parent.parent / "examples" / "pyrenees_fr.json"


def test_languages_available():
    assert LANGUAGES == ("en", "fr")


def test_tr_identity_and_fallback():
    assert tr("Itinerary", "en") == "Itinerary"       # English is identity
    assert tr("Itinerary", "fr") == "Itinéraire"       # translated
    assert tr("Itinerary", "de") == "Itinerary"        # unknown lang → source
    assert tr("not a known string", "fr") == "not a known string"  # missing key


def test_fmt_date_localized():
    d = date(2026, 6, 8)
    assert fmt_date(d, "long", "en") == "Jun 08, 2026"
    assert fmt_date(d, "long", "fr") == "08 juin 2026"
    assert fmt_date(d, "wd_md", "en") == "Mon Jun 08"
    assert fmt_date(d, "wd_md", "fr") == "lun. 08 juin"


def test_validate_output_is_french():
    doc = {"travel_description": {"title": "T"},
           "days": [{"title": "d", "activities": [
               {"type": "point_of_interest", "name": "M", "start_time": "09:00",
                "end_time": "11:00", "duration": "3h"}]}]}
    findings = validate_text(json.dumps(doc), lang="fr")
    text = format_findings(findings, verbose=2, lang="fr")
    assert "incompatibles" in text           # the time/duration message, translated
    assert "avertissement(s)" in text        # the summary, translated


def test_build_pdf_french(tmp_path):
    it = Itinerary.from_json_file(EXAMPLE_FR)
    out = build_pdf(it, tmp_path / "fr.pdf", lang="fr")
    assert out.exists() and out.read_bytes().startswith(b"%PDF")


def test_example_fr_has_no_errors():
    findings = validate_text(EXAMPLE_FR.read_text(encoding="utf-8"), lang="fr")
    assert [f for f in findings if f.level == "error"] == []
