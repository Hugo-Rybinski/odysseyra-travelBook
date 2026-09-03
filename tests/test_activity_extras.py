"""The five fields added for itineraries the schema couldn't hold: an activity's
``price``/``currency`` and ``contact``, a point of interest's per-weekday
``opening_hours``, a transport leg's ``distance_km``, and the four new point-of-
interest categories (``market`` / ``spring`` / ``canyon`` / ``mountain pass``).
"""

import json
from datetime import date, time
from pathlib import Path

import pytest

from odysseyra_travelbook import Itinerary, build_ics, build_pdf, validate_text
from odysseyra_travelbook.models import POI_CATEGORIES, to_dict
from odysseyra_travelbook.models.opening import OpeningRule, parse_opening
from odysseyra_travelbook.pdf import TravelPDF

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
FRANCE = EXAMPLES / "france.json"


def _doc(activities, **defaults):
    base = {"start_time": "09:00", "end_time": "18:00"}
    base.update(defaults)
    return {
        "travel_description": {"title": "T", "start_date": "2026-06-01"},
        "defaults": base,
        "days": [{"title": "D1", "activities": activities}],
    }


def _poi(name, **extra):
    return {"type": "point_of_interest", "name": name, **extra}


def _day(activities, **defaults):
    return Itinerary.from_dict(_doc(activities, **defaults)).days[0]


def _findings(doc, level="error"):
    """The messages of one level, from a doc dict (line numbers don't matter
    here — the specs tables are what's under test)."""
    return [f.message for f in validate_text(json.dumps(doc, indent=2))
            if f.level == level]


def _ics_text(itin):
    """The export with RFC 5545 line folding reversed and text-escaping undone,
    so a detail line can be matched as one substring."""
    return build_ics(itin).replace("\r\n ", "").replace("\\,", ",")


# -- price / currency ------------------------------------------------------

def test_price_and_currency_are_parsed_on_every_type():
    """`_sched` carries them, so each type gets them from one place."""
    day = _day([
        {"type": "road", "price": 9.5, "legs": [
            {"start_location": "A", "end_location": "B", "duration": "1h",
             "distance_km": 10,
             "end_coordinate": {"lat": 1, "long": 2}}]},
        _poi("P", duration="1h", price=12, currency="EUR"),
        {"type": "place", "name": "Pl", "duration": "1h", "price": 3},
        {"type": "hike", "name": "H", "duration": "1h", "price": 5},
        {"type": "meal", "restaurant": "R", "duration": "1h", "price": 28},
    ])
    assert [a.price for a in day.activities if a.kind != "buffer"] == \
        [9.5, 12.0, 3.0, 5.0, 28.0]
    # the buffers between them carry none
    assert all(a.price is None for a in day.activities if a.kind == "buffer")


def test_no_price_stays_none():
    assert _day([_poi("P", duration="1h")]).activities[0].price is None


def test_zero_is_kept_and_is_not_absent():
    """A stated free entry is information; only `None` means "unknown"."""
    assert _day([_poi("P", duration="1h", price=0)]).activities[0].price == 0.0


def test_a_buffer_has_no_price():
    """`Buffer.from_dict` doesn't go through `_sched`, so it takes the default."""
    day = _day([_poi("A", duration="1h"), {"type": "buffer", "duration": "30 min"},
                _poi("B", duration="1h")])
    buf = next(a for a in day.activities if a.kind == "buffer")
    assert buf.price is None and buf.currency == "" and buf.contact == ""


def test_the_currency_defaults_to_the_trip_default_when_serialized():
    itin = Itinerary.from_dict(_doc([_poi("P", duration="1h", price=12)],
                                    currency="USD"))
    price = to_dict(itin)["days"][0]["activities"][0]["price"]
    assert price["currency"] == "USD" and price["amount"] == 12.0


def test_an_activity_price_carries_no_payment_state():
    """There is no `paid` on an activity — a fee at the gate has nothing to
    settle in advance — so the serialized money always reports None."""
    itin = Itinerary.from_dict(_doc([_poi("P", duration="1h", price=12)]))
    assert to_dict(itin)["days"][0]["activities"][0]["price"]["paid"] is None


def test_a_secondary_currency_is_converted():
    itin = Itinerary.from_dict(_doc(
        [_poi("P", duration="1h", price=10)],
        currency="EUR",
        secondary_currencies=[{"currency": "KGS", "change_rate": 100}]))
    price = to_dict(itin)["days"][0]["activities"][0]["price"]
    assert price["in_default"] == 10.0
    assert price["secondaries"] == [{"currency": "KGS", "amount": 1000.0}]


@pytest.mark.parametrize("lang,expected", [("en", "Free"), ("fr", "Gratuit")])
def test_zero_prints_as_free(lang, expected):
    itin = Itinerary.from_dict(_doc([_poi("P", duration="1h", price=0)]))
    pdf = TravelPDF(itin, lang=lang)
    assert pdf.price_inline(0.0, "") == expected


def test_a_real_amount_prints_as_money_not_free():
    itin = Itinerary.from_dict(_doc([_poi("P", duration="1h", price=12)]))
    assert TravelPDF(itin).price_inline(12.0, "") == "€12"


def test_no_price_prints_nothing():
    itin = Itinerary.from_dict(_doc([_poi("P", duration="1h")]))
    assert TravelPDF(itin).price_inline(None, "") == ""


# -- contact ---------------------------------------------------------------

def test_contact_is_free_text_and_never_parsed():
    """Emergency numbering is local and half of these are instructions, so the
    field takes whatever it is given (whitespace aside)."""
    for raw in ("+996 700 732 984", "112", "host@example.com",
                "call the guardian to open the museum"):
        assert _day([_poi("P", duration="1h", contact=raw)]).activities[0].contact \
            == raw
    assert _day([_poi("P", duration="1h", contact="  15  ")]).activities[0].contact \
        == "15"


def test_contact_reaches_the_viewer():
    itin = Itinerary.from_dict(_doc([_poi("P", duration="1h", contact="112")]))
    assert to_dict(itin)["days"][0]["activities"][0]["contact"] == "112"


# -- per-weekday opening hours --------------------------------------------

def test_a_plain_value_is_one_default_rule():
    """The shape every file written before this feature parses to — which is
    what keeps them rendering identically."""
    op = parse_opening({"opening_hours": "09:30-18:00"})
    assert op.rules == (OpeningRule(hours=((time(9, 30), time(18)),)),)
    assert op.per_day is False
    assert op.hours_display == "09:30–18:00"


def test_groups_split_on_semicolons_and_take_their_days():
    op = parse_opening({"opening_hours": "mon-sat 09:00-17:00; sun 10:00-17:00"})
    assert op.per_day is True
    assert [r.days for r in op.rules] == [
        ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday"),
        ("sunday",),
    ]
    assert [r.hours_display for r in op.rules] == ["09:00–17:00", "10:00–17:00"]


def test_a_group_can_hold_several_ranges_and_a_day_list():
    op = parse_opening(
        {"opening_hours": "mon-fri, sun 09:00-12:30, 14:00-18:00; sat 10:00-16:00"})
    assert op.rules[0].days == ("monday", "tuesday", "wednesday", "thursday",
                                "friday", "sunday")
    assert op.rules[0].hours_display == "09:00–12:30, 14:00–18:00"
    assert op.rules[1].days == ("saturday",)


def test_a_day_less_group_is_the_default_for_the_rest():
    op = parse_opening({"opening_hours": "09:00-17:00; sun 10:00-17:00"})
    # Monday isn't named, so it falls through to the default group.
    assert op.hours_on(date(2026, 9, 28)) == ((time(9), time(17)),)     # a Monday
    assert op.hours_on(date(2026, 9, 27)) == ((time(10), time(17)),)    # a Sunday


def test_hours_on_picks_the_matching_rule():
    op = parse_opening({"opening_hours": "mon-sat 09:00-17:00; sun 10:00-17:00"})
    assert op.hours_display_on(date(2026, 9, 24)) == "09:00–17:00"  # Thursday
    assert op.hours_display_on(date(2026, 9, 27)) == "10:00–17:00"  # Sunday


def test_covers_checks_that_days_own_hours():
    """The Karakol museum case: Mon-Sat 09:00-17:00 but Sunday 10:00-17:00, so a
    09:30 visit is fine on a Thursday and outside on a Sunday."""
    op = parse_opening({"opening_hours": "mon-sat 09:00-17:00; sun 10:00-17:00"})
    assert op.covers(time(9, 30), time(10, 30), on=date(2026, 9, 24)) is True
    assert op.covers(time(9, 30), time(10, 30), on=date(2026, 9, 27)) is False


def test_covers_with_no_date_falls_back_to_every_range():
    """A caller with no date must not report a Sunday visit as outside the
    weekday hours, so every stated range is in play."""
    op = parse_opening({"opening_hours": "mon-sat 09:00-17:00; sun 10:00-17:00"})
    assert op.covers(time(9, 30), time(10, 30)) is True


def test_naming_weekdays_in_the_hours_sets_the_open_days():
    op = parse_opening({"opening_hours": "mon-fri 09:00-17:00"})
    assert op.days == ("monday", "tuesday", "wednesday", "thursday", "friday")
    assert op.closed_on(date(2026, 9, 26)) is True   # a Saturday


def test_a_default_group_leaves_the_open_days_empty():
    """It applies to every day, so it claims none in particular."""
    op = parse_opening({"opening_hours": "09:00-17:00; sun 10:00-17:00"})
    assert op.days == ()
    assert op.closed_on(date(2026, 9, 27)) is False


def test_explicit_opening_days_still_win():
    op = parse_opening({"opening_days": "wed-mon",
                        "opening_hours": "09:00-18:00; fri 09:00-21:45"})
    assert op.days == ("monday", "wednesday", "thursday", "friday", "saturday",
                       "sunday")
    assert op.closed_on(date(2026, 9, 29)) is True   # a Tuesday


@pytest.mark.parametrize("value", [
    "09:00-17:00; 10:00-18:00",                 # two default groups
    "mon-fri 09:00-17:00; wed 10:00-18:00",     # wednesday twice
    "someday 09:00-17:00",                      # not a weekday
    "mon-sat",                                  # a group with no times
])
def test_ambiguous_or_malformed_groups_are_rejected(value):
    from odysseyra_travelbook import ItineraryError
    with pytest.raises(ItineraryError, match="opening_hours"):
        parse_opening({"opening_hours": value})


def test_the_rules_reach_the_viewer():
    itin = Itinerary.from_dict(_doc(
        [_poi("P", duration="1h",
              opening_hours="mon-sat 09:00-17:00; sun 10:00-17:00")]))
    op = to_dict(itin)["days"][0]["activities"][0]["opening"]
    assert op["per_day"] is True
    assert [r["hours_display"] for r in op["rules"]] == ["09:00–17:00", "10:00–17:00"]
    assert op["rules"][1]["day_runs"] == [["sunday", "sunday"]]


def test_the_validator_quotes_that_days_hours():
    """A Sunday visit outside the Sunday hours is reported against those, not
    against the union of every day's."""
    doc = {
        "travel_description": {"title": "T", "start_date": "2026-09-27"},
        "defaults": {"start_time": "09:00"},
        "days": [{"title": "D", "activities": [
            _poi("Museum", start_time="09:30", duration="1h",
                 opening_hours="mon-sat 09:00-17:00; sun 10:00-17:00")]}],
    }
    warnings = _findings(doc, "warning")
    assert any("falls outside the opening hours" in w for w in warnings)
    assert any("10:00–17:00" in w for w in warnings)


def test_a_weekday_visit_inside_its_own_hours_is_silent():
    doc = {
        "travel_description": {"title": "T", "start_date": "2026-09-24"},
        "defaults": {"start_time": "09:00"},
        "days": [{"title": "D", "activities": [
            _poi("Museum", start_time="09:30", duration="1h",
                 opening_hours="mon-sat 09:00-17:00; sun 10:00-17:00")]}],
    }
    assert not any("falls outside the opening hours" in w
                   for w in _findings(doc, "warning"))


# -- a transport leg's distance -------------------------------------------

def _transport_doc(**leg):
    base = {"start": "A", "end": "B", "start_date": "2026-06-01",
            "start_time": "09:00", "end_time": "10:00"}
    base.update(leg)
    return {
        "travel_description": {"title": "T", "start_date": "2026-06-01"},
        "days": [{"title": "D", "activities": [_poi("P", duration="1h")]}],
        "transport": [{"type": "taxi", "legs": [base]}],
    }


def test_a_leg_carries_its_own_distance():
    itin = Itinerary.from_dict(_transport_doc(distance_km=30))
    assert itin.legs[0].distance_km == 30.0


def test_a_leg_without_one_stays_none():
    assert Itinerary.from_dict(_transport_doc()).legs[0].distance_km is None


def test_the_leg_distance_reaches_the_viewer():
    itin = Itinerary.from_dict(_transport_doc(distance_km=30.5))
    assert to_dict(itin)["transports"][0]["legs"][0]["distance_km"] == 30.5
    assert to_dict(itin)["days"][0]["transports"][0]["distance_km"] == 30.5


def test_the_leg_distance_is_rounded_for_display_only():
    """Same display rounding as every other distance (0.1 km under 10 km), with
    the stored value untouched."""
    itin = Itinerary.from_dict(_transport_doc(distance_km=8.44))
    pdf = TravelPDF(itin)
    assert "8.4 km" in pdf._leg_info(itin.legs[0])
    assert itin.legs[0].distance_km == 8.44


def test_the_leg_distance_is_in_the_calendar_export():
    itin = Itinerary.from_dict(_transport_doc(distance_km=30))
    assert "Distance: 30 km" in _ics_text(itin)


# -- the four new categories ----------------------------------------------

@pytest.mark.parametrize("category", ["market", "spring", "canyon", "mountain pass"])
def test_the_new_categories_are_accepted(category):
    assert category in POI_CATEGORIES
    day = _day([_poi("P", duration="1h", category=category)])
    assert day.activities[0].category == category


@pytest.mark.parametrize("category,label", [
    ("market", "MARKET"), ("spring", "SPRING"), ("canyon", "CANYON"),
    # The badge is clipped to 14 characters, so this is the longest label that
    # still fits whole — a test pins it because the next one wouldn't.
    ("mountain pass", "MOUNTAIN PASS"),
])
def test_the_new_categories_fit_the_badge(category, label):
    itin = Itinerary.from_dict(_doc([_poi("P", duration="1h", category=category)]))
    pdf = TravelPDF(itin)
    assert pdf._badge_label(itin.days[0].activities[0]) == label


@pytest.mark.parametrize("category,label", [
    ("market", "MARCHÉ"), ("spring", "SOURCE"), ("canyon", "CANYON"),
    ("mountain pass", "COL"),
])
def test_the_new_categories_are_translated(category, label):
    itin = Itinerary.from_dict(_doc([_poi("P", duration="1h", category=category)]))
    pdf = TravelPDF(itin, lang="fr")
    assert pdf._badge_label(itin.days[0].activities[0]) == label


# -- the example, and the renderers end to end ----------------------------

def test_the_example_carries_all_five():
    """france.json exercises each one, so the rendered PDFs show them."""
    itin = Itinerary.from_dict(json.loads(FRANCE.read_text("utf-8")))
    acts = [a for day in itin.days for a in day.activities]
    nested = [n for a in acts for n in (getattr(a, "activities", None) or [])]
    every = acts + nested

    # a fee, and a stated free entry
    assert any(a.price == 22 for a in every)
    assert any(a.price == 0 for a in every)
    # a contact of each kind the viewer links
    contacts = {a.contact for a in every if a.contact}
    assert any("@" in c for c in contacts)
    assert any(c.startswith("+") for c in contacts)
    # per-weekday hours (the Louvre's Friday late opening)
    louvre = next(a for a in every if a.title == "Musée du Louvre")
    assert louvre.opening.per_day is True
    assert louvre.opening.hours_display_on(date(2026, 9, 4)) == "09:00–21:45"  # Fri
    assert louvre.opening.hours_display_on(date(2026, 9, 3)) == "09:00–18:00"  # Thu
    # a new category, and a leg distance
    assert any(getattr(a, "category", "") == "market" for a in every)
    assert any(leg.distance_km == 240 for leg in itin.legs)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("ink_saver", [False, True])
def test_the_example_still_builds(tmp_path, lang, ink_saver):
    src = FRANCE if lang == "en" else EXAMPLES / "france_fr.json"
    itin = Itinerary.from_dict(json.loads(src.read_text("utf-8")))
    out = tmp_path / "book.pdf"
    build_pdf(itin, str(out), lang=lang, ink_saver=ink_saver, maps=False)
    assert out.stat().st_size > 1000


def test_the_calendar_export_packs_the_fee_and_the_contact():
    itin = Itinerary.from_dict(_doc(
        [_poi("P", duration="1h", price=12, contact="112")]))
    ics = _ics_text(itin)
    assert "Price: €12" in ics
    assert "Contact: 112" in ics


def test_the_calendar_export_says_free_for_a_zero_fee():
    itin = Itinerary.from_dict(_doc([_poi("P", duration="1h", price=0)]))
    assert "Price: Free" in _ics_text(itin)


def test_the_calendar_export_names_the_days_hours():
    itin = Itinerary.from_dict(_doc(
        [_poi("P", duration="1h",
              opening_hours="mon-sat 09:00-17:00; sun 10:00-17:00")]))
    assert "Open: Mon–Sat 09:00–17:00, Sun 10:00–17:00" in _ics_text(itin)


# -- validation ------------------------------------------------------------

def test_an_undeclared_price_currency_is_an_error():
    doc = _doc([_poi("P", duration="1h", price=12, currency="JPY")],
               currency="EUR")
    assert any("price currency 'JPY' is neither the default currency" in e
               for e in _findings(doc))


def test_a_declared_secondary_currency_is_accepted():
    doc = _doc([_poi("P", duration="1h", price=1200, currency="KGS")],
               currency="EUR",
               secondary_currencies=[{"currency": "KGS", "change_rate": 100}])
    assert not any("price currency" in e for e in _findings(doc))


def test_a_nested_activitys_currency_is_checked_too():
    doc = _doc([{"type": "place", "name": "Area", "duration": "2h", "activities": [
        _poi("Inner", duration="1h", price=12, currency="JPY")]}], currency="EUR")
    assert any("price currency 'JPY'" in e for e in _findings(doc))


def test_a_non_numeric_price_is_an_error():
    doc = _doc([_poi("P", duration="1h", price="twelve")])
    assert any("'price' is invalid" in e for e in _findings(doc))


def test_a_non_numeric_leg_distance_is_an_error():
    doc = _transport_doc(distance_km="far")
    assert any("'distance_km' is invalid" in e for e in _findings(doc))


def test_the_three_new_fields_state_their_defaults_as_info():
    doc = _doc([_poi("P", duration="1h")])
    infos = _findings(doc, "info")
    for field in ("price", "currency", "contact"):
        assert any(f"'{field}' is missing" in i for i in infos), field
