"""The ``misc`` group and its ``emergency_contacts``: parsing, serialization,
validation, stitching, and the PDF page both renderers mirror."""

import json
from pathlib import Path

import pytest

from odysseyra_travelbook import Itinerary, build_pdf, validate_text
from odysseyra_travelbook.models import EmergencyContact, ItineraryError, to_dict
from odysseyra_travelbook.pdf import TravelPDF
from odysseyra_travelbook.stitch import aggregate, fragment_files
from odysseyra_travelbook.validate import validate_fragment

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE = EXAMPLES / "pyrenees.json"

CONTACTS = [
    {"name": "Emergency — any service", "contact": "112"},
    {"name": "SAMU", "contact": "15"},
]


def _doc(contacts=None, **misc):
    """pyrenees.json with its `misc` replaced (``contacts=None`` drops the key)."""
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    if contacts is None and not misc:
        raw.pop("misc", None)
    else:
        raw["misc"] = {**({} if contacts is None
                          else {"emergency_contacts": contacts}), **misc}
    return raw


def _itinerary(contacts=None, **misc):
    return Itinerary.from_dict(_doc(contacts, **misc))


def _messages(findings, level):
    return [f.message for f in findings if f.level == level]


# -- the model -------------------------------------------------------------

def test_the_group_is_optional_and_defaults_to_no_contacts():
    assert _itinerary().emergency_contacts == []


def test_contacts_are_parsed_in_order():
    assert _itinerary(CONTACTS).emergency_contacts == [
        EmergencyContact("Emergency — any service", "112"),
        EmergencyContact("SAMU", "15"),
    ]


def test_both_halves_are_optional():
    # Neither field is required: a number with no label is still dialable, and a
    # label with no number tells the traveller what to look up.
    contacts = _itinerary([{"contact": "112"}, {"name": "Your embassy"}])
    assert contacts.emergency_contacts == [
        EmergencyContact("", "112"),
        EmergencyContact("Your embassy", ""),
    ]


def test_whitespace_is_stripped_and_an_empty_entry_is_dropped():
    it = _itinerary([{"name": "  SAMU  ", "contact": " 15 "},
                     {"name": "   ", "contact": ""},
                     {}])
    assert it.emergency_contacts == [EmergencyContact("SAMU", "15")]


def test_the_contact_is_never_parsed():
    # Emergency numbering is local, and an entry may hold an email or an address
    # instead — so whatever is written survives byte for byte.
    for value in ("112", "+996 312 597 000", "help@example.com",
                  "2 Route de Cauterets, 65260 Pierrefitte-Nestalas"):
        it = _itinerary([{"name": "x", "contact": value}])
        assert it.emergency_contacts[0].contact == value


@pytest.mark.parametrize("misc", [
    {"emergency_contacts": "112"},          # not an array
    {"emergency_contacts": [["112"]]},      # an entry that isn't an object
])
def test_a_broken_shape_is_a_model_error(misc):
    raw = _doc()
    raw["misc"] = misc
    with pytest.raises(ItineraryError):
        Itinerary.from_dict(raw)


def test_a_non_object_group_is_a_model_error():
    raw = _doc()
    raw["misc"] = ["112"]
    with pytest.raises(ItineraryError):
        Itinerary.from_dict(raw)


def test_the_group_is_read_from_its_own_object_only():
    # Unlike travel_description/defaults, `misc` has no top-level fallback.
    raw = _doc()
    raw["emergency_contacts"] = CONTACTS
    assert Itinerary.from_dict(raw).emergency_contacts == []


# -- serialization (the viewer's contract) ---------------------------------

def test_the_contacts_reach_the_viewer_flattened_at_the_top_level():
    assert to_dict(_itinerary(CONTACTS))["emergency_contacts"] == CONTACTS


def test_no_contacts_serializes_as_an_empty_list():
    assert to_dict(_itinerary())["emergency_contacts"] == []


# -- the validator ---------------------------------------------------------

def test_a_missing_group_states_its_default():
    infos = _messages(validate_text(json.dumps(_doc(), indent=2)), "info")
    assert any("'emergency_contacts' is missing" in m and "misc" in m
               for m in infos)


def test_a_complete_contact_raises_nothing():
    findings = validate_text(json.dumps(_doc(CONTACTS), indent=2))
    assert not [f for f in findings
                if f.level in ("error", "warning") and "contact" in f.message]


@pytest.mark.parametrize("contact,missing", [
    ({"contact": "112"}, "name"),
    ({"name": "Police"}, "contact"),
    ({"name": "Police", "contact": "   "}, "contact"),
])
def test_a_half_filled_contact_is_a_warning_not_an_error(contact, missing):
    findings = validate_text(json.dumps(_doc([contact]), indent=2))
    assert _messages(findings, "error") == []
    assert any(f"'{missing}' is missing" in m
               for m in _messages(findings, "warning"))


def test_an_entirely_empty_contact_is_a_warning():
    # The model drops it, so without this it would vanish without a word.
    findings = validate_text(json.dumps(_doc([{"name": "", "contact": ""}]),
                                        indent=2))
    assert any("emergency contact is empty" in m
               for m in _messages(findings, "warning"))


@pytest.mark.parametrize("misc,fragment", [
    ({"emergency_contacts": "112"}, "must be an array"),
    ({"emergency_contacts": ["112"]}, "must be an object"),
])
def test_a_broken_shape_is_a_validator_error(misc, fragment):
    raw = _doc()
    raw["misc"] = misc
    errors = _messages(validate_text(json.dumps(raw, indent=2)), "error")
    assert any(fragment in m for m in errors), errors


def test_a_non_object_group_is_a_validator_error():
    raw = _doc()
    raw["misc"] = ["112"]
    errors = _messages(validate_text(json.dumps(raw, indent=2)), "error")
    assert any("'misc' must be an object" in m for m in errors), errors


def test_a_finding_points_at_the_offending_line():
    text = json.dumps(_doc([{"name": "ok", "contact": "112"}, {"name": "half"}]),
                      indent=2)
    warning = next(f for f in validate_text(text)
                   if f.level == "warning" and "'contact' is missing" in f.message)
    # The line it names must be inside the second entry, not the first.
    lines = text.split("\n")
    assert '"half"' in "\n".join(lines[warning.line - 2:warning.line + 2])


# -- the stitch fragment ---------------------------------------------------

def test_the_group_stitches_from_a_misc_json_fragment(tmp_path):
    root = tmp_path / "trip"
    (root / "days").mkdir(parents=True)
    (root / "travel_description.json").write_text(json.dumps({"title": "T"}))
    (root / "misc.json").write_text(json.dumps({"emergency_contacts": CONTACTS}))
    (root / "days" / "1.json").write_text(json.dumps(
        {"title": "d", "activities": [{"type": "point_of_interest", "name": "M"}]}))

    assert aggregate(root)["misc"] == {"emergency_contacts": CONTACTS}
    assert ("misc", root / "misc.json") in fragment_files(root)


def test_a_misc_fragment_is_validated_against_its_own_lines():
    text = json.dumps({"emergency_contacts": [{"name": "Police"}]}, indent=2)
    findings = validate_fragment(text, "misc")
    warning = next(f for f in findings if "'contact' is missing" in f.message)
    assert 1 <= warning.line <= len(text.split("\n"))


def test_the_example_fragments_still_reassemble_the_example():
    # pyrenees_pieces/misc.json must round-trip like every other fragment.
    assert aggregate(EXAMPLES / "pyrenees_pieces") == json.loads(
        EXAMPLE.read_text(encoding="utf-8"))


# -- the PDF page ----------------------------------------------------------

def _rows(itinerary, lang="en"):
    """The (name, contact) pairs the last page draws, in order."""
    pdf = TravelPDF(itinerary, lang, False, "google")
    drawn = []
    pdf._emergency_row = lambda c, last=False: drawn.append((c.name, c.contact))
    pdf.emergency_contacts()
    return drawn


def test_the_page_lists_every_contact_in_order():
    assert _rows(_itinerary(CONTACTS)) == [("Emergency — any service", "112"),
                                           ("SAMU", "15")]


def test_the_page_is_skipped_when_there_are_no_contacts(tmp_path):
    before = build_pdf(_itinerary(), tmp_path / "none.pdf")
    after = build_pdf(_itinerary(CONTACTS), tmp_path / "some.pdf")
    assert after.stat().st_size > before.stat().st_size


def test_the_band_header_is_localized():
    for lang, kicker, title in (("en", "IN CASE OF EMERGENCY", "Emergency contacts"),
                                ("fr", "EN CAS D'URGENCE", "Numéros d'urgence")):
        pdf = TravelPDF(_itinerary(CONTACTS), lang, False, "google")
        headers = []
        pdf._band_header = lambda k, t, right="": headers.append((k, t))
        pdf.emergency_contacts()
        assert headers == [(kicker, title)]


def test_the_cover_links_to_the_page_only_when_there_are_contacts():
    for contacts, expected in ((CONTACTS, True), (None, False)):
        pdf = TravelPDF(_itinerary(contacts), "en", False, "google")
        pdf.cover()
        assert hasattr(pdf, "emergency_link") is expected


@pytest.mark.parametrize("contact", [
    {"name": "SAMU", "contact": "15"},                       # both, side by side
    {"name": "Rescue", "contact": "2 Route de Cauterets, 65260 Pierrefitte"},
    {"contact": "112"},                                      # number alone
    {"name": "Your embassy"},                                # label alone
])
def test_every_row_shape_draws_and_advances_the_cursor(contact):
    pdf = TravelPDF(_itinerary([contact]), "en", False, "google")
    pdf.add_page()
    y = pdf.get_y()
    pdf._emergency_row(pdf.itinerary.emergency_contacts[0], last=True)
    assert pdf.get_y() > y


@pytest.mark.parametrize("ink_saver", [False, True])
def test_a_book_with_contacts_still_builds(tmp_path, ink_saver):
    out = build_pdf(_itinerary(CONTACTS), tmp_path / "contacts.pdf",
                    ink_saver=ink_saver)
    assert out.read_bytes().startswith(b"%PDF")


# -- the examples ----------------------------------------------------------

@pytest.mark.parametrize("name", ["france.json", "france_fr.json",
                                  "pyrenees.json"])
def test_every_valid_example_lists_emergency_contacts(name):
    it = Itinerary.from_json_file(str(EXAMPLES / name))
    assert it.emergency_contacts, f"{name} should carry emergency contacts"
    # Every entry has at least one half — an empty one would have been dropped.
    assert all(c.name or c.contact for c in it.emergency_contacts)
