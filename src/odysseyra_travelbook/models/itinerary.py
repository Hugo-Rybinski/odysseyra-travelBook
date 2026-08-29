"""The Day and Itinerary aggregates that tie the pieces together."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from pathlib import Path

from .accommodation import Accommodation
from .activities import (
    Activity,
    activity_from_dict,
    resolve_meal_categories,
    schedule_activities,
)
from .car_rental import CarRental, CarRentalEvent, resolve_car_rental
from .currency import SecondaryCurrency, to_default
from .parsers import (
    ItineraryError,
    _parse_bool,
    _parse_date,
    _parse_duration,
    _parse_float,
    _parse_time,
    _parse_tz,
)
from .transport import Transport, resolve_transport


@dataclass
class Day:
    title: str
    date: date | None = None
    city: str = ""
    description: str = ""
    activities: list[Activity] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Day":
        if "title" not in data:
            raise ItineraryError("Each day needs a 'title'")
        return cls(
            title=str(data["title"]),
            date=_parse_date(data.get("date")),
            city=str(data.get("city", "")),
            description=str(data.get("description", "")),
            activities=[activity_from_dict(a) for a in data.get("activities", [])],
        )


@dataclass
class Itinerary:
    title: str
    subtitle: str = ""
    summary: str = ""
    cover_color: str = "#1f4e5f"
    default_start_time: time = time(8, 0)
    default_end_time: time | None = None
    default_buffer_min: int = 0
    default_timezone: int = 0  # GMT / UTC+0
    default_meal_breakfast_until: time = time(10, 0)
    default_meal_lunch_until: time = time(16, 0)
    default_meal_duration_min: int = 0
    # Clock times used to place an accommodation on a calendar (ICS export): each
    # night runs from ``accommodation_start_time`` that evening to
    # ``accommodation_end_time`` (midnight by default — the end of that night).
    default_accommodation_start_time: time = time(22, 0)
    default_accommodation_end_time: time = time(0, 0)
    default_currency: str = "EUR"  # all prices are in this unless they say otherwise
    secondary_currencies: list[SecondaryCurrency] = field(default_factory=list)
    include_maps_in_render: bool = False  # draw a per-day map (opt-in)
    infer_coordinates_from_address: bool = False  # geocode missing coordinates
    inference_countries: list[str] = field(default_factory=list)  # ISO codes; [] = any
    show_moon_phase: bool = False  # show the night's moon phase in "tonight" (opt-in)
    start_date: date | None = None  # inferred from the trip's earliest date
    end_date: date | None = None  # inferred from the trip's latest date
    days: list[Day] = field(default_factory=list)
    accommodations: list[Accommodation] = field(default_factory=list)
    transports: list[Transport] = field(default_factory=list)
    car_rentals: list[CarRental] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Itinerary":
        if not isinstance(data, dict):
            raise ItineraryError("Top-level JSON must be an object")
        # Descriptive fields live under "travel_description" and default config
        # under "defaults" (legacy alias: "default"); both fall back to
        # top-level keys for compatibility.
        desc = {**data, **(data.get("travel_description") or {})}
        defaults = data.get("defaults") or {}

        if "title" not in desc:
            raise ItineraryError("Itinerary needs a 'title'")
        days_data = data.get("days", [])
        if not isinstance(days_data, list) or not days_data:
            raise ItineraryError("Itinerary needs a non-empty 'days' array")

        default_start = _parse_time(defaults.get("start_time")) or time(8, 0)
        default_end = _parse_time(defaults.get("end_time"))
        default_buffer = _parse_duration(defaults.get("buffer")) or 0
        default_tz = _parse_tz(defaults.get("timezone", data.get("timezone")))
        if default_tz is None:
            default_tz = 0  # GMT / UTC+0
        breakfast_until = _parse_time(defaults.get("breakfast_until")) or time(10, 0)
        lunch_until = _parse_time(defaults.get("lunch_until")) or time(16, 0)
        meal_duration = _parse_duration(defaults.get("meal_duration")) or 0
        accommodation_start = (_parse_time(defaults.get("accommodation_start_time"))
                               or time(22, 0))
        accommodation_end = _parse_time(defaults.get("accommodation_end_time"))
        if accommodation_end is None:
            accommodation_end = time(0, 0)
        default_currency = str(defaults.get("currency", "EUR")).strip().upper() or "EUR"
        secondary_currencies = cls._parse_secondary_currencies(
            defaults.get("secondary_currencies")
        )
        include_maps = _parse_bool(defaults.get("include_maps_in_render", False))
        infer_coords = _parse_bool(defaults.get("infer_coordinates_from_address", False))
        show_moon = _parse_bool(defaults.get("show_moon_phase", False))
        inference_countries = cls._parse_inference_countries(
            defaults.get("inference_countries")
        )
        transport_data = data.get("transport", [])
        itinerary = cls(
            title=str(desc["title"]),
            subtitle=str(desc.get("subtitle", "")),
            summary=str(desc.get("summary", "")),
            cover_color=str(desc.get("cover_color", "#1f4e5f")),
            default_start_time=default_start,
            default_end_time=default_end,
            default_buffer_min=default_buffer,
            default_timezone=default_tz,
            default_meal_breakfast_until=breakfast_until,
            default_meal_lunch_until=lunch_until,
            default_meal_duration_min=meal_duration,
            default_accommodation_start_time=accommodation_start,
            default_accommodation_end_time=accommodation_end,
            default_currency=default_currency,
            secondary_currencies=secondary_currencies,
            include_maps_in_render=include_maps,
            infer_coordinates_from_address=infer_coords,
            inference_countries=inference_countries,
            show_moon_phase=show_moon,
            start_date=_parse_date(desc.get("start_date")),
            end_date=_parse_date(desc.get("end_date")),
            days=[Day.from_dict(d) for d in days_data],
            accommodations=[
                Accommodation.from_dict(a) for a in data.get("accommodations", [])
            ],
            transports=[Transport.from_dict(t) for t in transport_data],
            car_rentals=[
                CarRental.from_dict(c) for c in data.get("car_rentals", [])
            ],
        )
        for transport in itinerary.transports:
            resolve_transport(transport, default_tz)
        for car_rental in itinerary.car_rentals:
            resolve_car_rental(car_rental, default_tz)
        itinerary._infer_dates()
        for day in itinerary.days:
            for act in day.activities:
                if (act.kind == "meal" and act.duration_min is None
                        and act.end_time is None):
                    act.duration_min = meal_duration
            day.activities = schedule_activities(
                day.activities, default_start, default_buffer
            )
            # Resolve each meal's category now the timeline (and so each meal's
            # start time) is settled, using the trip's meal thresholds.
            resolve_meal_categories(day.activities, breakfast_until, lunch_until)
        return itinerary

    @staticmethod
    def _parse_secondary_currencies(raw) -> list[SecondaryCurrency]:
        """Build the ``secondary_currencies`` list from the defaults object.
        Each entry is ``{"currency": <ISO code>, "change_rate": <float>}`` with
        the rate given as units of that currency per one unit of the default."""
        if raw in (None, ""):
            return []
        if not isinstance(raw, list):
            raise ItineraryError("'secondary_currencies' must be an array")
        result = []
        for entry in raw:
            if not isinstance(entry, dict):
                raise ItineraryError("Each secondary currency must be an object")
            code = str(entry.get("currency", "")).strip().upper()
            rate = _parse_float(entry.get("change_rate"), "change_rate")
            if not code or rate is None:
                raise ItineraryError(
                    "A secondary currency needs a 'currency' and a 'change_rate'"
                )
            if rate <= 0:
                raise ItineraryError("change_rate must be a positive number")
            result.append(SecondaryCurrency(code, rate))
        return result

    @staticmethod
    def _parse_inference_countries(raw) -> list[str]:
        """ISO-3166-1 alpha-2 country codes constraining geocoding (upper-cased).
        Accepts a list, or a single string; empty means "any country"."""
        if raw in (None, ""):
            return []
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            raise ItineraryError("'inference_countries' must be an array of codes")
        codes = []
        for entry in raw:
            code = str(entry).strip().upper()
            if len(code) != 2 or not code.isalpha():
                raise ItineraryError(
                    f"inference_countries code {entry!r} must be a 2-letter ISO "
                    "country code like 'FR'"
                )
            codes.append(code)
        return codes

    def in_default(self, amount: float, code: str = "") -> float | None:
        """Convert ``amount`` (in currency ``code``, or the default when empty)
        into the trip's default currency; ``None`` if ``code`` has no rate."""
        return to_default(amount, code, self.default_currency,
                          self.secondary_currencies)

    def _infer_dates(self) -> None:
        """Fill missing day dates from the trip start + the day index, then set
        ``start_date`` / ``end_date`` (unless given manually) to the earliest /
        latest date across days, transport and accommodation."""
        # Day-date anchor: the manual trip start if given, else the first day's
        # date (explicit dates adjusted by index), else earliest transport/stay.
        if self.start_date is not None:
            day0 = self.start_date
        else:
            explicit = [(i, d.date) for i, d in enumerate(self.days) if d.date]
            if explicit:
                day0 = min(d - timedelta(days=i) for i, d in explicit)
            else:
                seeds = [t.start_date for t in self.transports if t.start_date]
                seeds += [a.arrival for a in self.accommodations if a.arrival]
                seeds += [c.pickup.date for c in self.car_rentals if c.pickup.date]
                day0 = min(seeds) if seeds else None
        if day0 is not None:
            for i, day in enumerate(self.days):
                if day.date is None:
                    day.date = day0 + timedelta(days=i)

        dates = [d.date for d in self.days if d.date]
        for t in self.transports:
            dates += [d for d in (t.start_date, t.end_date) if d]
        for a in self.accommodations:
            dates += [d for d in (a.arrival, a.departure) if d]
        for c in self.car_rentals:
            dates += [d for d in (c.booking_start.date, c.booking_end.date,
                                  c.pickup.date, c.dropoff.date) if d]
        if self.start_date is None:
            self.start_date = min(dates) if dates else None
        if self.end_date is None:
            self.end_date = max(dates) if dates else None

    @classmethod
    def from_json_file(cls, path: str | Path) -> "Itinerary":
        path = Path(path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ItineraryError(f"File not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ItineraryError(f"Invalid JSON in {path}: {exc}") from exc
        return cls.from_dict(raw)

    @property
    def date_range(self) -> str:
        if self.start_date and self.end_date:
            return f"{self.start_date:%b %d, %Y} – {self.end_date:%b %d, %Y}"
        if self.start_date:
            return f"{self.start_date:%b %d, %Y}"
        return ""

    def stay_for(self, day: date | None) -> Accommodation | None:
        """The accommodation you sleep at on the night of ``day`` (or None)."""
        for acc in self.accommodations:
            if acc.covers(day):
                return acc
        return None

    def transports_on(self, day: date | None) -> list[Transport]:
        """Transport legs departing on ``day``."""
        if day is None:
            return []
        return [t for t in self.transports if t.start_date == day]

    def car_events_on(self, day: date | None) -> list[CarRentalEvent]:
        """Car-rental pick-up / drop-off events falling on ``day``."""
        if day is None:
            return []
        events = []
        for cr in self.car_rentals:
            if cr.pickup.date == day:
                events.append(cr.pickup_event())
            if cr.dropoff.date == day:
                events.append(cr.dropoff_event())
        return events

    def night_transport(self, day: date | None) -> Transport | None:
        """An overnight leg departing on ``day`` — you sleep aboard it."""
        if day is None:
            return None
        for t in self.transports:
            if t.overnight and t.start_date == day:
                return t
        return None
