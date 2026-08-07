"""The CarRental type and its time-zone resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .geo import Coordinate, _parse_coordinate
from .parsers import (
    ItineraryError,
    _add_minutes,
    _format_duration,
    _parse_currency,
    _parse_duration,
    _parse_paid,
    _parse_price,
)
from .scheduling import Scheduled, Stamp


CAR_TYPES = ("regular", "small", "suv", "4x4")
# Canonical stored value → the label shown in the PDF (so "suv" prints "SUV"
# and "4x4" is not mangled by a naive ``.upper()``).
_CAR_TYPE_LABELS = {"regular": "Regular", "small": "Small", "suv": "SUV", "4x4": "4x4"}


@dataclass
class CarRental:
    """A rental-car booking (a top-level trip section).

    The booking runs from a start to an end datetime; the pick-up and drop-off
    datetimes must fall inside that window (checked by the validator). Each of
    the four datetimes is a :class:`~.scheduling.Stamp` whose UTC offset falls
    back to the trip's global ``timezone``. The drop-off location defaults to
    the pick-up one.
    """

    kind = "car_rental"
    booking_start: Stamp = field(default_factory=Stamp)
    booking_end: Stamp = field(default_factory=Stamp)
    pickup: Stamp = field(default_factory=Stamp)
    dropoff: Stamp = field(default_factory=Stamp)
    pickup_location: str = ""
    dropoff_location: str = ""  # defaults to pickup_location
    company: str = ""
    booking_number: str = ""
    status: str = ""  # "" | "booked" | "confirmed"
    price: float | None = None
    currency: str = ""  # "" → the trip's default currency
    paid: bool | None = None  # None = no badge
    car_type: str = "regular"
    car_model: str = ""
    contact: str = ""
    additional_drivers: int = 0
    pickup_duration_min: int | None = None
    dropoff_duration_min: int | None = None
    coordinate: Coordinate | None = None  # optional single label point
    pickup_coordinate: Coordinate | None = None
    dropoff_coordinate: Coordinate | None = None

    @property
    def car_type_label(self) -> str:
        return _CAR_TYPE_LABELS.get(self.car_type, self.car_type.title())

    @property
    def title(self) -> str:
        return self.company or self.car_model or "Car rental"

    @property
    def pickup_duration_display(self) -> str:
        return _format_duration(self.pickup_duration_min)

    @property
    def dropoff_duration_display(self) -> str:
        return _format_duration(self.dropoff_duration_min)

    def _event(self, kind, stamp: Stamp, loc, dur) -> "CarRentalEvent":
        t = stamp.time
        end = _add_minutes(t, dur) if (t is not None and dur) else None
        return CarRentalEvent(kind=kind, rental=self, date=stamp.date,
                              start_time=t, end_time=end,
                              start_tz=stamp.tz, end_tz=stamp.tz,
                              location=loc, duration_min=dur)

    def pickup_event(self) -> "CarRentalEvent":
        return self._event("car_pickup", self.pickup, self.pickup_location,
                           self.pickup_duration_min)

    def dropoff_event(self) -> "CarRentalEvent":
        return self._event("car_dropoff", self.dropoff, self.dropoff_location,
                           self.dropoff_duration_min)

    @classmethod
    def from_dict(cls, d: dict) -> "CarRental":
        if not isinstance(d, dict):
            raise ItineraryError("Each car rental must be an object")
        for key in (
            "booking_start_date", "booking_start_time",
            "booking_end_date", "booking_end_time",
            "pickup_date", "pickup_time",
            "dropoff_date", "dropoff_time",
            "pickup_location",
        ):
            if key not in d or d[key] in (None, ""):
                raise ItineraryError(f"A car rental needs a '{key}'")
        ctype = str(d.get("car_type", "regular")).strip().lower()
        if ctype not in CAR_TYPES:
            raise ItineraryError(
                "car type must be one of: "
                f"{', '.join(CAR_TYPES)} (got {d.get('car_type')!r})"
            )
        status = str(d.get("status", "")).strip().lower()
        if status and status not in ("booked", "confirmed"):
            raise ItineraryError(
                f"car rental status must be 'booked' or 'confirmed', got {status!r}"
            )
        drivers = d.get("additional_drivers", 0)
        if drivers in (None, ""):
            drivers = 0
        try:
            drivers = int(drivers)
        except (TypeError, ValueError) as exc:
            raise ItineraryError(
                f"additional_drivers must be a whole number, got {drivers!r}"
            ) from exc
        pickup_location = str(d.get("pickup_location", ""))
        return cls(
            booking_start=Stamp.from_dict(d, "booking_start"),
            booking_end=Stamp.from_dict(d, "booking_end"),
            pickup=Stamp.from_dict(d, "pickup"),
            dropoff=Stamp.from_dict(d, "dropoff"),
            pickup_location=pickup_location,
            dropoff_location=str(d.get("dropoff_location", "")) or pickup_location,
            company=str(d.get("company", "")),
            booking_number=str(d.get("booking_number", "")),
            status=status,
            price=_parse_price(d.get("price")),
            currency=_parse_currency(d.get("currency")),
            paid=_parse_paid(d.get("paid")),
            car_type=ctype,
            car_model=str(d.get("car_model", "")),
            contact=str(d.get("contact", "")),
            additional_drivers=drivers,
            pickup_duration_min=_parse_duration(d.get("pickup_duration")),
            dropoff_duration_min=_parse_duration(d.get("dropoff_duration")),
            coordinate=_parse_coordinate(d.get("coordinate")),
            pickup_coordinate=_parse_coordinate(d.get("pickup_coordinate"), "pickup_coordinate"),
            dropoff_coordinate=_parse_coordinate(d.get("dropoff_coordinate"), "dropoff_coordinate"),
        )


@dataclass
class CarRentalEvent(Scheduled):
    """A car pick-up or drop-off, woven into a day's itinerary timeline.

    Carries the shared :class:`~.scheduling.Scheduled` fields the day renderer
    and validator need (``start_time`` for sorting, ``end_time`` from the
    pick-up/drop-off duration) plus a back-reference to the owning
    :class:`CarRental`.
    """

    kind: str = ""  # "car_pickup" | "car_dropoff"
    rental: CarRental | None = None
    date: date | None = None
    location: str = ""


def resolve_car_rental(cr: CarRental, default_tz: int | None) -> None:
    """Fill each unset UTC offset with the trip default. Mutates ``cr``."""
    for stamp in (cr.booking_start, cr.booking_end, cr.pickup, cr.dropoff):
        if stamp.tz is None:
            stamp.tz = default_tz
