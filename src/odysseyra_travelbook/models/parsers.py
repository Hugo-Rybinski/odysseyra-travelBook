"""Scalar parsers and the shared ItineraryError."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta


class ItineraryError(ValueError):
    """Raised when the JSON does not describe a valid itinerary."""


# -- scalar parsers -----------------------------------------------------

_ANCHOR = date(2000, 1, 1)  # arbitrary date for time arithmetic


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError) as exc:
        raise ItineraryError(f"Invalid date {value!r}, expected YYYY-MM-DD") from exc


def _parse_time(value) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    try:
        return datetime.strptime(str(value).strip(), "%H:%M").time()
    except (ValueError, TypeError) as exc:
        raise ItineraryError(f"Invalid time {value!r}, expected HH:MM") from exc


def _parse_float(value, name: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError) as exc:
        raise ItineraryError(f"{name} must be a number, got {value!r}") from exc


def _parse_price(value, name: str = "price") -> float | None:
    """A price amount as a float. Numbers pass straight through; strings are
    tolerated for legacy data (a leading/trailing currency symbol, ISO code,
    thousands separators or spaces are stripped before parsing)."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ItineraryError(f"{name} must be a number, got {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    s = re.sub(r"[€$£¥]", "", str(value))
    s = re.sub(r"[A-Za-z]{3}", "", s)  # a stray ISO code
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError as exc:
        raise ItineraryError(f"{name} must be a number, got {value!r}") from exc


def _parse_currency(value) -> str:
    """An ISO currency code, upper-cased ('' when unset → the trip default)."""
    if value is None or value == "":
        return ""
    return str(value).strip().upper()


def _parse_duration(value) -> int | None:
    """Parse a human duration into whole minutes.

    Accepts ``"1h30"``, ``"2h"``, ``"1h30m"``, ``"50 min"``, ``"90m"``,
    ``"1:30"`` and bare numbers (minutes).
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):  # avoid treating True/False as ints
        raise ItineraryError(f"Could not parse duration {value!r}")
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().lower()
    clock = re.fullmatch(r"(\d+):(\d{2})", s)
    if clock:
        return int(clock.group(1)) * 60 + int(clock.group(2))
    hours = re.search(r"(\d+)\s*h", s)
    if hours:
        total = int(hours.group(1)) * 60
        rest = re.search(r"(\d+)", s[hours.end():])
        if rest:
            total += int(rest.group(1))
        return total
    mins = re.search(r"(\d+)", s)
    if mins:
        return int(mins.group(1))
    raise ItineraryError(f"Could not parse duration {value!r}")


def _format_duration(minutes: int | None) -> str:
    if not minutes:
        return ""
    if minutes < 60:
        return f"{minutes} min"
    h, m = divmod(minutes, 60)
    return f"{h}h{m:02d}" if m else f"{h}h"


# -- display rounding for the two measured figures a book prints --------------
# Both are estimates: a distance is routed or read off a guidebook, an ascent is
# accumulated from a GPS altimeter. Printing every digit of one claims a
# precision nobody has, and the precision a reader can *use* falls off with the
# magnitude — 8.4 km of walking is a different afternoon from 8.7, while 341 km
# of driving and 342 are the same day behind the wheel. So the step coarsens as
# the number grows. The viewer computes the same thing in `render/format.ts`
# (`roundKm` / `roundElevation`) — keep the two in step.


def round_km(value: float) -> float:
    """A distance in km snapped to 0.1 below 10, 0.5 up to 20, whole km above."""
    step = 0.1 if value < 10 else (0.5 if value <= 20 else 1.0)
    return round(round(value / step) * step, 1)


def round_elevation(value: float) -> int:
    """A climb in metres snapped to 5 below 100, and to 10 from there up."""
    step = 5 if value < 100 else 10
    return int(round(value / step) * step)


def format_km(value) -> str:
    """``"8.4 km"`` — a rounded distance with its unit, ``""`` when unset."""
    return "" if value is None else f"{round_km(value):g} km"


def format_elevation(value) -> str:
    """``"780 m"`` — a rounded climb with its unit, ``""`` when unset. The ``+``
    / ``↑`` a caller may put in front of it is the caller's."""
    return "" if value is None else f"{round_elevation(value)} m"


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y")
    return bool(value)


def _parse_route(value, default: str = "loop") -> str:
    if not value:
        return default
    norm = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if norm == "loop":
        return "loop"
    if norm in ("back_and_forth", "out_and_back", "there_and_back"):
        return "back_and_forth"
    if norm in ("one_way", "oneway"):
        return "one_way"
    raise ItineraryError(
        "hike route must be 'loop', 'back_and_forth' or 'one_way', "
        f"got {value!r}"
    )


def _parse_tz(value) -> int | None:
    """Parse a UTC offset into minutes. Accepts '+02:00', '+0200', 'UTC-3',
    'GMT+1', '+2', 'Z'."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value) * 60  # bare number = hours
    s = str(value).strip().upper()
    if s in ("Z", "UTC", "GMT"):
        return 0
    s = s.replace("UTC", "").replace("GMT", "").strip()
    m = re.fullmatch(r"([+-])(\d{1,2})(?::?(\d{2}))?", s)
    if not m:
        raise ItineraryError(
            f"Invalid timezone {value!r}, expected e.g. '+02:00' or 'UTC-3'"
        )
    sign = 1 if m.group(1) == "+" else -1
    return sign * (int(m.group(2)) * 60 + int(m.group(3) or 0))


def _format_tz(offset: int | None) -> str:
    if offset is None:
        return ""
    sign = "+" if offset >= 0 else "-"
    h, m = divmod(abs(offset), 60)
    return f"UTC{sign}{h}" + (f":{m:02d}" if m else "")


def _parse_paid(value) -> bool | None:
    """Tri-state payment flag: True (paid), False (to pay), None (unset)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("paid", "paid online", "true", "yes", "1"):
        return True
    if s in ("to pay", "to_pay", "topay", "unpaid", "false", "no", "0"):
        return False
    raise ItineraryError(f"paid must be 'paid' or 'to pay', got {value!r}")


def _tmin(t: time | None) -> int | None:
    return None if t is None else t.hour * 60 + t.minute


def _min_to_time(m: int) -> time:
    m %= 1440
    return time(m // 60, m % 60)


def _add_minutes(t: time, minutes: int) -> time:
    return (datetime.combine(_ANCHOR, t) + timedelta(minutes=minutes)).time()


def _diff_minutes(start: time, end: time) -> int:
    s = datetime.combine(_ANCHOR, start)
    e = datetime.combine(_ANCHOR, end)
    if e < s:  # spills past midnight
        e += timedelta(days=1)
    return int((e - s).total_seconds() // 60)
