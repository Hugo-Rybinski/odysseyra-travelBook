"""Tests for the transport booking/leg split.

One booking (a PNR, a price, a link) may move you several times, so what is
reserved once lives on the booking and what moves once lives on its ``legs``.
The model tests for the shape itself sit in ``test_odysseyra.py`` next to the
other model tests; this file covers what the split changed *downstream* — the
resolved dict, the day pages, the transport page, the maps and the calendar
export — plus the multi-leg example itself.
"""

import json
from datetime import date
from pathlib import Path

from odysseyra_travelbook import Itinerary, build_ics, to_dict
from odysseyra_travelbook.pdf import TravelPDF

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
FRANCE = EXAMPLES / "france.json"
PYRENEES = EXAMPLES / "pyrenees.json"


def _doc(**booking):
    """A 3-day trip carrying one booking, whose fields the caller supplies."""
    return {
        "travel_description": {"title": "T"},
        "days": [{"title": f"d{n}", "date": f"2026-06-0{n}", "activities": []}
                 for n in (1, 2, 3)],
        "transport": [booking],
    }


def _round_trip(**extra):
    return Itinerary.from_dict(_doc(
        type="plane", booking_number="PNR1", booking_source="Air France",
        website="https://af.example", booking_link="https://af.example/PNR1",
        status="confirmed", price=1200, currency="USD", paid="paid",
        legs=[
            {"start": "JFK", "end": "CDG", "start_date": "2026-06-01",
             "start_time": "22:10", "duration": "7h35",
             "description": "Seat 24A."},
            {"start": "CDG", "end": "JFK", "start_date": "2026-06-03",
             "start_time": "10:00", "end_time": "13:00"},
        ],
        **extra))


# --- the resolved dict ------------------------------------------------------

def test_the_top_level_transports_are_bookings_holding_their_legs():
    d = to_dict(_round_trip())
    booking = d["transports"][0]
    # no `name` given, so the heading is the route through every leg
    assert booking["name"] == ""
    assert booking["title"] == "JFK → CDG → JFK"
    assert booking["route_chain"] == "JFK → CDG → JFK"
    assert booking["booking_number"] == "PNR1"
    assert [leg["title"] for leg in booking["legs"]] == ["JFK → CDG", "CDG → JFK"]
    # the booking has no times or places of its own — those are the legs'
    assert "start_time" not in booking and "start" not in booking
    assert booking["start_date"] == "2026-06-01"    # earliest departure
    assert booking["end_date"] == "2026-06-03"      # latest arrival


def test_a_days_transports_are_legs_enriched_with_their_booking():
    """What the day renderers consume: the leg, plus everything about the
    reservation it would otherwise have to look up."""
    days = to_dict(_round_trip())["days"]
    assert [len(day["transports"]) for day in days] == [1, 0, 1]
    out, back = days[0]["transports"][0], days[2]["transports"][0]
    assert (out["title"], back["title"]) == ("JFK → CDG", "CDG → JFK")
    for i, leg in enumerate((out, back), start=1):
        assert leg["type"] == "plane"
        assert leg["booking_number"] == "PNR1"
        assert leg["booking_source"] == "Air France"
        assert leg["website"] == "https://af.example"
        assert leg["booking_link"] == "https://af.example/PNR1"
        assert leg["status"] == "confirmed"
        assert (leg["leg_index"], leg["leg_count"]) == (i, 2)
    # …including the price, which is the *booking's* — hence one, not two fares
    assert out["price"]["amount"] == back["price"]["amount"] == 1200


def test_only_the_leg_that_moves_that_day_lands_on_it():
    d = to_dict(_round_trip())
    assert d["days"][1]["transports"] == [], "nothing departs on day 2"


def test_the_overnight_leg_alone_fills_the_night():
    # A leg crossing midnight is the night's "accommodation"; its siblings aren't.
    it = Itinerary.from_dict(_doc(type="train", legs=[
        {"start": "A", "end": "B", "start_date": "2026-06-01",
         "start_time": "22:10", "end_time": "06:45"},
        {"start": "B", "end": "C", "start_date": "2026-06-03",
         "start_time": "09:00", "duration": "1h"},
    ]))
    night = it.night_transport(date(2026, 6, 1))
    assert night is not None and night.title == "A → B"
    assert it.night_transport(date(2026, 6, 3)) is None
    assert to_dict(it)["days"][0]["night_transport"]["title"] == "A → B"


# --- the renderers ----------------------------------------------------------

def _record_drawn(pdf) -> list[str]:
    """Capture, in order, the strings a card actually *draws*.

    Measurement passes are skipped: the card measures its text (`dry_run=True`)
    to compute its height before drawing anything, so counting those would both
    duplicate strings and scramble the order."""
    drawn: list[str] = []
    for name in ("cell", "multi_cell"):
        original = getattr(TravelPDF, name)

        def spy(self, *a, _orig=original, **kw):
            if not kw.get("dry_run"):
                text = next((x for x in a if isinstance(x, str)), kw.get("txt", ""))
                if text:
                    drawn.append(text)
            return _orig(self, *a, **kw)

        setattr(pdf, name, spy.__get__(pdf, TravelPDF))
    return drawn

def test_the_transport_card_draws_every_leg():
    """The page groups by booking: one card, one block per leg — so a two-leg
    booking prints both routes and its reference/price once."""
    pdf = TravelPDF(_round_trip(), "en", False, "google")
    pdf.add_page()
    drawn = _record_drawn(pdf)
    pdf._transport_card(pdf.itinerary.transports[0])
    text = " | ".join(drawn)
    assert "JFK → CDG" in text and "CDG → JFK" in text
    assert text.count("Ref PNR1") == 1, "the reference belongs to the booking"
    assert "Seat 24A." in text, "each leg keeps its own note"


def test_the_day_row_reads_the_booking_through_the_leg():
    # A day's row shows a leg with no booking around it, so its identity line
    # carries both halves — unlike the transport page, which splits them.
    pdf = TravelPDF(_round_trip(), "en", False, "google")
    line = pdf._transport_booking(pdf.itinerary.legs[0])
    assert "Ref PNR1" in line
    assert "Booked via Air France" in line


def test_the_flight_number_is_the_legs_own():
    it = Itinerary.from_dict(_doc(type="plane", booking_number="PNR1", legs=[
        {"start": "A", "end": "B", "start_date": "2026-06-01",
         "start_time": "09:00", "duration": "1h", "flight_number": "AF1"},
        {"start": "B", "end": "C", "start_date": "2026-06-01",
         "start_time": "12:00", "duration": "1h", "flight_number": "AF2"},
    ]))
    pdf = TravelPDF(it, "en", False, "google")
    first, second = it.legs
    assert "Flight AF1" in pdf._transport_booking(first)
    assert "Flight AF2" in pdf._transport_booking(second)


def test_every_leg_of_a_booking_is_drawn_on_its_own_day_map():
    from odysseyra_travelbook.maps.build import day_legs

    it = Itinerary.from_dict(_doc(type="plane", legs=[
        {"start": "A", "end": "B", "start_date": "2026-06-01",
         "start_time": "09:00", "duration": "1h",
         "start_coordinate": {"lat": 40.0, "long": -70.0},
         "end_coordinate": {"lat": 49.0, "long": 2.5}},
        {"start": "B", "end": "C", "start_date": "2026-06-03",
         "start_time": "09:00", "duration": "1h",
         "start_coordinate": {"lat": 49.0, "long": 2.5},
         "end_coordinate": {"lat": 43.6, "long": 1.4}},
    ]))
    assert day_legs(it.days[0], it) == [[(40.0, -70.0), (49.0, 2.5)]]
    assert day_legs(it.days[1], it) == []
    assert day_legs(it.days[2], it) == [[(49.0, 2.5), (43.6, 1.4)]]


# --- the calendar export ----------------------------------------------------

def _events(ics: str) -> list[str]:
    return ics.split("BEGIN:VEVENT")[1:]


def test_the_ics_emits_one_event_per_leg():
    ics = build_ics(_round_trip(), now=None)
    legs = [e for e in _events(ics) if "SUMMARY:✈️ Plane:" in e]
    assert len(legs) == 2
    assert any("JFK → CDG" in e for e in legs)
    assert any("CDG → JFK" in e for e in legs)
    # the booking's reference rides on both
    assert all("Booking number: PNR1" in e for e in legs)


def test_the_ics_says_a_multi_leg_price_is_the_whole_bookings():
    two = build_ics(_round_trip(), now=None)
    assert "Price (whole booking):" in two
    one = build_ics(Itinerary.from_dict(_doc(
        type="train", price=45, legs=[
            {"start": "A", "end": "B", "start_date": "2026-06-01",
             "start_time": "09:00", "duration": "1h"}])), now=None)
    assert "Price:" in one and "Price (whole booking):" not in one


# --- the examples -----------------------------------------------------------

def test_france_carries_the_multi_leg_booking():
    """france.json is the multi-leg example: one round-trip PNR with a
    connection on the way home, so both renderers exercise the grouped card."""
    it = Itinerary.from_json_file(FRANCE)
    flights = next(t for t in it.transports if t.type == "plane")
    assert len(flights.legs) == 3
    # an explicit name heads the card; the chain is what it would fall back to
    assert flights.name == "Round trip New York ↔ France"
    assert flights.title == flights.name
    assert flights.route_chain == ("New York JFK → Paris CDG → Toulouse-Blagnac"
                                   " → Paris CDG → New York JFK")
    assert flights.description.startswith("One booking both ways")
    assert [leg.flight_number for leg in flights.legs] == ["AF23", "AF7590", "AF6"]
    # the two return legs sit on the same (last) day
    last = it.days[-1]
    assert [leg.title for leg in it.transports_on(last.date)] == [
        "Toulouse-Blagnac → Paris CDG", "Paris CDG → New York JFK"]
    # one price for the reservation, and every leg reports it
    assert flights.price == 1410
    assert all(leg.price == 1410 for leg in flights.legs)


def test_pyrenees_keeps_the_single_leg_shape():
    """The single-leg example: three one-hop bookings. Two are unnamed, so their
    heading is the route chain (identical to the leg's own title); the night
    train is named, which is what keeps a one-leg card from saying its route
    twice."""
    it = Itinerary.from_json_file(PYRENEES)
    assert [len(t.legs) for t in it.transports] == [1, 1, 1]
    for booking in it.transports:
        leg = booking.legs[0]
        assert (leg.leg_index, leg.leg_count) == (1, 1)
        assert booking.route_chain == leg.title
        assert booking.title == (booking.name or leg.title)
    plane, train, night = it.transports
    assert (plane.name, train.name) == ("", "")
    assert night.name == "Night train back to Paris"
    assert night.description.startswith("Non-refundable fare")


def test_the_fragments_reassemble_the_multi_level_shape():
    from odysseyra_travelbook.stitch import aggregate

    stitched = aggregate(EXAMPLES / "pyrenees_pieces")
    expected = json.loads(PYRENEES.read_text(encoding="utf-8"))
    assert stitched["transport"] == expected["transport"]


# --- the booking's own name and note ----------------------------------------

def test_the_name_defaults_to_the_route_through_every_leg():
    """No `name` → the chain the user asked for: "Airport 1 → Airport 2 → …",
    a connection named once, a break kept."""
    connecting = Itinerary.from_dict(_doc(type="plane", legs=[
        {"start": "A1", "end": "A2", "start_date": "2026-06-01",
         "start_time": "08:00", "duration": "1h"},
        {"start": "A2", "end": "A3", "start_date": "2026-06-01",
         "start_time": "11:00", "duration": "1h"},
        {"start": "A3", "end": "A4", "start_date": "2026-06-02",
         "start_time": "09:00", "duration": "1h"},
    ])).transports[0]
    assert connecting.route_chain == "A1 → A2 → A3 → A4"
    assert connecting.title == connecting.route_chain

    # A leg starting somewhere else is a break, not a connection: keep both ends,
    # or the booking would read as going somewhere it doesn't.
    broken = Itinerary.from_dict(_doc(type="plane", legs=[
        {"start": "JFK", "end": "CDG", "start_date": "2026-06-01",
         "start_time": "08:00", "duration": "1h"},
        {"start": "TLS", "end": "JFK", "start_date": "2026-06-03",
         "start_time": "09:00", "duration": "1h"},
    ])).transports[0]
    assert broken.route_chain == "JFK → CDG → TLS → JFK"


def test_an_explicit_name_wins_and_the_chain_stays_available():
    booking = _round_trip(name="Round trip New York ↔ Paris").transports[0]
    assert booking.title == "Round trip New York ↔ Paris"
    assert booking.route_chain == "JFK → CDG → JFK", "still computed"
    d = to_dict(booking.legs[0].transport and _round_trip(
        name="Round trip New York ↔ Paris"))["transports"][0]
    assert (d["name"], d["title"]) == ("Round trip New York ↔ Paris",
                                       "Round trip New York ↔ Paris")


def test_the_booking_note_is_separate_from_a_legs_note():
    """Two levels, two questions: the reservation's terms vs this hop's seat.
    Neither is copied onto the other."""
    it = _round_trip(description="One bag each, skis extra.")
    booking = it.transports[0]
    assert booking.description == "One bag each, skis extra."
    assert booking.legs[0].description == "Seat 24A."
    assert booking.legs[1].description == "", "a leg without a note has none"

    d = to_dict(it)
    assert d["transports"][0]["description"] == "One bag each, skis extra."
    # the day's leg carries its own note only — the booking's belongs to the
    # transport section, not to a row about one hop
    day_leg = d["days"][0]["transports"][0]
    assert day_leg["description"] == "Seat 24A."
    assert "One bag each" not in json.dumps(d["days"])


def test_the_card_states_the_reservation_before_its_legs():
    """The layout requirement, pinned: every booking-level line is drawn before
    the first leg's route, so shared info can't read as one hop's."""
    it = _round_trip(name="Round trip New York ↔ Paris",
                     description="One bag each, skis extra.")
    pdf = TravelPDF(it, "en", False, "google")
    pdf.add_page()
    drawn = _record_drawn(pdf)
    pdf._transport_card(it.transports[0])

    def at(fragment):
        return next(i for i, text in enumerate(drawn) if fragment in text)

    first_leg = at("JFK → CDG")
    for shared in ("Round trip New York ↔ Paris", "Ref PNR1",
                   "One bag each, skis extra.", "$1200", "Website"):
        assert at(shared) < first_leg, f"{shared!r} must precede the legs"
    # the legs follow in travel order, each badged just before its route
    assert first_leg < at("CDG → JFK")
    assert drawn[first_leg - 1] == "Leg 1"
    assert drawn[at("CDG → JFK") - 1] == "Leg 2"


def test_the_ics_keeps_the_two_notes_apart():
    ics = build_ics(_round_trip(description="One bag each."), now=None)
    out = next(e for e in _events(ics) if "JFK → CDG" in e)
    body = out.replace("\r\n ", "")
    assert "Description: Seat 24A." in body       # the leg's own
    assert "Booking note: One bag each." in body  # the reservation's


def _single(**booking):
    """A one-leg booking (the common case), with its own note."""
    return Itinerary.from_dict(_doc(
        type="train", booking_number="IC-1", booking_source="SNCF",
        legs=[{"start": "Montréjeau", "end": "Paris Austerlitz",
               "start_date": "2026-06-01", "start_time": "22:10",
               "end_time": "06:45", "train_number": "IC 3711",
               "description": "Couchette 4, upper berths."}],
        **booking))


def test_a_one_leg_card_is_flat_and_never_repeats_its_route():
    """A booking with one leg has nothing to tell apart, so there's no rule, no
    inset and no leg number — and the route is printed once."""
    it = _single(description="Non-refundable fare.")
    pdf = TravelPDF(it, "en", False, "google")
    pdf.add_page()
    drawn = _record_drawn(pdf)
    pdf._transport_card(it.transports[0])

    route = "Montréjeau → Paris Austerlitz"
    assert drawn.count(route) == 1, "the heading is the route"
    assert not [text for text in drawn if text.startswith("Leg ")], \
        "a lone leg gets no badge"
    # both notes and the identity line are still there, booking note first
    text = " | ".join(drawn)
    assert "Non-refundable fare." in text
    assert "Couchette 4, upper berths." in text
    assert text.index("Non-refundable fare.") < text.index("Couchette 4")
    assert "Train IC 3711" in text and "Ref IC-1" in text


def test_a_named_one_leg_card_shows_the_route_under_its_name():
    # Named differently, the route is no longer a repeat — so it gets its line.
    it = _single(name="Night train back to Paris")
    pdf = TravelPDF(it, "en", False, "google")
    pdf.add_page()
    drawn = _record_drawn(pdf)
    pdf._transport_card(it.transports[0])
    assert drawn.index("Night train back to Paris") < drawn.index(
        "Montréjeau → Paris Austerlitz")
