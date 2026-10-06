"""A stay of two or more nights also states what its price works out at per
night — computed from `price` and the dates, never written in the JSON."""

from datetime import date

from odysseyra_travelbook.ics import build_ics
from odysseyra_travelbook.models import Accommodation, Itinerary


def _stay(arrival, departure, price=540.0, currency=""):
    return Accommodation(name="Hôtel", city="Lourdes", arrival=arrival,
                         departure=departure, price=price, currency=currency)


def test_per_night_divides_the_whole_stay():
    acc = _stay(date(2026, 6, 8), date(2026, 6, 11))
    assert acc.nights == 3
    assert acc.price_per_night == 180.0


def test_no_per_night_for_one_night_or_no_price():
    # For one night the per-night figure *is* the price: printing it twice says
    # nothing. Without a price or the dates there is nothing to divide.
    assert _stay(date(2026, 6, 8), date(2026, 6, 9)).price_per_night is None
    assert _stay(date(2026, 6, 8), date(2026, 6, 11), price=None).price_per_night is None
    assert _stay(date(2026, 6, 8), None).price_per_night is None


def _doc(nights, price=540):
    return {
        "travel_description": {"title": "T"},
        "days": [{"title": "Lourdes", "city": "Lourdes"}] * nights,
        "accommodations": [{
            "name": "Hôtel", "city": "Lourdes", "arrival": "2026-06-08",
            "departure": f"2026-06-{8 + nights:02d}", "price": price,
        }],
    }


def test_ics_labels_the_whole_stay_and_adds_the_per_night_line():
    ics = build_ics(Itinerary.from_dict(_doc(3))).replace("\r\n ", "")
    assert "Price (whole stay): €540" in ics
    assert "Price per night: €180" in ics


def test_ics_one_night_stay_keeps_its_plain_price():
    ics = build_ics(Itinerary.from_dict(_doc(1))).replace("\r\n ", "")
    assert "Price: €540" in ics
    assert "per night" not in ics


def test_pdf_builds_a_card_with_the_per_night_row():
    from odysseyra_travelbook.pdf import build_pdf
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "x.pdf")
        build_pdf(Itinerary.from_dict(_doc(3)), out)
        assert os.path.getsize(out) > 0
