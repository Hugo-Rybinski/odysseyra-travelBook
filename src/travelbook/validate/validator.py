"""The validator: walks the parsed data (with line numbers) and emits findings."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from ..lang import DEFAULT_LANGUAGE, tr
from ..models import (
    Itinerary,
    ItineraryError,
    _parse_date,
    _parse_duration,
    _parse_route,
    _parse_time,
    _parse_tz,
)
from .findings import Finding
from .jsonpos import JSONPositionError, load_with_lines
from .specs import (
    ACCOMMODATION_SPECS,
    ACTIVITY_SPECS,
    CAR_RENTAL_SPECS,
    DAY_SPECS,
    DEFAULTS,
    SCHEDULE,
    TRANSPORT_SPECS,
    TRAVEL_DESCRIPTION,
)


def _tmin(value):
    try:
        t = _parse_time(value)
    except ItineraryError:
        return None
    return None if t is None else t.hour * 60 + t.minute


def _tz(value, default):
    if value in (None, ""):
        return default or 0
    try:
        v = _parse_tz(value)
    except ItineraryError:
        return default or 0
    return v if v is not None else (default or 0)


def _dur(value):
    try:
        return _parse_duration(value)
    except ItineraryError:
        return None


def _date(value):
    try:
        return _parse_date(value)
    except ItineraryError:
        return None


def _span(obj):
    """A (start, end) minute pair from explicit times (end may exceed 1440 if
    it crosses midnight), or None if not determinable."""
    s = _tmin(obj.get("start_time"))
    if s is None:
        return None
    e = _tmin(obj.get("end_time"))
    if e is None:
        d = _dur(obj.get("duration"))
        e = s + d if d is not None else None
    if e is None:
        return None
    if e <= s:
        e += 1440
    return (s, e)


def _acc_nights(a):
    arr, dep = _date(a.get("arrival")), _date(a.get("departure"))
    return (arr, dep) if (arr and dep and dep > arr) else None


def _acc_covers(a, day):
    nights = _acc_nights(a)
    return bool(nights and nights[0] <= day < nights[1])


def _transport_dates(t):
    """(start_date, end_date) with end_date inferred (+1 for overnight legs)."""
    sd, ed = _date(t.get("start_date")), _date(t.get("end_date"))
    if ed is None and sd is not None:
        s, e = _tmin(t.get("start_time")), _tmin(t.get("end_time"))
        ed = sd + timedelta(days=1) if (s is not None and e is not None and e < s) else sd
    return sd, ed


def _truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "yes", "1", "paid", "paid online")


class _Validator:
    def __init__(self, data, lines, lang=DEFAULT_LANGUAGE):
        self.data = data
        self.lines = lines
        self.lang = lang
        self.findings: list[Finding] = []

    def t(self, text):
        return tr(text, self.lang)

    def line(self, path):
        for k in range(len(path), -1, -1):
            ln = self.lines.get(tuple(path[:k]))
            if ln is not None:
                return ln
        return 1

    def add(self, level, path, template, **kw):
        """Add a finding; ``template`` is translated then ``.format(**kw)``ed."""
        message = self.t(template).format(**kw) if kw else self.t(template)
        self.findings.append(Finding(level, self.line(path), message))

    def check_object(self, obj, base_path, specs, *, skip_optional=False):
        obj_line = self.line(base_path)
        for spec in specs:
            fpath = tuple(base_path) + (spec.name,)
            present = isinstance(obj, dict) and spec.name in obj and obj[spec.name] is not None
            desc = self.t(spec.description)
            expected = self.t(spec.expected)
            if present:
                value = obj[spec.name]
                if spec.check and not (isinstance(value, list) or isinstance(value, dict)):
                    err = spec.check(value)
                    if err:
                        self.findings.append(Finding("error", self.line(fpath), self.t(
                            "field '{name}' is invalid ({value}) — {description}. "
                            "Expected {expected} ({error}).").format(
                            name=spec.name, value=repr(value), description=desc,
                            expected=expected, error=err)))
            elif spec.required:
                self.findings.append(Finding("error", obj_line, self.t(
                    "required field '{name}' is missing — {description}. "
                    "Expected {expected}.").format(
                    name=spec.name, description=desc, expected=expected)))
            elif not skip_optional:
                self.findings.append(Finding(
                    "warning" if spec.warn_if_missing else "info", obj_line, self.t(
                        "optional field '{name}' is missing — {description}. "
                        "Expected {expected}. Defaulting to {default}.").format(
                        name=spec.name, description=desc, expected=expected,
                        default=self.t(spec.default))))

    # -- top level ------------------------------------------------------
    def run(self):
        data = self.data
        if not isinstance(data, dict):
            self.add("error", (), "the top-level JSON must be an object")
            return self.findings

        td = data.get("travel_description")
        td_path = ("travel_description",) if isinstance(td, dict) else ()
        td_obj = td if isinstance(td, dict) else data
        self.check_object(td_obj, td_path, TRAVEL_DESCRIPTION)

        df = data.get("default")
        df_path = ("default",) if isinstance(df, dict) else ()
        df_obj = df if isinstance(df, dict) else {}
        self.check_object(df_obj, df_path or (), DEFAULTS)

        days = data.get("days")
        if not isinstance(days, list) or not days:
            self.add("error", ("days",) if "days" in data else (),
                     "required field 'days' is missing or empty — the list of "
                     "days. Expected a non-empty array of day objects.")
        else:
            for i, day in enumerate(days):
                self._day(day, ("days", i))

        transport = data.get("transport", data.get("transports"))
        if transport is None:
            self.add("info", (), "optional field 'transport' is missing — the "
                     "transport legs. Expected an array of transport objects. "
                     "Defaulting to [] (no transport page).")
        elif isinstance(transport, list):
            for i, t in enumerate(transport):
                self._transport(t, ("transport", i))

        acc = data.get("accommodations")
        if acc is None:
            self.add("info", (), "optional field 'accommodations' is missing — "
                     "the places you stay. Expected an array of accommodation "
                     "objects. Defaulting to [] (no accommodation page).")
        elif isinstance(acc, list):
            for i, a in enumerate(acc):
                self._accommodation(a, ("accommodations", i))

        cars = data.get("car_rentals")
        if cars is None:
            self.add("info", (), "optional field 'car_rentals' is missing — the "
                     "rental-car bookings. Expected an array of car rental "
                     "objects. Defaulting to [] (no car rental page).")
        elif isinstance(cars, list):
            for i, c in enumerate(cars):
                self._car_rental(c, ("car_rentals", i))

        self._coherence(td_obj, days if isinstance(days, list) else [],
                        transport if isinstance(transport, list) else [],
                        acc if isinstance(acc, list) else [])
        return self.findings

    # -- day & activities ----------------------------------------------
    def _day(self, day, path):
        if not isinstance(day, dict):
            self.add("error", path, "each day must be an object")
            return
        self.check_object(day, path, DAY_SPECS)
        activities = day.get("activities")
        if not activities:
            self.add("error", path, "a day's 'activities' must not be empty — every "
                     "day needs at least one activity.")
        for j, act in enumerate(activities or []):
            self._activity(act, path + ("activities", j))

    def _activity(self, act, path):
        if not isinstance(act, dict):
            self.add("error", path, "each activity must be an object with a 'type'")
            return
        kinds = ", ".join(ACTIVITY_SPECS)
        kind = act.get("type")
        if kind is None:
            self.add("error", path, "required field 'type' is missing — the "
                     "activity type. Expected one of: {kinds}.", kinds=kinds)
            return
        if kind not in ACTIVITY_SPECS:
            self.add("error", path + ("type",),
                     "field 'type' is invalid ({kind}) — the activity type. "
                     "Expected one of: {kinds}.", kind=repr(kind), kinds=kinds)
            return
        self.check_object(act, path, ACTIVITY_SPECS[kind])
        if kind != "buffer":
            self.check_object(act, path, SCHEDULE)
            self._time_consistency(act, path, tz_aware=False)
        self._magnitudes(act, path, kind)
        if kind == "buffer":
            if _dur(act.get("duration")) == 0:
                self.add("info", path, "this is a zero-minute buffer — it only "
                         "suppresses the trip's default buffer here and draws no line.")
        if kind == "hike":
            self._hike_route_endpoints(act, path)
        if kind == "meal" and act.get("restaurant") and act.get("area"):
            self.add("warning", path, "both 'restaurant' and 'area' are set — "
                     "'area' is ignored when a restaurant is named.")
        if kind == "place":
            pois = act.get("points_of_interest", act.get("monuments", []))
            for k, poi in enumerate(pois or []):
                if isinstance(poi, str):
                    continue
                if not isinstance(poi, dict):
                    self.add("error", path + ("points_of_interest", k),
                             "a point of interest must be an object or a name string")
                    continue
                self.check_object(poi, path + ("points_of_interest", k),
                                  ACTIVITY_SPECS["point_of_interest"], skip_optional=True)

    def _transport(self, t, path):
        if not isinstance(t, dict):
            self.add("error", path, "each transport must be an object")
            return
        self.check_object(t, path, TRANSPORT_SPECS)
        self._time_consistency(t, path, tz_aware=True)
        self._magnitudes(t, path, "transport")
        sd, ed = _date(t.get("start_date")), _date(t.get("end_date"))
        if sd and ed and ed < sd:
            self.add("error", path, "transport end_date ({ed}) is before "
                     "start_date ({sd}).", ed=ed, sd=sd)
        if t.get("status") and not t.get("booking_number"):
            self.add("warning", path, "'status' is set but 'booking_number' is "
                     "missing — a confirmed/booked leg usually has a reference.")
        if t.get("paid") is not None and not t.get("price"):
            self.add("warning", path, "'paid' is set but 'price' is missing — the "
                     "payment state is given without an amount.")

    def _accommodation(self, a, path):
        if not isinstance(a, dict):
            self.add("error", path, "each accommodation must be an object")
            return
        self.check_object(a, path, ACCOMMODATION_SPECS)
        arr, dep = _date(a.get("arrival")), _date(a.get("departure"))
        if arr and dep and dep <= arr:
            self.add("error", path, "accommodation departure ({dep}) must be "
                     "after arrival ({arr}).", dep=dep, arr=arr)
        if _truthy(a.get("paid_online")) and not a.get("price"):
            self.add("warning", path, "'paid_online' is true but 'price' is "
                     "missing — marked paid without an amount.")

    def _default_tz(self):
        df = self.data.get("default") if isinstance(self.data.get("default"), dict) else {}
        return _tz(df.get("timezone", self.data.get("timezone")), 0)

    def _car_dt(self, obj, dkey, tkey, tzkey, default_tz):
        """(comparable UTC datetime, local label) for a date/time/tz triple, or
        None if either the date or time is missing/unparseable."""
        d = _date(obj.get(dkey))
        try:
            t = _parse_time(obj.get(tkey))
        except ItineraryError:
            t = None
        if d is None or t is None:
            return None
        tz = _tz(obj.get(tzkey), default_tz)
        cmp = datetime.combine(d, t) - timedelta(minutes=tz)
        return cmp, f"{d} {t:%H:%M}"

    def _car_rental(self, cr, path):
        if not isinstance(cr, dict):
            self.add("error", path, "each car rental must be an object")
            return
        self.check_object(cr, path, CAR_RENTAL_SPECS)
        default_tz = self._default_tz()
        bs = self._car_dt(cr, "booking_start_date", "booking_start_time",
                          "booking_start_tz", default_tz)
        be = self._car_dt(cr, "booking_end_date", "booking_end_time",
                          "booking_end_tz", default_tz)
        pu = self._car_dt(cr, "pickup_date", "pickup_time", "pickup_tz", default_tz)
        do = self._car_dt(cr, "dropoff_date", "dropoff_time", "dropoff_tz", default_tz)
        if bs and be and be[0] <= bs[0]:
            self.add("error", path, "car rental booking end ({end}) must be after "
                     "booking start ({start}).", end=be[1], start=bs[1])
        elif bs and be:  # a valid window — check the pick-up / drop-off fall in it
            if pu and not (bs[0] <= pu[0] <= be[0]):
                self.add("error", path, "car rental pick-up ({pu}) is outside the "
                         "booking period ({start} → {end}).",
                         pu=pu[1], start=bs[1], end=be[1])
            if do and not (bs[0] <= do[0] <= be[0]):
                self.add("error", path, "car rental drop-off ({do}) is outside the "
                         "booking period ({start} → {end}).",
                         do=do[1], start=bs[1], end=be[1])
        if pu and do and do[0] < pu[0]:
            self.add("error", path, "car rental drop-off ({do}) is before the "
                     "pick-up ({pu}).", do=do[1], pu=pu[1])
        if cr.get("paid") is not None and not cr.get("price"):
            self.add("warning", path, "'paid' is set but 'price' is missing — the "
                     "payment state is given without an amount.")

    def _car_event_conflicts(self, car_rentals, day_date, occupied):
        """Warn when a car pick-up / drop-off on ``day_date`` overlaps any
        occupied (activity / transport) span on that day."""
        for ci, cr in enumerate(car_rentals):
            if not isinstance(cr, dict):
                continue
            for kind, dkey, tkey, durkey in (
                ("pickup", "pickup_date", "pickup_time", "pickup_duration"),
                ("dropoff", "dropoff_date", "dropoff_time", "dropoff_duration"),
            ):
                if _date(cr.get(dkey)) != day_date:
                    continue
                s = _tmin(cr.get(tkey))
                if s is None:
                    continue
                e = s + (_dur(cr.get(durkey)) or 0)
                clash = any(
                    (s < ae and a0 < e) if e > s else (a0 <= s < ae)
                    for a0, ae in occupied
                )
                if not clash:
                    continue
                when = f"{s // 60:02d}:{s % 60:02d}"
                if kind == "pickup":
                    self.add("warning", ("car_rentals", ci),
                             "the car rental pick-up ({time}) overlaps an activity "
                             "or transport on {date}.", time=when, date=day_date)
                else:
                    self.add("warning", ("car_rentals", ci),
                             "the car rental drop-off ({time}) overlaps an activity "
                             "or transport on {date}.", time=when, date=day_date)

    # -- coherence ------------------------------------------------------
    def _magnitudes(self, obj, path, kind):
        dk = obj.get("distance_km")
        if dk is not None:
            try:
                v = float(dk)
            except (TypeError, ValueError):
                v = None
            if v is not None and v <= 0:
                self.add("error", path + ("distance_km",),
                         "distance_km must be a positive number (got {value}).",
                         value=dk)
        dur = obj.get("duration")
        if dur is not None:
            d = _dur(dur)
            if d is not None and (d < 0 or (d == 0 and kind != "buffer")):
                self.add("error", path + ("duration",),
                         "duration must be a positive length (got {value}).",
                         value=repr(dur))

    def _hike_route_endpoints(self, act, path):
        try:
            route = _parse_route(act.get("route"), default="back_and_forth")
        except ItineraryError:
            return  # invalid route already reported
        start = str(act.get("start", "")).strip()
        end = str(act.get("end", "")).strip()
        if route in ("loop", "back_and_forth") and end and end != start:
            self.add("warning", path, "a '{route}' hike returns to its start, but "
                     "'end' ({end}) differs from 'start' ({start}) — set 'end' "
                     "to the start, or omit it.",
                     route=route, end=repr(end), start=repr(start))
        if route == "one_way" and (not end or end == start):
            self.add("warning", path, "a 'one_way' hike should have an 'end' that "
                     "differs from its 'start'.")

    def _default_start_min(self):
        df = self.data.get("default") if isinstance(self.data.get("default"), dict) else {}
        raw = df.get("start_time", self.data.get("default_start_time"))
        try:
            t = _parse_time(raw)
        except ItineraryError:
            t = None
        return (t.hour * 60 + t.minute) if t else 480  # 08:00

    def _time_consistency(self, obj, path, *, tz_aware):
        s, e, d = _tmin(obj.get("start_time")), _tmin(obj.get("end_time")), _dur(
            obj.get("duration"))
        if s is None or e is None or d is None:
            return
        if tz_aware:
            default = None  # unknown here; use provided offsets only
            so = _tz(obj.get("start_tz"), default)
            eo = _tz(obj.get("end_tz"), default)
            expected = ((s - so) + d + eo) % 1440
        else:
            expected = (s + d) % 1440
        if expected != e % 1440:
            self.add("error", path, "start time, end time and duration are "
                     "incompatible — the three don't agree. Provide only two of "
                     "start_time / end_time / duration, or make them consistent.")

    def _coherence(self, td, days, transport, accommodations):
        # Trip start/end are only cross-checked when set manually (otherwise
        # they are inferred as the earliest/latest date and always consistent).
        td_base = ("travel_description",) if "travel_description" in self.data else ()
        sd, ed = _date(td.get("start_date")), _date(td.get("end_date"))
        range_ok = bool(sd and ed and sd <= ed)

        if sd and ed and ed < sd:
            self.add("error", td_base,
                     "trip end_date ({ed}) is before start_date ({sd}).",
                     ed=ed, sd=sd)

        day_dates = [
            (_date(d.get("date")), i)
            for i, d in enumerate(days) if isinstance(d, dict) and _date(d.get("date"))
        ]

        # (3) duplicate / out-of-order day dates
        seen, prev = {}, None
        for d, i in day_dates:
            if d in seen:
                self.add("error", ("days", i, "date"),
                         "day date {d} is duplicated (also on day {other}).",
                         d=d, other=seen[d] + 1)
            else:
                seen[d] = i
            if prev is not None and d < prev:
                self.add("error", ("days", i, "date"),
                         "day date {d} is earlier than the previous day ({prev}) — "
                         "days should be in chronological order.", d=d, prev=prev)
            prev = d

        # (10) a manual trip range that doesn't cover the itinerary
        if day_dates:
            first_d, last_d = day_dates[0][0], day_dates[-1][0]
            if sd and (not ed or sd <= ed) and sd > first_d:
                self.add("warning", td_base, "trip start_date ({sd}) is after the "
                         "first day ({first}) — the range doesn't cover the trip.",
                         sd=sd, first=first_d)
            if ed and (not sd or sd <= ed) and ed < last_d:
                self.add("warning", td_base, "trip end_date ({ed}) is before the "
                         "last day ({last}) — the range doesn't cover the trip.",
                         ed=ed, last=last_d)

        # (4) dates outside a manual trip range
        if range_ok:
            def _out(d):
                return d < sd or d > ed
            for i, day in enumerate(days):
                if isinstance(day, dict):
                    d = _date(day.get("date"))
                    if d and _out(d):
                        self.add("warning", ("days", i, "date"),
                                 "day date {d} is outside the trip range "
                                 "({sd} → {ed}).", d=d, sd=sd, ed=ed)
            for i, a in enumerate(accommodations):
                if isinstance(a, dict):
                    for key in ("arrival", "departure"):
                        d = _date(a.get(key))
                        if d and _out(d):
                            self.add("warning", ("accommodations", i, key),
                                     "accommodation {key} {d} is outside the trip "
                                     "range ({sd} → {ed}).", key=key, d=d, sd=sd, ed=ed)
            for i, t in enumerate(transport):
                if isinstance(t, dict):
                    for key in ("start_date", "end_date"):
                        d = _date(t.get(key))
                        if d and _out(d):
                            self.add("warning", ("transport", i, key),
                                     "transport {key} {d} is outside the trip "
                                     "range ({sd} → {ed}).", key=key, d=d, sd=sd, ed=ed)

        # (5-existing) overlapping accommodations (same night booked twice)
        stays = []
        for i, a in enumerate(accommodations):
            if isinstance(a, dict):
                n = _acc_nights(a)
                if n:
                    stays.append((n[0], n[1], i, a.get("name", "?")))
        for x in range(len(stays)):
            for y in range(x + 1, len(stays)):
                a1, d1, i1, n1 = stays[x]
                a2, d2, i2, n2 = stays[y]
                if a1 < d2 and a2 < d1:
                    self.add("error", ("accommodations", i2),
                             "accommodations {n1} and {n2} overlap on the same "
                             "night(s) — you can only sleep in one place.",
                             n1=repr(n1), n2=repr(n2))

        # overnight transports indexed by departure date
        overnight = {}
        for i, t in enumerate(transport):
            if isinstance(t, dict):
                tsd, ted = _transport_dates(t)
                if tsd and ted and ted > tsd:
                    overnight.setdefault(tsd, []).append(i)

        # (1) nights with nowhere to sleep, (2) double-booked nights,
        # (12) accommodation city vs day city
        for d, i in day_dates:
            is_last = i == len(days) - 1
            stay = next((a for a in accommodations
                         if isinstance(a, dict) and _acc_covers(a, d)), None)
            has_leg = d in overnight
            if stay is not None and has_leg:
                self.add("error", ("days", i),
                         "the night of {d} has both an accommodation and an "
                         "overnight transport — you can't sleep in two places.", d=d)
            elif stay is None and not has_leg and not is_last:
                self.add("warning", ("days", i),
                         "the night of {d} has no accommodation and no overnight "
                         "transport — you have nowhere to sleep.", d=d)
            if stay is not None:
                city = str(stay.get("city", "")).strip().lower()
                day_city = str(days[i].get("city", "")).strip().lower()
                if city and day_city and city not in day_city:
                    self.add("warning", ("days", i),
                             "the day's city ({day_city}) doesn't match the "
                             "accommodation city ({acc_city}).",
                             day_city=repr(days[i].get("city")),
                             acc_city=repr(stay.get("city")))

        # (5,6) overlapping items on a day's timeline (activities + transports)
        car_rentals = self.data.get("car_rentals") or []
        for di, day in enumerate(days):
            if not isinstance(day, dict):
                continue
            day_date = _date(day.get("date"))
            spans = []
            for aj, act in enumerate(day.get("activities", []) or []):
                if isinstance(act, dict) and act.get("type") != "buffer":
                    sp = _span(act)
                    if sp:
                        spans.append((sp[0], sp[1], ("days", di, "activities", aj)))
            if day_date:
                for tj, t in enumerate(transport):
                    if isinstance(t, dict) and _date(t.get("start_date")) == day_date:
                        sp = _span(t)
                        if sp:
                            spans.append((sp[0], sp[1], ("transport", tj)))
            spans.sort()
            for k in range(1, len(spans)):
                if spans[k][0] < spans[k - 1][1]:
                    self.add("error", spans[k][2], "this overlaps the previous item "
                             "on the day's timeline — their start/end times collide.")

            # a car pick-up / drop-off clashing with an activity or transport
            # is a soft conflict (warning), not a hard overlap error
            if day_date:
                occupied = [(s, e) for s, e, _ in spans]
                self._car_event_conflicts(car_rentals, day_date, occupied)

        # (7) a day whose schedule runs past midnight
        default_start = self._default_start_min()
        for di, day in enumerate(days):
            if not isinstance(day, dict):
                continue
            total = 0
            for act in day.get("activities", []) or []:
                if not isinstance(act, dict):
                    continue
                if act.get("type") == "buffer":
                    total += _dur(act.get("duration")) or 0
                    continue
                d = _dur(act.get("duration"))
                if d is None:
                    sp = _span(act)
                    d = (sp[1] - sp[0]) if sp else 0
                total += d or 0
            if total and default_start + total > 1440:
                self.add("error", ("days", di), "the day's activities run past "
                         "midnight — the schedule doesn't fit in a single day.")

        # activities ending after the day's default end_time
        df = self.data.get("default") if isinstance(self.data.get("default"), dict) else {}
        end_raw = df.get("end_time", self.data.get("default_end_time"))
        if end_raw is not None:
            try:
                day_end = _parse_time(end_raw)
            except ItineraryError:
                day_end = None
            if day_end is not None:
                self._check_end_of_day(day_end)

    def _check_end_of_day(self, day_end):
        """Warn about any activity whose computed end time is after the day's
        `default.end_time`. Needs the scheduled times, so it builds the model;
        skipped if the data can't be built (bigger errors exist)."""
        try:
            itinerary = Itinerary.from_dict(self.data)
        except ItineraryError:
            return
        days_raw = self.data.get("days") or []
        for di, built in enumerate(itinerary.days):
            if di >= len(days_raw) or not isinstance(days_raw[di], dict):
                continue
            raw_idx = [
                j for j, a in enumerate(days_raw[di].get("activities", []) or [])
                if isinstance(a, dict) and a.get("type") != "buffer"
            ]
            built_acts = [a for a in built.activities if a.kind != "buffer"]
            for j, act in zip(raw_idx, built_acts):
                if act.end_time and act.end_time > day_end:
                    self.add("warning", ("days", di, "activities", j),
                             "this activity ends at {end}, after the day's "
                             "end_time ({day_end}).",
                             end=f"{act.end_time:%H:%M}",
                             day_end=f"{day_end:%H:%M}")


def validate_text(text: str, lang: str = DEFAULT_LANGUAGE) -> list[Finding]:
    try:
        data, lines = load_with_lines(text)
    except JSONPositionError as exc:
        return [Finding("error", None,
                        tr("invalid JSON — {error}", lang).format(error=exc))]
    return _Validator(data, lines, lang).run()
