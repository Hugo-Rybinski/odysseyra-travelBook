"""Shared scheduling primitives.

``Scheduled`` is the base for everything that lands on a day's timeline — an
:class:`~.activities.Activity`, a :class:`~.transport.Transport` leg or a
:class:`~.car_rental.CarRentalEvent` — carrying the clock times, duration and
per-end UTC offsets they all share. ``Stamp`` groups a date + clock time + UTC
offset into one value (used for the car rental's four booking/pick-up/drop-off
datetimes)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from .parsers import _format_duration, _parse_date, _parse_time, _parse_tz


@dataclass
class Scheduled:
    """Timeline fields shared by every activity, transport leg and car-rental
    event: a start/end clock time, a duration in minutes, and a UTC offset for
    each end (``None`` means "use the trip's default timezone")."""

    start_time: time | None = None
    end_time: time | None = None
    duration_min: int | None = None
    start_tz: int | None = None
    end_tz: int | None = None

    @property
    def time_range(self) -> str:
        if self.start_time and self.end_time:
            return f"{self.start_time:%H:%M} – {self.end_time:%H:%M}"
        if self.start_time:
            return f"{self.start_time:%H:%M}"
        return ""

    @property
    def duration_display(self) -> str:
        return _format_duration(self.duration_min)


@dataclass
class Stamp:
    """A date + clock time + UTC offset; any part may be absent."""

    date: date | None = None
    time: time | None = None
    tz: int | None = None

    @classmethod
    def from_dict(cls, d: dict, prefix: str) -> "Stamp":
        """Read the ``<prefix>_date`` / ``<prefix>_time`` / ``<prefix>_tz`` keys
        out of ``d`` into a stamp (e.g. prefix ``"pickup"``)."""
        return cls(
            date=_parse_date(d.get(f"{prefix}_date")),
            time=_parse_time(d.get(f"{prefix}_time")),
            tz=_parse_tz(d.get(f"{prefix}_tz")),
        )
