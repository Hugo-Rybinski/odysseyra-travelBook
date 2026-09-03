"""Transport: a booking and its legs, plus tz-aware scheduling resolution.

The split mirrors what a ticket actually is. One **booking** (a PNR, a price, a
reservation link) may move you several times — an outbound and a return flight,
a flight with a connection, a rail ticket routed via a change — so the booking
carries what is bought once (``type``, ``name``, ``booking_number``,
``booking_source``, ``website``, ``booking_link``, ``status``, ``description``,
``price``/``currency``/``paid``) and each :class:`TransportLeg` carries what
moves once (where from, where to, when, the flight/train number of *that* hop,
its own note and coordinates).

Both levels carry a ``description``, answering different questions: the
booking's is about the reservation (a baggage allowance, a fare condition), a
leg's is about that hop (a seat, a terminal). Neither is proxied onto the other.

``legs`` is required and must hold at least one entry: a single-hop booking is a
one-leg booking, not a special case, so every consumer walks legs and there is
no second shape to support.

A leg reads its booking's shared fields as if they were its own
(``leg.type``, ``leg.booking_number``, …) through the proxy properties below —
the same enrichment ``serialize.py`` bakes into the resolved leg for the day
pages. That is what lets the day itinerary, the maps, the ICS export and the
validator treat a leg as the self-contained thing they always treated a
transport as.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .geo import Coordinate, _parse_coordinate
from .parsers import (
    ItineraryError,
    _min_to_time,
    _parse_currency,
    _parse_date,
    _parse_duration,
    _parse_float,
    _parse_paid,
    _parse_price,
    _parse_time,
    _parse_tz,
    _tmin,
)
from .scheduling import Scheduled


TRANSPORT_TYPES = ("plane", "train", "bus", "taxi", "ferry", "other")


@dataclass
class TransportLeg(Scheduled):
    """One hop of a booking: a departure, an arrival, and the times between.

    Times are clock times, each with an optional UTC offset (``start_tz`` /
    ``end_tz``) that falls back to the trip's global ``timezone``. Given any two
    of ``start_time`` / ``end_time`` / ``duration``, the third is inferred
    (across time zones when they differ).

    ``transport`` points back at the booking this leg belongs to, so the shared
    reservation fields are readable straight off the leg (see the proxies
    below). It is set by :meth:`Transport.from_dict` and is only ``None`` for a
    leg built on its own in a test.
    """

    kind = "transport"
    start: str = ""
    end: str = ""
    start_date: date | None = None  # departure date; slots the leg into that day
    end_date: date | None = None  # arrival date (inferred for overnight legs)
    flight_number: str = ""  # planes only
    train_number: str = ""  # trains only
    # How far this hop covers. A road's legs have always carried one; a transport
    # leg's is just as much part of the hop (an airport transfer is "30 km /
    # 35 min", and a ferry's crossing is a distance), and it is per **leg**
    # rather than per booking for the same reason the times are. Rounded for
    # display only, like every other distance in the book (`format_km`).
    distance_km: float | None = None
    # A short note for whatever the fields above don't carry (seat, terminal,
    # baggage allowance…). Prose, drawn under the leg's booking line. Per-leg:
    # an outbound and a return rarely share a seat.
    description: str = ""
    coordinate: Coordinate | None = None  # optional single label point
    start_coordinate: Coordinate | None = None  # departure point
    end_coordinate: Coordinate | None = None  # arrival point
    # Set by the owning booking; excluded from repr/compare so a leg still
    # prints (and compares) as its own data rather than dragging the booking —
    # and so the back-reference can't recurse.
    transport: "Transport | None" = field(default=None, repr=False, compare=False)

    # --- the booking's shared fields, readable off the leg --------------------
    # A leg is what the day pages, the maps and the calendar export deal with,
    # and each of them needs the type badge or the reference next to the route.
    # Reading through rather than copying keeps one source of truth.

    @property
    def type(self) -> str:
        return self.transport.type if self.transport else "other"

    @property
    def booking_number(self) -> str:
        return self.transport.booking_number if self.transport else ""

    @property
    def booking_source(self) -> str:
        return self.transport.booking_source if self.transport else ""

    @property
    def website(self) -> str:
        return self.transport.website if self.transport else ""

    @property
    def booking_link(self) -> str:
        return self.transport.booking_link if self.transport else ""

    @property
    def status(self) -> str:
        return self.transport.status if self.transport else ""

    @property
    def price(self) -> float | None:
        """The **booking's** price — it covers every leg, so a renderer showing
        it per leg would print it once per hop. Only the transport page does."""
        return self.transport.price if self.transport else None

    @property
    def currency(self) -> str:
        return self.transport.currency if self.transport else ""

    @property
    def paid(self) -> bool | None:
        return self.transport.paid if self.transport else None

    @property
    def leg_index(self) -> int:
        """1-based position within the booking (1 for a single-leg booking)."""
        if self.transport is None:
            return 1
        for i, leg in enumerate(self.transport.legs, start=1):
            if leg is self:
                return i
        return 1

    @property
    def leg_count(self) -> int:
        return len(self.transport.legs) if self.transport else 1

    # --- the leg's own derived values ----------------------------------------

    @property
    def title(self) -> str:
        if self.start and self.end:
            return f"{self.start} → {self.end}"
        return self.start or self.end or (self.type.title() if self.type else "Transport")

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
    def from_dict(cls, d: dict) -> "TransportLeg":
        if not isinstance(d, dict):
            raise ItineraryError("Each transport leg must be an object")
        for key in ("start", "end", "start_time", "start_date"):
            if key not in d:
                raise ItineraryError(f"A transport leg needs a '{key}'")
        return cls(
            start=str(d.get("start", "")),
            end=str(d.get("end", "")),
            start_date=_parse_date(d.get("start_date")),
            end_date=_parse_date(d.get("end_date")),
            start_time=_parse_time(d.get("start_time")),
            end_time=_parse_time(d.get("end_time")),
            start_tz=_parse_tz(d.get("start_tz")),
            end_tz=_parse_tz(d.get("end_tz")),
            duration_min=_parse_duration(d.get("duration")),
            flight_number=str(d.get("flight_number", "")),
            train_number=str(d.get("train_number", "")),
            distance_km=_parse_float(d.get("distance_km"),
                                     "transport leg distance_km"),
            description=str(d.get("description", "")),
            coordinate=_parse_coordinate(d.get("coordinate")),
            start_coordinate=_parse_coordinate(d.get("start_coordinate"),
                                              "start_coordinate"),
            end_coordinate=_parse_coordinate(d.get("end_coordinate"),
                                             "end_coordinate"),
        )


@dataclass
class Transport:
    """One booking (plane, train, bus, …) and the legs it moves you over.

    Not a :class:`Scheduled`: a booking has no single pair of times — its legs
    do. Its dates are derived from them (:attr:`start_date` / :attr:`end_date`).
    """

    kind = "transport_booking"
    type: str = "other"
    # What to call the booking as a whole ("Round trip New York ↔ France").
    # Optional: `title` falls back to the route chain through its legs.
    name: str = ""
    booking_number: str = ""
    booking_source: str = ""
    website: str = ""  # the carrier's website
    booking_link: str = ""  # direct link to this reservation
    status: str = ""  # "" | "booked" | "confirmed"
    # A note about the *whole* reservation (a baggage allowance, a fare
    # condition, a check-in window) — as opposed to a leg's own `description`,
    # which is about that hop (a seat, a terminal).
    description: str = ""
    price: float | None = None  # for the whole booking, every leg included
    currency: str = ""  # "" → the trip's default currency
    paid: bool | None = None  # None = no badge
    legs: list[TransportLeg] = field(default_factory=list)

    @property
    def route_chain(self) -> str:
        """Every place the booking touches, in travel order:
        ``Airport 1 → Airport 2 → Airport 3 → Airport 4``.

        A connection collapses (leg 2 starting where leg 1 ended is named once),
        while a break does not — a round trip via a different outbound airport
        reads through all of them, since dropping either end would misdescribe
        the booking."""
        places: list[str] = []
        for leg in self.legs:
            for place in (leg.start, leg.end):
                if place and place != (places[-1] if places else None):
                    places.append(place)
        # Same separator a leg's own title uses, so the two read as one family.
        return " → ".join(places)

    @property
    def title(self) -> str:
        """What to show as the booking's heading: its `name` when given, else the
        route chain through its legs."""
        if self.name:
            return self.name
        return self.route_chain or (self.type.title() if self.type else "Transport")

    @property
    def start_date(self) -> date | None:
        """The earliest departure across the legs."""
        dates = [leg.start_date for leg in self.legs if leg.start_date]
        return min(dates) if dates else None

    @property
    def end_date(self) -> date | None:
        """The latest arrival across the legs."""
        dates = [d for leg in self.legs
                 for d in (leg.end_date, leg.start_date) if d]
        return max(dates) if dates else None

    @classmethod
    def from_dict(cls, d: dict) -> "Transport":
        if not isinstance(d, dict):
            raise ItineraryError("Each transport must be an object")
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
        legs_data = d.get("legs")
        if legs_data is None:
            raise ItineraryError(
                "A 'transport' needs a 'legs' array — one entry per hop, and a "
                "single-hop booking is a one-entry array"
            )
        if not isinstance(legs_data, list):
            raise ItineraryError("transport 'legs' must be an array")
        if not legs_data:
            raise ItineraryError("A 'transport' needs at least one leg in 'legs'")
        transport = cls(
            type=ttype,
            name=str(d.get("name", "")),
            booking_number=str(d.get("booking_number", "")),
            booking_source=str(d.get("booking_source", "")),
            website=str(d.get("website", "")),
            booking_link=str(d.get("booking_link", "")),
            status=status,
            description=str(d.get("description", "")),
            price=_parse_price(d.get("price")),
            currency=_parse_currency(d.get("currency")),
            paid=_parse_paid(d.get("paid")),
            legs=[TransportLeg.from_dict(leg) for leg in legs_data],
        )
        for leg in transport.legs:
            leg.transport = transport
        return transport


def resolve_transport(leg: TransportLeg, default_tz: int | None) -> None:
    """Fill in whichever of start/end/duration the leg left out, honoring the
    time zones (each falling back to ``default_tz``). Mutates ``leg`` in place."""
    so = leg.start_tz if leg.start_tz is not None else default_tz
    eo = leg.end_tz if leg.end_tz is not None else default_tz
    leg.start_tz, leg.end_tz = so, eo
    so0, eo0 = so or 0, eo or 0
    s, e, d = _tmin(leg.start_time), _tmin(leg.end_time), leg.duration_min
    if s is not None and d is not None and e is None:
        leg.end_time = _min_to_time((s - so0) + d + eo0)
    elif s is not None and e is not None and d is None:
        leg.duration_min = ((e - eo0) - (s - so0)) % 1440
    elif e is not None and d is not None and s is None:
        leg.start_time = _min_to_time((e - eo0) - d + so0)

    # Infer the arrival date: a leg whose local arrival clock is earlier than
    # its departure has rolled past midnight (an overnight leg).
    if leg.start_date is not None and leg.end_date is None:
        crosses = (
            leg.start_time is not None
            and leg.end_time is not None
            and leg.end_time < leg.start_time
        )
        leg.end_date = leg.start_date + timedelta(days=1) if crosses else leg.start_date
