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

  The hours may also **differ by weekday**, written as ``;``-separated groups
  each optionally prefixed with the days it applies to —
  ``"mon-sat 09:00-17:00; sun 10:00-17:00"``. That stays one transcribable line
  rather than becoming a list of objects, which is the whole point of these two
  fields; and because a day spec never contains a digit while a time range
  always starts with one, the split needs no punctuation between them. A group
  with **no** days is the default for every day no other group names, so
  ``"09:00-17:00; sun 10:00-17:00"`` reads as "9-5, but 10-5 on Sundays". Two
  groups may not name the same weekday, and there may be at most one default
  group: either would leave the day's hours ambiguous.

Both reduce to one :class:`Opening` — a set of open ``days`` plus the
:class:`OpeningRule` list — which is what the renderers draw and what the
validator asks whether a visit falls inside (:meth:`Opening.closed_on` /
:meth:`Opening.covers`). It carries no display strings beyond the
language-neutral ``hours_display``: weekday names have to be localized, so each
renderer formats ``day_runs`` itself (``lang.fmt_weekday_runs`` on the Python
side, ``fmtWeekdayRuns`` in the viewer).

``per_day`` is what tells a renderer which of the two shapes to draw: without
it the line is the overall days then the hours (``Tue–Sun · 09:30–18:00``), with
it one part per rule (``Mon–Sat 09:00–17:00 · Sun 10:00–17:00``). Keep
``pdf/days.py``'s ``_opening_line`` and the viewer's ``Opening`` in step.
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
_HOURS_EXPECTED = ("time ranges like '09:30-18:00' or '09:30-12:30, 14:00-18:00', "
                   "optionally per weekday as 'mon-sat 09:00-17:00; sun 10:00-17:00'")

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


def _parse_hour_ranges(text: str, value) -> tuple[tuple[time, time], ...]:
    """The ``HH:MM-HH:MM`` ranges of one comma-separated run, in the order
    given. ``value`` is the whole field, echoed in any error."""
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


# Where a group's day spec ends and its hours begin: a weekday name holds no
# digit, and a time range always opens with one, so the first digit is the seam
# and no separator has to be written between the two.
_FIRST_DIGIT = re.compile(r"\d")


def _parse_opening_hours(value) -> tuple["OpeningRule", ...]:
    """``"mon-sat 09:00-17:00; sun 10:00-17:00"`` → one :class:`OpeningRule` per
    ``;``-separated group, in the order given. ``()`` when nothing is given
    (open all day).

    A group with no day prefix is the default (``days=()``); the plain
    single-group form every existing file uses therefore yields exactly one
    rule with no days, which is what makes the whole feature backward
    compatible."""
    if value is None or value == "":
        return ()
    text = str(value).strip()
    if not text:
        return ()
    rules: list[OpeningRule] = []
    claimed: dict[str, None] = {}   # weekday → already named by an earlier rule
    for group in text.split(";"):
        token = group.strip()
        if not token:
            continue
        seam = _FIRST_DIGIT.search(token)
        if seam is None:
            raise ItineraryError(
                f"Invalid opening_hours {value!r}, expected {_HOURS_EXPECTED}")
        days = _parse_opening_days_in_hours(token[:seam.start()], value)
        hours = _parse_hour_ranges(token[seam.start():], value)
        if not hours:
            raise ItineraryError(
                f"Invalid opening_hours {value!r}, expected {_HOURS_EXPECTED}")
        # Both clashes make a day's hours ambiguous, so neither can be resolved
        # by picking one — they have to be reported.
        if not days and any(not r.days for r in rules):
            raise ItineraryError(
                f"opening_hours {value!r} has two groups with no weekdays — "
                "only one can be the default for the days nothing else names")
        for name in days:
            if name in claimed:
                raise ItineraryError(
                    f"opening_hours {value!r} names {name} twice — a day can "
                    "only have one set of hours")
            claimed[name] = None
        rules.append(OpeningRule(days=days, hours=hours))
    return tuple(rules)


def _parse_opening_days_in_hours(text: str, value) -> tuple[str, ...]:
    """The day prefix of one ``opening_hours`` group (``""`` → ``()``). Reuses
    the ``opening_days`` grammar, but reports against ``opening_hours``, which
    is the field the reader actually wrote."""
    spec = text.strip().rstrip(",").strip()
    if not spec:
        return ()
    try:
        return _parse_opening_days(spec)
    except ItineraryError as exc:
        raise ItineraryError(
            f"Invalid opening_hours {value!r}, expected {_HOURS_EXPECTED}"
        ) from exc


def _fold_day_runs(days: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """``days`` folded into consecutive runs, as ``(first, last)`` name pairs —
    ``("monday", "wednesday"), ("friday", "friday")`` for Mon-Wed + Fri. A
    single day is a run of one, so a renderer has just the one shape to format.

    Runs **wrap the week**: a place closed on Tuesdays folds to the one run
    ``Wed–Mon``, which is how opening days are printed, rather than to
    ``Mon, Wed–Sun``, which splits the message in two at a boundary nobody cares
    about. A wrapping run is still unambiguous — "X–Y" reads as *walk forward
    from X until Y* whichever day you think the week starts on."""
    if not days:
        return ()
    present = {WEEKDAYS.index(d) for d in days}
    if len(present) == 7:
        return ((WEEKDAYS[0], WEEKDAYS[6]),)  # open every day
    runs: list[tuple[str, str]] = []
    for start in sorted(i for i in present if (i - 1) % 7 not in present):
        last = start
        while (last + 1) % 7 in present:
            last = (last + 1) % 7
        runs.append((WEEKDAYS[start], WEEKDAYS[last]))
    return tuple(runs)


def _hours_display(hours: tuple[tuple[time, time], ...]) -> str:
    """``"09:30–12:30, 14:00–18:00"`` — digits only, so it needs no localization
    and both renderers print the one string."""
    return ", ".join(f"{o:%H:%M}–{c:%H:%M}" for o, c in hours)


@dataclass(frozen=True)
class OpeningRule:
    """One set of hours, and the weekdays it applies to. ``days`` empty means
    *every day no other rule names* — the default group, and the only shape a
    file that never mentions a weekday in its ``opening_hours`` produces."""

    days: tuple[str, ...] = ()
    hours: tuple[tuple[time, time], ...] = ()

    @property
    def day_runs(self) -> tuple[tuple[str, str], ...]:
        return _fold_day_runs(self.days)

    @property
    def hours_display(self) -> str:
        return _hours_display(self.hours)


@dataclass(frozen=True)
class Opening:
    """When a point of interest is open: the weekdays it opens at all, plus one
    or more :class:`OpeningRule` hour sets. Either half may be empty — no
    ``days`` means every day, no ``rules`` means all day — so an empty
    ``Opening`` says nothing and is never built (:func:`parse_opening` returns
    ``None``)."""

    days: tuple[str, ...] = ()
    rules: tuple[OpeningRule, ...] = ()

    @property
    def day_runs(self) -> tuple[tuple[str, str], ...]:
        """The open ``days`` folded into runs — see :func:`_fold_day_runs`."""
        return _fold_day_runs(self.days)

    @property
    def per_day(self) -> bool:
        """True when the hours differ by weekday, i.e. some rule names days.
        This is what picks between the renderers' two line shapes."""
        return any(rule.days for rule in self.rules)

    @property
    def hours(self) -> tuple[tuple[time, time], ...]:
        """Every stated range, whichever day it belongs to — so ``if
        opening.hours`` still reads as "some hours are stated", and a check with
        no date to go on has the full set to fall back on."""
        return tuple(r for rule in self.rules for r in rule.hours)

    @property
    def hours_display(self) -> str:
        """The hours as one digits-only string. With per-weekday rules this is
        the union and so says nothing about *which* day — a renderer drawing
        those wants ``rules``, and a message about one day wants
        :meth:`hours_display_on`."""
        return _hours_display(self.hours)

    def hours_on(self, day: date | None) -> tuple[tuple[time, time], ...]:
        """The ranges that apply on ``day``: the rule naming that weekday, else
        the default rule, else nothing stated. With no date there is no rule to
        pick, so every range is in play (:attr:`hours`)."""
        if day is None:
            return self.hours
        name = WEEKDAYS[day.weekday()]
        for rule in self.rules:
            if rule.days and name in rule.days:
                return rule.hours
        for rule in self.rules:
            if not rule.days:
                return rule.hours
        return ()

    def hours_display_on(self, day: date | None) -> str:
        """:meth:`hours_on` as the digits-only string, for a message about one
        particular day."""
        return _hours_display(self.hours_on(day))

    def closed_on(self, day: date | None) -> bool:
        """True when ``day`` falls on a weekday this place doesn't open. Unknown
        (no date, or no stated days) is never "closed"."""
        if day is None or not self.days:
            return False
        return WEEKDAYS[day.weekday()] not in self.days

    def covers(self, start: time | None, end: time | None = None,
               on: date | None = None) -> bool:
        """True when a visit running ``start`` → ``end`` fits inside a *single*
        opening range — so a visit straddling the midday closure doesn't count,
        which is the whole reason the closure is kept as two ranges. Unknown (no
        stated hours, or no start time) always fits: there is nothing to be
        outside of.

        ``on`` is the date of the visit, which is what picks the rule when the
        hours differ by weekday. Leaving it out checks against *every* stated
        range, so a caller with no date can't report a Sunday visit as outside
        the weekday hours."""
        hours = self.hours_on(on)
        if not hours or start is None:
            return True
        s = _tmin(start)
        e = _tmin(end) if end is not None else s
        if e < s:  # the visit runs past midnight
            e += 1440
        for opens, closes in hours:
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
    or ``None`` when it states neither.

    ``opening_days`` stays authoritative for *which* days the place opens. When
    it is absent but the hours name weekdays, those days become the open set:
    writing ``"mon-fri 09:00-17:00"`` and nothing else says the place is shut at
    the weekend, and inferring anything less would report it as open with no
    stated hours. A default (day-less) group leaves the set empty — it applies
    to every day, so it claims none in particular."""
    days = _parse_opening_days(data.get("opening_days"))
    rules = _parse_opening_hours(data.get("opening_hours"))
    if not days and not rules:
        return None
    if not days and any(rule.days for rule in rules):
        named = {d for rule in rules for d in rule.days}
        # A default group covers whatever the named ones leave over, so the
        # place is open all week and the day set stays empty.
        if not any(not rule.days for rule in rules):
            days = tuple(d for d in WEEKDAYS if d in named)
    return Opening(days=days, rules=rules)
