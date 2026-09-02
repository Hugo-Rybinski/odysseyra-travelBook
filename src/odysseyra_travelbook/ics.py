"""Export a resolved :class:`~.models.Itinerary` to an iCalendar (``.ics``) file
that imports cleanly into Google Calendar (and Apple/Outlook).

One ``VEVENT`` is emitted per timed thing in the trip:

* every day activity **except buffers** (which are free time, not events),
* every transport **leg** — a booking that moves you twice gets two events,
* every car-rental pick-up and drop-off,
* every **night** of each accommodation booking — a night runs from that evening
  at ``defaults.accommodation_start_time`` (22:00) to
  ``defaults.accommodation_end_time`` (00:00, i.e. midnight).

**Time zones.** Everything in the model is a wall-clock time plus a fixed UTC
offset (``start_tz`` / ``end_tz``, falling back to the trip's ``timezone``). We
emit each datetime as its local wall time tagged with a ``TZID`` that points at a
self-contained ``VTIMEZONE`` block carrying that offset, so the event lands at
the right instant *and* shows the local time of the place — a leg that departs
in one zone and arrives in another keeps both. No IANA zone database is needed.

Every event's ``DESCRIPTION`` is packed with as much of the object's detail as it
carries (addresses, references, prices, nested activities, …), localized via
:func:`~.lang.tr` when ``lang`` is not English.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from .lang import fmt_date, fmt_weekday_runs, tr
from .models import Itinerary, format_elevation, format_km
from .models.currency import format_money

__all__ = ["build_ics"]

# A car event with no explicit duration, and any zero-length event, is given
# this many minutes so it shows as a visible block rather than an instant.
_MIN_EVENT_MIN = 15
_CAR_EVENT_MIN = 30

# A leading glyph on each event summary, by activity kind / transport type, so
# the calendar is scannable at a glance. Kinds/types not listed get none.
_ACTIVITY_EMOJI = {"road": "🚗", "hike": "🥾", "meal": "🍽️"}
_TRANSPORT_EMOJI = {
    "plane": "✈️", "train": "🚆", "bus": "🚌", "taxi": "🚕", "ferry": "⛴️",
}  # "other" is intentionally left unprefixed
_ACCOMMODATION_EMOJI = "🛏️"


def _with_emoji(emoji: str, text: str) -> str:
    return f"{emoji} {text}" if emoji else text


# --- low-level iCalendar text helpers --------------------------------------

def _escape(text: str) -> str:
    """Escape a text value per RFC 5545 (backslash, ``;`` ``,`` and newlines)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Fold a content line to <=75 octets, continuations prefixed with a space,
    never splitting a multi-byte UTF-8 character (RFC 5545 §3.1)."""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    pieces: list[bytes] = []
    start, limit = 0, 75
    while start < len(encoded):
        end = min(start + limit, len(encoded))
        while end < len(encoded) and (encoded[end] & 0xC0) == 0x80:
            end -= 1  # back off to a character boundary
        pieces.append(encoded[start:end])
        start, limit = end, 74  # continuation lines lose one octet to the space
    return "\r\n ".join(p.decode("utf-8") for p in pieces)


def _fmt_offset(offset: int) -> str:
    """A UTC offset in minutes as ``+HHMM`` / ``-HHMM`` (for ``TZOFFSET*``)."""
    sign = "+" if offset >= 0 else "-"
    h, m = divmod(abs(offset), 60)
    return f"{sign}{h:02d}{m:02d}"


def _tzid(offset: int) -> str:
    """A colon-free ``TZID`` label for a fixed offset (safe as an unquoted
    parameter value): ``GMT`` at UTC, else e.g. ``GMT+0200`` / ``GMT-0330``."""
    return "GMT" if offset == 0 else "GMT" + _fmt_offset(offset)


def _vtimezone(offset: int) -> list[str]:
    """A minimal fixed-offset ``VTIMEZONE`` (no daylight-saving transitions)."""
    off = _fmt_offset(offset)
    return [
        "BEGIN:VTIMEZONE",
        f"TZID:{_tzid(offset)}",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        f"TZOFFSETFROM:{off}",
        f"TZOFFSETTO:{off}",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]


def _local(dt: datetime, offset: int) -> str:
    """A local-time property value tagged with its zone: ``;TZID=…:YYYYMMDDT…``."""
    return f";TZID={_tzid(offset)}:{dt:%Y%m%dT%H%M%S}"


def _slug(title: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in title]
    slug = "".join(keep).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "trip"


# --- an event being assembled ----------------------------------------------

class _Event:
    """One VEVENT: its summary, tagged start/end, location and detail lines."""

    __slots__ = ("uid", "summary", "start", "start_off", "end", "end_off",
                 "location", "lines")

    def __init__(self, uid: str, summary: str, start: datetime, start_off: int,
                 end: datetime, end_off: int, location: str, lines: list[str]):
        self.uid = uid
        self.summary = summary
        self.start = start
        self.start_off = start_off
        self.end = end
        self.end_off = end_off
        self.location = location
        self.lines = lines


def _combine(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute)


def _detail(lines: list[str], label: str, value, lang: str = "en") -> None:
    """Append a ``Label: value`` line when ``value`` is non-empty."""
    if value in (None, "", False):
        return
    lines.append(f"{tr(label, lang)}: {value}")


# --- per-section event builders --------------------------------------------

def _activity_events(itin: Itinerary, day, day_no: int, day_date: date,
                     uid_base: str, lang: str, counter: list[int]) -> list[_Event]:
    events: list[_Event] = []
    context = tr("Day {n}", lang).format(n=day_no)
    if day.title:
        context += f" · {day.title}"
    for act in day.activities:
        if act.kind == "buffer" or act.start_time is None:
            continue
        start_off = act.start_tz if act.start_tz is not None else itin.default_timezone
        end_off = act.end_tz if act.end_tz is not None else itin.default_timezone
        sdt = _combine(day_date, act.start_time)
        edt = _combine(day_date, act.end_time or act.start_time)
        if edt < sdt:
            edt += timedelta(days=1)  # crossed midnight
        if edt <= sdt:
            edt = sdt + timedelta(minutes=_MIN_EVENT_MIN)

        lines = [context, ""]
        location = ""
        if act.kind == "road":
            _detail(lines, "Type", tr("Drive", lang), lang)
            _detail(lines, "Distance", format_km(act.distance_km), lang)
            # road-level flag, or any single leg marked off-road
            if act.off_road or any(w.off_road for w in act.waypoints):
                _detail(lines, "Off-road", tr("Yes", lang), lang)
            names = [w.location for w in act.waypoints if w.location]
            _detail(lines, "Via", ", ".join(names), lang)
            _detail(lines, "Guidebook", _pages(act, lang), lang)
            # the arrival (final named waypoint) is the useful map target;
            # fall back to the departure when the drive has no named arrival.
            location = act.destination or act.start
        elif act.kind == "point_of_interest":
            _detail(lines, "Category", tr(act.category, lang), lang)
            _detail(lines, "Open", _opening(act, lang), lang)
            _detail(lines, "Address", act.address, lang)
            _detail(lines, "Website", act.website, lang)
            _detail(lines, "Description", act.description, lang)
            _detail(lines, "Guidebook", _pages(act, lang), lang)
            location = act.address
        elif act.kind == "place":
            _detail(lines, "Description", act.description, lang)
            _detail(lines, "Guidebook", _pages(act, lang), lang)
        elif act.kind == "hike":
            _detail(lines, "Distance", format_km(act.distance_km), lang)
            _detail(lines, "Elevation", format_elevation(act.elevation_m), lang)
            _detail(lines, "Route", tr(act.route_label, lang), lang)
            _detail(lines, "Description", act.description, lang)
            _detail(lines, "Guidebook", _pages(act, lang), lang)
            location = act.start
        elif act.kind == "meal":
            _detail(lines, "Type", tr(act.category or "meal", lang), lang)
            _detail(lines, "Restaurant", act.restaurant, lang)
            _detail(lines, "Area", act.area, lang)
            _detail(lines, "Address", act.address, lang)
            location = act.address or act.area
        nested = [a.title for a in getattr(act, "activities", []) or []]
        _detail(lines, "Includes", "; ".join(nested), lang)
        _detail(lines, "Duration", act.duration_display, lang)

        counter[0] += 1
        summary = _with_emoji(_ACTIVITY_EMOJI.get(act.kind, ""), act.title)
        events.append(_Event(
            f"{uid_base}-{counter[0]}@odysseyra", summary,
            sdt, start_off, edt, end_off, location, _trim(lines)))
    return events


def _transport_events(itin: Itinerary, uid_base: str, lang: str,
                      counter: list[int]) -> list[_Event]:
    events: list[_Event] = []
    # One event per *leg* — a calendar entry is a movement, so a two-leg round
    # trip is two entries. The booking's shared fields (reference, source,
    # status, price, links) are packed onto each, read straight off the leg.
    for t in itin.transports:
        for leg in t.legs:
            if leg.start_date is None or leg.start_time is None:
                continue
            start_off = (leg.start_tz if leg.start_tz is not None
                         else itin.default_timezone)
            end_off = leg.end_tz if leg.end_tz is not None else itin.default_timezone
            sdt = _combine(leg.start_date, leg.start_time)
            end_date = leg.end_date or leg.start_date
            edt = (_combine(end_date, leg.end_time) if leg.end_time is not None
                   else sdt + timedelta(minutes=_MIN_EVENT_MIN))
            if edt <= sdt:
                edt = sdt + timedelta(minutes=_MIN_EVENT_MIN)

            type_label = leg.type.title() if leg.type else tr("Transport", lang)
            summary = _with_emoji(_TRANSPORT_EMOJI.get(leg.type, ""),
                                  f"{tr(type_label, lang)}: {leg.title}")
            lines = [
                f"{tr('Departure', lang)}: {leg.start} — "
                f"{fmt_date(leg.start_date, 'wd_md', lang)} {leg.start_time:%H:%M}",
                f"{tr('Arrival', lang)}: {leg.end} — "
                f"{fmt_date(end_date, 'wd_md', lang)} "
                f"{(leg.end_time or leg.start_time):%H:%M}",
                "",
            ]
            _detail(lines, "Duration", leg.duration_display, lang)
            _detail(lines, "Flight number", leg.flight_number, lang)
            _detail(lines, "Train number", leg.train_number, lang)
            _detail(lines, "Booking number", leg.booking_number, lang)
            _detail(lines, "Booking source", leg.booking_source, lang)
            _detail(lines, "Status", tr(leg.status, lang) if leg.status else "", lang)
            _detail(lines, "Description", leg.description, lang)
            # The booking's own note, on every one of its events — it is about
            # the reservation, so it applies to each hop. Labelled apart from the
            # leg's own note above so the two can't be read as one.
            _detail(lines, "Booking note", t.description, lang)
            # The booking's price, and a multi-leg booking says so rather than
            # looking like this hop's fare.
            _detail(lines, "Price" if leg.leg_count == 1 else "Price (whole booking)",
                    _money(itin, leg.price, leg.currency, leg.paid, lang), lang)
            _detail(lines, "Website", leg.website, lang)
            _detail(lines, "Booking", leg.booking_link, lang)

            counter[0] += 1
            events.append(_Event(
                f"{uid_base}-{counter[0]}@odysseyra", summary,
                sdt, start_off, edt, end_off, leg.start, _trim(lines)))
    return events


def _car_events(itin: Itinerary, uid_base: str, lang: str,
                counter: list[int]) -> list[_Event]:
    events: list[_Event] = []
    for cr in itin.car_rentals:
        specs = (
            ("Car pick-up", cr.pickup, cr.pickup_location, cr.pickup_duration_min, True),
            ("Car drop-off", cr.dropoff, cr.dropoff_location, cr.dropoff_duration_min, False),
        )
        for label, stamp, loc, dur, is_pickup in specs:
            if stamp.date is None or stamp.time is None:
                continue
            off = stamp.tz if stamp.tz is not None else itin.default_timezone
            sdt = _combine(stamp.date, stamp.time)
            edt = sdt + timedelta(minutes=max(dur or 0, _CAR_EVENT_MIN))

            who = cr.company or cr.car_model or tr("Car rental", lang)
            lines: list[str] = []
            _detail(lines, "Company", cr.company, lang)
            _detail(lines, "Car model", cr.car_model, lang)
            _detail(lines, "Car type", cr.car_type_label, lang)
            _detail(lines, "Booking number", cr.booking_number, lang)
            if is_pickup:
                _detail(lines, "Additional drivers",
                        cr.additional_drivers or "", lang)
                _detail(lines, "Price",
                        _money(itin, cr.price, cr.currency, cr.paid, lang), lang)
            _detail(lines, "Status", tr(cr.status, lang) if cr.status else "", lang)
            _detail(lines, "Description", cr.description, lang)
            _detail(lines, "Contact", cr.contact, lang)
            _detail(lines, "Website", cr.website, lang)
            _detail(lines, "Booking", cr.booking_link, lang)

            counter[0] += 1
            events.append(_Event(
                f"{uid_base}-{counter[0]}@odysseyra", f"{tr(label, lang)}: {who}",
                sdt, off, edt, off, loc, _trim(lines)))
    return events


def _accommodation_events(itin: Itinerary, uid_base: str, lang: str,
                          counter: list[int]) -> list[_Event]:
    """One event **per night** of each booking: every night from arrival up to
    (not including) departure runs from that evening's
    ``accommodation_start_time`` to ``accommodation_end_time`` the next day
    (midnight by default)."""
    events: list[_Event] = []
    off = itin.default_timezone
    start_t = itin.default_accommodation_start_time
    end_t = itin.default_accommodation_end_time
    for acc in itin.accommodations:
        if acc.arrival is None:
            continue
        departure = acc.departure or (acc.arrival + timedelta(days=1))
        total = max((departure - acc.arrival).days, 1)
        for i in range(total):
            night = acc.arrival + timedelta(days=i)
            sdt = _combine(night, start_t)
            edt = _combine(night + timedelta(days=1), end_t)
            if edt <= sdt:
                edt = sdt + timedelta(minutes=_MIN_EVENT_MIN)

            lines: list[str] = []
            if total > 1:
                _detail(lines, "Night", f"{i + 1}/{total}", lang)
            _detail(lines, "Type", tr(acc.type, lang), lang)
            _detail(lines, "City", acc.city, lang)
            _detail(lines, "Address", acc.address, lang)
            if acc.breakfast_included:
                _detail(lines, "Breakfast included", tr("Yes", lang), lang)
            _detail(lines, "Contact", acc.contact, lang)
            _detail(lines, "Status", tr(acc.status, lang) if acc.status else "", lang)
            _detail(lines, "Description", acc.description, lang)
            _detail(lines, "Price",
                    _money(itin, acc.price, acc.currency, acc.paid, lang), lang)
            _detail(lines, "Booking source", acc.booking_source, lang)
            _detail(lines, "Website", acc.website, lang)
            _detail(lines, "Booking", acc.booking_link, lang)

            counter[0] += 1
            events.append(_Event(
                f"{uid_base}-{counter[0]}@odysseyra",
                _with_emoji(_ACCOMMODATION_EMOJI, acc.name),
                sdt, off, edt, off, acc.address or acc.city, _trim(lines)))
    return events


# --- value formatters -------------------------------------------------------

def _pages(act, lang: str) -> str:
    """An activity's guidebook page reference as ``p. 15-18`` ("" when it has
    none). Only road / point_of_interest / place / hike carry the field."""
    pages = getattr(act, "guidebook_pages", "")
    return tr("p. {pages}", lang).format(pages=pages) if pages else ""


def _opening(act, lang: str) -> str:
    """A point of interest's opening days/hours on one line — ``Tue–Sun, 09:30–
    12:30, 14:00–18:00`` ("" when it states neither). Only a point of interest
    carries the field."""
    opening = getattr(act, "opening", None)
    if opening is None:
        return ""
    parts = []
    if opening.day_runs:
        parts.append(fmt_weekday_runs(opening.day_runs, lang))
    if opening.hours:
        parts.append(opening.hours_display)
    return ", ".join(parts)


def _money(itin: Itinerary, amount, currency: str, paid, lang: str) -> str:
    if amount is None:
        return ""
    code = (currency or itin.default_currency).strip().upper()
    out = format_money(amount, code, lang)
    if paid is True:
        out += f" ({tr('paid', lang)})"
    elif paid is False:
        out += f" ({tr('to pay', lang)})"
    return out


def _trim(lines: list[str]) -> list[str]:
    """Drop a trailing blank separator when a section produced no detail lines."""
    while lines and lines[-1] == "":
        lines.pop()
    return lines


# --- assembly ---------------------------------------------------------------

def _render(itin: Itinerary, events: list[_Event], now: datetime,
            lang: str) -> str:
    dtstamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    offsets = sorted({e.start_off for e in events} | {e.end_off for e in events})

    out: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Odysseyra//TravelBook//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(itin.title)}",
    ]
    for off in offsets:
        out.extend(_vtimezone(off))
    for e in events:
        out.append("BEGIN:VEVENT")
        out.append(f"UID:{e.uid}")
        out.append(f"DTSTAMP:{dtstamp}")
        out.append(f"DTSTART{_local(e.start, e.start_off)}")
        out.append(f"DTEND{_local(e.end, e.end_off)}")
        out.append(f"SUMMARY:{_escape(e.summary)}")
        if e.location:
            out.append(f"LOCATION:{_escape(e.location)}")
        body = "\n".join(e.lines).strip("\n")
        if body:
            out.append(f"DESCRIPTION:{_escape(body)}")
        out.append("END:VEVENT")
    out.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in out) + "\r\n"


def build_ics(itinerary: Itinerary, output: str | Path | None = None,
              lang: str = "en", now: datetime | None = None) -> str:
    """Build the iCalendar text for a resolved ``itinerary`` and return it.

    When ``output`` is given the text is also written there (UTF-8). ``now``
    stamps every event's ``DTSTAMP`` (defaults to the current UTC time; pass a
    fixed value for reproducible output)."""
    now = now or datetime.now(timezone.utc)
    uid_base = _slug(itinerary.title)
    counter = [0]
    events: list[_Event] = []
    for i, day in enumerate(itinerary.days, start=1):
        if day.date is None:
            continue
        events += _activity_events(itinerary, day, i, day.date, uid_base, lang, counter)
    events += _transport_events(itinerary, uid_base, lang, counter)
    events += _car_events(itinerary, uid_base, lang, counter)
    events += _accommodation_events(itinerary, uid_base, lang, counter)

    text = _render(itinerary, events, now, lang)
    if output is not None:
        Path(output).write_text(text, encoding="utf-8")
    return text
