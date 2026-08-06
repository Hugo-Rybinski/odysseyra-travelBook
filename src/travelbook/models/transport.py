"""The Transport leg type and its time-zone-aware scheduling resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

from .geo import Coordinate, _parse_coordinate
from .parsers import (
    ItineraryError,
    _format_duration,
    _min_to_time,
    _parse_currency,
    _parse_date,
    _parse_duration,
    _parse_paid,
    _parse_price,
    _parse_time,
    _parse_tz,
    _tmin,
)


TRANSPORT_TYPES = ("plane", "train", "bus", "taxi", "ferry", "other")


@dataclass
class Transport:
    """A travel leg (plane, train, bus, …) — a top-level trip section.

    Times are clock times, each with an optional UTC offset (``start_tz`` /
    ``end_tz``) that falls back to the trip's global ``timezone``. Given any two
    of ``start_time`` / ``end_time`` / ``duration``, the third is inferred
    (across time zones when they differ).
    """

    kind = "transport"
    type: str = "other"
    start: str = ""
    end: str = ""
    start_date: date | None = None  # departure date; slots the leg into that day
    end_date: date | None = None  # arrival date (inferred for overnight legs)
    start_time: time | None = None
    end_time: time | None = None
    start_tz: int | None = None
    end_tz: int | None = None
    duration_min: int | None = None
    flight_number: str = ""  # planes only
    train_number: str = ""  # trains only
    booking_number: str = ""
    booking_source: str = ""
    status: str = ""  # "" | "booked" | "confirmed"
    price: float | None = None
    currency: str = ""  # "" → the trip's default currency
    paid: bool | None = None  # None = no badge
    coordinate: Coordinate | None = None  # optional single label point
    start_coordinate: Coordinate | None = None  # departure point
    end_coordinate: Coordinate | None = None  # arrival point

    @property
    def title(self) -> str:
        if self.start and self.end:
            return f"{self.start} → {self.end}"
        return self.start or self.end or (self.type.title() if self.type else "Transport")

    @property
    def duration_display(self) -> str:
        return _format_duration(self.duration_min)

    @property
    def overnight(self) -> bool:
        """True if the leg spans a night (arrives on a later day)."""
        return (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date > self.start_date
        )

    @property
    def end_day_offset(self) -> int:
        """How many days after departure the leg arrives (0 = same day)."""
        if self.start_date is None or self.end_date is None:
            return 0
        return (self.end_date - self.start_date).days

    @classmethod
    def from_dict(cls, d: dict) -> "Transport":
        if not isinstance(d, dict):
            raise ItineraryError("Each transport must be an object")
        for key in ("start", "end", "start_time"):
            if key not in d:
                raise ItineraryError(f"A 'transport' needs a '{key}'")
        if "start_date" not in d and "date" not in d:
            raise ItineraryError("A 'transport' needs a 'start_date'")
        ttype = str(d.get("type", "other")).strip().lower()
        if ttype not in TRANSPORT_TYPES:
            raise ItineraryError(
                "transport type must be one of: "
                f"{', '.join(TRANSPORT_TYPES)} (got {d.get('type')!r})"
            )
        status = str(d.get("status", "")).strip().lower()
        if status and status not in ("booked", "confirmed"):
            raise ItineraryError(
                f"transport status must be 'booked' or 'confirmed', got {status!r}"
            )
        return cls(
            type=ttype,
            start=str(d.get("start", "")),
            end=str(d.get("end", "")),
            start_date=_parse_date(d.get("start_date", d.get("date"))),
            end_date=_parse_date(d.get("end_date")),
            start_time=_parse_time(d.get("start_time")),
            end_time=_parse_time(d.get("end_time")),
            start_tz=_parse_tz(d.get("start_tz", d.get("start_timezone"))),
            end_tz=_parse_tz(d.get("end_tz", d.get("end_timezone"))),
            duration_min=_parse_duration(d.get("duration")),
            flight_number=str(d.get("flight_number", "")),
            train_number=str(d.get("train_number", "")),
            booking_number=str(d.get("booking_number", "")),
            booking_source=str(d.get("booking_source", "")),
            status=status,
            price=_parse_price(d.get("price")),
            currency=_parse_currency(d.get("currency")),
            paid=_parse_paid(d.get("paid")),
            coordinate=_parse_coordinate(d.get("coordinate")),
            start_coordinate=_parse_coordinate(d.get("start_coordinate"), "start_coordinate"),
            end_coordinate=_parse_coordinate(d.get("end_coordinate"), "end_coordinate"),
        )


def resolve_transport(t: Transport, default_tz: int | None) -> None:
    """Fill in whichever of start/end/duration was left out, honoring the time
    zones (each falling back to ``default_tz``). Mutates ``t`` in place."""
    so = t.start_tz if t.start_tz is not None else default_tz
    eo = t.end_tz if t.end_tz is not None else default_tz
    t.start_tz, t.end_tz = so, eo
    so0, eo0 = so or 0, eo or 0
    s, e, d = _tmin(t.start_time), _tmin(t.end_time), t.duration_min
    if s is not None and d is not None and e is None:
        t.end_time = _min_to_time((s - so0) + d + eo0)
    elif s is not None and e is not None and d is None:
        t.duration_min = ((e - eo0) - (s - so0)) % 1440
    elif e is not None and d is not None and s is None:
        t.start_time = _min_to_time((e - eo0) - d + so0)

    # Infer the arrival date: a leg whose local arrival clock is earlier than
    # its departure has rolled past midnight (an overnight leg).
    if t.start_date is not None and t.end_date is None:
        crosses = (
            t.start_time is not None
            and t.end_time is not None
            and t.end_time < t.start_time
        )
        t.end_date = t.start_date + timedelta(days=1) if crosses else t.start_date

