"""The Accommodation type."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .parsers import ItineraryError, _parse_bool, _parse_date


ACCOMMODATION_TYPES = ("hotel", "camping", "b&b", "other")


@dataclass
class Accommodation:
    """A place to stay for one or more nights (a top-level trip section)."""

    name: str
    arrival: date | None = None
    departure: date | None = None
    city: str = ""  # town, for the day-by-day overview
    type: str = "hotel"
    address: str = ""
    contact: str = ""
    booking_source: str = ""  # e.g. "Booking.com", "Hotel website"
    price: str = ""
    paid_online: bool = False  # True → "Paid online", False → "To pay"
    breakfast_included: bool = False

    @property
    def nights(self) -> int | None:
        if self.arrival and self.departure:
            return (self.departure - self.arrival).days
        return None

    @property
    def date_range(self) -> str:
        if self.arrival and self.departure:
            return f"{self.arrival:%b %d} → {self.departure:%b %d}"
        if self.arrival:
            return f"from {self.arrival:%b %d}"
        return ""

    def covers(self, day: date | None) -> bool:
        """True if you sleep here on the night of ``day``."""
        if day is None or self.arrival is None:
            return False
        if self.departure is not None:
            return self.arrival <= day < self.departure
        return self.arrival == day

    def night_of(self, day: date | None) -> int | None:
        """1-based index of ``day`` within this stay (None if not covered)."""
        if not self.covers(day):
            return None
        return (day - self.arrival).days + 1

    @classmethod
    def from_dict(cls, d: dict) -> "Accommodation":
        if not isinstance(d, dict):
            raise ItineraryError("Each accommodation must be an object")
        for key in ("name", "arrival", "departure", "city"):
            if key not in d:
                raise ItineraryError(f"An accommodation needs a '{key}'")
        atype = str(d.get("type", "hotel")).strip().lower()
        if atype not in ACCOMMODATION_TYPES:
            raise ItineraryError(
                "accommodation type must be one of: "
                f"{', '.join(ACCOMMODATION_TYPES)} (got {d.get('type')!r})"
            )
        price = d.get("price", "")
        return cls(
            name=str(d["name"]),
            arrival=_parse_date(d.get("arrival")),
            departure=_parse_date(d.get("departure")),
            city=str(d.get("city", "")),
            type=atype,
            address=str(d.get("address", "")),
            contact=str(d.get("contact", "")),
            booking_source=str(d.get("booking_source", "")),
            price="" if price == "" or price is None else str(price),
            paid_online=_parse_bool(d.get("paid_online", False)),
            breakfast_included=_parse_bool(d.get("breakfast_included", False)),
        )
