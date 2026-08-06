"""The Day and Itinerary aggregates that tie the pieces together."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from pathlib import Path

from .accommodation import Accommodation
from .activities import Activity, activity_from_dict, schedule_activities
from .car_rental import CarRental, CarRentalEvent, resolve_car_rental
from .parsers import (
    ItineraryError,
    _parse_date,
    _parse_duration,
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
        defaults = data.get("defaults", data.get("default")) or {}

        if "title" not in desc:
            raise ItineraryError("Itinerary needs a 'title'")
        days_data = data.get("days", [])
        if not isinstance(days_data, list) or not days_data:
            raise ItineraryError("Itinerary needs a non-empty 'days' array")

        default_start = _parse_time(
            defaults.get("start_time", data.get("default_start_time"))
        ) or time(8, 0)
        default_end = _parse_time(defaults.get("end_time", data.get("default_end_time")))
        default_buffer = _parse_duration(
            defaults.get("buffer", data.get("default_buffer"))
        ) or 0
        default_tz = _parse_tz(defaults.get("timezone", data.get("timezone")))
        if default_tz is None:
            default_tz = 0  # GMT / UTC+0
        breakfast_until = _parse_time(defaults.get("breakfast_until")) or time(10, 0)
        lunch_until = _parse_time(defaults.get("lunch_until")) or time(16, 0)
        meal_duration = _parse_duration(defaults.get("meal_duration")) or 0
        transport_data = data.get("transport", data.get("transports", []))
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
                if act.kind == "meal":
                    act.breakfast_until = breakfast_until
                    act.lunch_until = lunch_until
                    if act.duration_min is None and act.end_time is None:
                        act.duration_min = meal_duration
            day.activities = schedule_activities(
                day.activities, default_start, default_buffer
            )
        return itinerary

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
                seeds += [c.pickup_date for c in self.car_rentals if c.pickup_date]
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
            dates += [d for d in (c.booking_start_date, c.booking_end_date,
                                  c.pickup_date, c.dropoff_date) if d]
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
            if cr.pickup_date == day:
                events.append(cr.pickup_event())
            if cr.dropoff_date == day:
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
