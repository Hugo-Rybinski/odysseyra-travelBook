"""A point of interest's opening days and hours.

Two optional source fields, both compact strings so a guidebook line
("Tue–Sun, 9.30–12.30 & 14.00–18.00") transcribes without being taken apart
into an object:

* ``opening_days`` — ``"tue-sun"`` / ``"monday-friday, sunday"``; single days
  and/or ranges, comma-separated, case-insensitive, full names or three-letter
  abbreviations. A range may wrap the week (``"sat-mon"`` = Sat, Sun, Mon).
  Absent means *every day* — not "unknown", because a sight with no stated
  closing day is one you can turn up at.
* ``opening_hours`` — ``"09:30-18:00"`` / ``"09:30-12:30, 14:00-18:00"``; one or
  more ``HH:MM-HH:MM`` ranges, so the midday closure guidebooks are full of
  survives as two ranges instead of being flattened into one long one. A range
  whose close is *before* its open crosses midnight (``"18:00-02:00"``).

Both reduce to one :class:`Opening`, which is what the renderers draw and what
the validator asks whether a visit falls inside (:meth:`Opening.closed_on` /
:meth:`Opening.covers`). It carries no display strings beyond the
language-neutral ``hours_display``: weekday names have to be localized, so each
renderer formats ``day_runs`` itself (``lang.fmt_weekday_runs`` on the Python
side, ``fmtWeekdayRuns`` in the viewer).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, time

from .parsers import ItineraryError, _parse_time, _tmin

# The canonical weekday keys, Monday first — exactly the lowercased English
# weekday names ``lang/dates.py`` formats from (a test pins the two together).
WEEKDAYS = (
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
)

_DAYS_EXPECTED = ("weekday names like 'tue-sun', 'monday, thursday' or "
                  "'mon-fri, sun'")
_HOURS_EXPECTED = "time ranges like '09:30-18:00' or '09:30-12:30, 14:00-18:00'"

# A range separator: a plain hyphen, or the en/em dash a line pasted from a book
# carries.
_DASH = re.compile(r"\s*[-–—]\s*")


def _weekday_index(token: str) -> int:
    """The 0-6 index of one weekday token — a full name, or any unambiguous
    prefix of at least three letters (``mon``, ``tues``, ``thurs``)."""
    key = token.strip().lower().rstrip(".")
    hits = [i for i, name in enumerate(WEEKDAYS) if name.startswith(key)]
    if len(key) < 3 or len(hits) != 1:
        raise ItineraryError(f"unknown weekday {token.strip()!r}")
    return hits[0]


def _parse_opening_days(value) -> tuple[str, ...]:
    """``"tue-sun"`` → the canonical names it covers, in week order. ``()`` when
    nothing is given (open every day)."""
    if value is None or value == "":
        return ()
    text = str(value).strip()
    if not text:
        return ()
    found: set[int] = set()
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        bounds = _DASH.split(token)
        try:
            if len(bounds) == 1:
                found.add(_weekday_index(bounds[0]))
            elif len(bounds) == 2:
                lo, hi = _weekday_index(bounds[0]), _weekday_index(bounds[1])
                # A range may wrap the week — "sat-mon" is Sat, Sun, Mon.
                span = (hi - lo) % 7
                found.update((lo + step) % 7 for step in range(span + 1))
            else:
                raise ItineraryError("not a day or a range")
        except ItineraryError as exc:
            # The offending token isn't named: the whole value is short and is
            # echoed, and one message per field is one entry to translate (the
            # house style of ``Invalid date {value}, expected …``).
            raise ItineraryError(
                f"Invalid opening_days {value!r}, expected {_DAYS_EXPECTED}"
            ) from exc
    return tuple(WEEKDAYS[i] for i in sorted(found))


def _parse_opening_hours(value) -> tuple[tuple[time, time], ...]:
    """``"09:30-12:30, 14:00-18:00"`` → the ``(open, close)`` pairs, in the order
    given. ``()`` when nothing is given (open all day)."""
    if value is None or value == "":
        return ()
    text = str(value).strip()
    if not text:
        return ()
    ranges: list[tuple[time, time]] = []
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        bounds = _DASH.split(token)
        if len(bounds) != 2 or not all(b.strip() for b in bounds):
            raise ItineraryError(
                f"Invalid opening_hours {value!r}, expected {_HOURS_EXPECTED}")
        try:
            opens, closes = _parse_time(bounds[0]), _parse_time(bounds[1])
        except ItineraryError as exc:
            raise ItineraryError(
                f"Invalid opening_hours {value!r}, expected {_HOURS_EXPECTED}"
            ) from exc
        if opens == closes:
            raise ItineraryError(
                f"opening_hours range {token!r} opens and closes at the same "
                "time — give the closing time, or drop the range")
        ranges.append((opens, closes))
    return tuple(ranges)


@dataclass(frozen=True)
class Opening:
    """When a point of interest is open. Either half may be empty: no ``days``
    means every day, no ``hours`` means all day — so an empty ``Opening`` says
    nothing and is never built (:func:`parse_opening` returns ``None``)."""

    days: tuple[str, ...] = ()
    hours: tuple[tuple[time, time], ...] = ()

    @property
    def day_runs(self) -> tuple[tuple[str, str], ...]:
        """``days`` folded back into consecutive runs, as ``(first, last)`` name
        pairs — ``("monday", "wednesday"), ("friday", "friday")`` for Mon-Wed +
        Fri. A single day is a run of one, so a renderer has just the one shape
        to format.

        Runs **wrap the week**: a place closed on Tuesdays folds to the one run
        ``Wed–Mon``, which is how opening days are printed, rather than to
        ``Mon, Wed–Sun``, which splits the message in two at a boundary nobody
        cares about. A wrapping run is still unambiguous — "X–Y" reads as *walk
        forward from X until Y* whichever day you think the week starts on."""
        if not self.days:
            return ()
        present = {WEEKDAYS.index(d) for d in self.days}
        if len(present) == 7:
            return ((WEEKDAYS[0], WEEKDAYS[6]),)  # open every day
        runs: list[tuple[str, str]] = []
        for start in sorted(i for i in present if (i - 1) % 7 not in present):
            last = start
            while (last + 1) % 7 in present:
                last = (last + 1) % 7
            runs.append((WEEKDAYS[start], WEEKDAYS[last]))
        return tuple(runs)

    @property
    def hours_display(self) -> str:
        """``"09:30–12:30, 14:00–18:00"`` — digits only, so it needs no
        localization and both renderers print the one string."""
        return ", ".join(f"{o:%H:%M}–{c:%H:%M}" for o, c in self.hours)

    def closed_on(self, day: date | None) -> bool:
        """True when ``day`` falls on a weekday this place doesn't open. Unknown
        (no date, or no stated days) is never "closed"."""
        if day is None or not self.days:
            return False
        return WEEKDAYS[day.weekday()] not in self.days

    def covers(self, start: time | None, end: time | None = None) -> bool:
        """True when a visit running ``start`` → ``end`` fits inside a *single*
        opening range — so a visit straddling the midday closure doesn't count,
        which is the whole reason the closure is kept as two ranges. Unknown (no
        stated hours, or no start time) always fits: there is nothing to be
        outside of."""
        if not self.hours or start is None:
            return True
        s = _tmin(start)
        e = _tmin(end) if end is not None else s
        if e < s:  # the visit runs past midnight
            e += 1440
        for opens, closes in self.hours:
            o, c = _tmin(opens), _tmin(closes)
            if c < o:
                c += 1440  # the range runs past midnight
            if o <= s and e <= c:
                return True
            # A range that crossed midnight also covers the small hours of the
            # same clock day, so try the visit shifted a day forward.
            if c > 1440 and o <= s + 1440 and e + 1440 <= c:
                return True
        return False


def parse_opening(data: dict) -> Opening | None:
    """The ``Opening`` behind an activity's ``opening_days`` / ``opening_hours``,
    or ``None`` when it states neither."""
    days = _parse_opening_days(data.get("opening_days"))
    hours = _parse_opening_hours(data.get("opening_hours"))
    if not days and not hours:
        return None
    return Opening(days=days, hours=hours)
