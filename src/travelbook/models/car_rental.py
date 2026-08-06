"""The CarRental type and its time-zone resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from .parsers import (
    ItineraryError,
    _add_minutes,
    _format_duration,
    _parse_date,
    _parse_duration,
    _parse_paid,
    _parse_time,
    _parse_tz,
)


CAR_TYPES = ("regular", "small", "suv", "4x4")
# Canonical stored value → the label shown in the PDF (so "suv" prints "SUV"
# and "4x4" is not mangled by a naive ``.upper()``).
_CAR_TYPE_LABELS = {"regular": "Regular", "small": "Small", "suv": "SUV", "4x4": "4x4"}


@dataclass
class CarRental:
    """A rental-car booking (a top-level trip section).

    The booking runs from a start to an end datetime; the pick-up and drop-off
    datetimes must fall inside that window (checked by the validator). Each of
    the four times carries an optional UTC offset that falls back to the trip's
    global ``timezone``. The drop-off location defaults to the pick-up one.
    """

    kind = "car_rental"
    booking_start_date: date | None = None
    booking_start_time: time | None = None
    booking_end_date: date | None = None
    booking_end_time: time | None = None
    pickup_date: date | None = None
    pickup_time: time | None = None
    dropoff_date: date | None = None
    dropoff_time: time | None = None
    booking_start_tz: int | None = None
    booking_end_tz: int | None = None
    pickup_tz: int | None = None
    dropoff_tz: int | None = None
    pickup_location: str = ""
    dropoff_location: str = ""  # defaults to pickup_location
    company: str = ""
    booking_number: str = ""
    price: str = ""
    paid: bool | None = None  # None = no badge
    car_type: str = "regular"
    car_model: str = ""
    contact: str = ""
    additional_drivers: int = 0
    pickup_duration_min: int | None = None
    dropoff_duration_min: int | None = None

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

    def _event(self, kind, d, t, tz, loc, dur) -> "CarRentalEvent":
        end = _add_minutes(t, dur) if (t is not None and dur) else None
        return CarRentalEvent(kind, self, d, t, end, tz, tz, loc, dur)

    def pickup_event(self) -> "CarRentalEvent":
        return self._event("car_pickup", self.pickup_date, self.pickup_time,
                           self.pickup_tz, self.pickup_location,
                           self.pickup_duration_min)

    def dropoff_event(self) -> "CarRentalEvent":
        return self._event("car_dropoff", self.dropoff_date, self.dropoff_time,
                           self.dropoff_tz, self.dropoff_location,
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
        drivers = d.get("additional_drivers", 0)
        if drivers in (None, ""):
            drivers = 0
        try:
            drivers = int(drivers)
        except (TypeError, ValueError) as exc:
            raise ItineraryError(
                f"additional_drivers must be a whole number, got {drivers!r}"
            ) from exc
        price = d.get("price", "")
        pickup_location = str(d.get("pickup_location", ""))
        return cls(
            booking_start_date=_parse_date(d.get("booking_start_date")),
            booking_start_time=_parse_time(d.get("booking_start_time")),
            booking_end_date=_parse_date(d.get("booking_end_date")),
            booking_end_time=_parse_time(d.get("booking_end_time")),
            pickup_date=_parse_date(d.get("pickup_date")),
            pickup_time=_parse_time(d.get("pickup_time")),
            dropoff_date=_parse_date(d.get("dropoff_date")),
            dropoff_time=_parse_time(d.get("dropoff_time")),
            booking_start_tz=_parse_tz(d.get("booking_start_tz")),
            booking_end_tz=_parse_tz(d.get("booking_end_tz")),
            pickup_tz=_parse_tz(d.get("pickup_tz")),
            dropoff_tz=_parse_tz(d.get("dropoff_tz")),
            pickup_location=pickup_location,
            dropoff_location=str(d.get("dropoff_location", "")) or pickup_location,
            company=str(d.get("company", "")),
            booking_number=str(d.get("booking_number", "")),
            price="" if price == "" or price is None else str(price),
            paid=_parse_paid(d.get("paid")),
            car_type=ctype,
            car_model=str(d.get("car_model", "")),
            contact=str(d.get("contact", "")),
            additional_drivers=drivers,
            pickup_duration_min=_parse_duration(d.get("pickup_duration")),
            dropoff_duration_min=_parse_duration(d.get("dropoff_duration")),
        )


@dataclass
class CarRentalEvent:
    """A car pick-up or drop-off, woven into a day's itinerary timeline.

    Carries the scheduling fields the day renderer and validator need
    (``start_time`` for sorting, ``end_time`` from the pick-up/drop-off
    duration) plus a back-reference to the owning :class:`CarRental`.
    """

    kind: str  # "car_pickup" | "car_dropoff"
    rental: CarRental
    date: date | None
    start_time: time | None
    end_time: time | None
    start_tz: int | None
    end_tz: int | None
    location: str
    duration_min: int | None

    @property
    def duration_display(self) -> str:
        return _format_duration(self.duration_min)


def resolve_car_rental(cr: CarRental, default_tz: int | None) -> None:
    """Fill each unset UTC offset with the trip default. Mutates ``cr``."""
    if cr.booking_start_tz is None:
        cr.booking_start_tz = default_tz
    if cr.booking_end_tz is None:
        cr.booking_end_tz = default_tz
    if cr.pickup_tz is None:
        cr.pickup_tz = default_tz
    if cr.dropoff_tz is None:
        cr.dropoff_tz = default_tz
