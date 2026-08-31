"""The validator: walks the parsed data (with line numbers) and emits findings."""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta

from ..lang import DEFAULT_LANGUAGE, fmt_weekday_runs, tr, weekday_name
from ..models import (
    NESTED_ACTIVITY_TYPES,
    Itinerary,
    ItineraryError,
    _format_duration,
    _parse_date,
    _parse_duration,
    _parse_route,
    _parse_time,
    _parse_tz,
    gpx_track,
)
from .findings import Finding
from .jsonpos import JSONPositionError, load_with_lines
from .specs import (
    ACCOMMODATION_SPECS,
    ACTIVITY_SPECS,
    CAR_RENTAL_SPECS,
    DAY_SPECS,
    DEFAULTS,
    PLACE_SCHEDULE,
    SCHEDULE,
    TRANSPORT_SPECS,
    TRAVEL_DESCRIPTION,
    V_BOOL,
    V_COORDINATE,
    V_CURRENCY,
    V_DUR,
    V_ISO_COUNTRY,
    V_NUMBER,
)

# coordinate object keys accepted on itinerary objects (point + segment endpoints)
COORDINATE_KEYS = (
    "coordinate", "start_coordinate", "end_coordinate",
    "pickup_coordinate", "dropoff_coordinate",
)

# The parenthetical ``({error})`` detail comes from the value parsers/checks as a
# fully-formatted English string, so it can't be looked up verbatim once a value
# is interpolated. Each entry maps the English form back to a translatable
# template (with named groups) so the validator can localize it: match → the
# template's translation is re-``.format``ed with the captured pieces. Static
# check() returns (no interpolation) translate directly and never reach here.
# Order matters — the broad "{name} must be a number" pattern must come last.
_ERROR_TEMPLATES = [
    (re.compile(r"^Invalid date (?P<value>.+), expected YYYY-MM-DD$"),
     "Invalid date {value}, expected YYYY-MM-DD"),
    (re.compile(r"^Invalid time (?P<value>.+), expected HH:MM$"),
     "Invalid time {value}, expected HH:MM"),
    (re.compile(r"^Invalid timezone (?P<value>.+), expected e\.g\. "
                r"'\+02:00' or 'UTC-3'$"),
     "Invalid timezone {value}, expected e.g. '+02:00' or 'UTC-3'"),
    (re.compile(r"^Could not parse duration (?P<value>.+)$"),
     "Could not parse duration {value}"),
    (re.compile(r"^hike route must be 'loop', 'back_and_forth' or 'one_way', "
                r"got (?P<value>.+)$"),
     "hike route must be 'loop', 'back_and_forth' or 'one_way', got {value}"),
    (re.compile(r"^paid must be 'paid' or 'to pay', got (?P<value>.+)$"),
     "paid must be 'paid' or 'to pay', got {value}"),
    (re.compile(r"^(?P<name>.+) must be an object with 'lat' and 'long'$"),
     "{name} must be an object with 'lat' and 'long'"),
    (re.compile(r"^(?P<name>.+) needs both 'lat' and 'long'$"),
     "{name} needs both 'lat' and 'long'"),
    (re.compile(r"^(?P<name>.+)\.lat must be between -90 and 90 "
                r"\(got (?P<value>.+)\)$"),
     "{name}.lat must be between -90 and 90 (got {value})"),
    (re.compile(r"^(?P<name>.+)\.long must be between -180 and 180 "
                r"\(got (?P<value>.+)\)$"),
     "{name}.long must be between -180 and 180 (got {value})"),
    # a point of interest's opening days/hours (models/opening.py) — one template
    # per field, with the (short) offending value echoed whole
    (re.compile(r"^Invalid opening_days (?P<value>.+), expected weekday names "
                r"like 'tue-sun', 'monday, thursday' or 'mon-fri, sun'$"),
     "Invalid opening_days {value}, expected weekday names like 'tue-sun', "
     "'monday, thursday' or 'mon-fri, sun'"),
    (re.compile(r"^Invalid opening_hours (?P<value>.+), expected time ranges "
                r"like '09:30-18:00' or '09:30-12:30, 14:00-18:00'$"),
     "Invalid opening_hours {value}, expected time ranges like '09:30-18:00' "
     "or '09:30-12:30, 14:00-18:00'"),
    (re.compile(r"^opening_hours range (?P<value>.+) opens and closes at the "
                r"same time — give the closing time, or drop the range$"),
     "opening_hours range {value} opens and closes at the same time — give the "
     "closing time, or drop the range"),
    (re.compile(r"^(?P<name>.+) must be a number, got (?P<value>.+)$"),
     "{name} must be a number, got {value}"),
    # a hike's embedded GPX (models/gpx.py) — the wrapper is ours, the
    # parenthesised {detail} is the stdlib decoder's and stays English
    (re.compile(r"^'gpx' is not valid base64 \((?P<detail>.+)\) — encode the "
                r"\.gpx file with base64$"),
     "'gpx' is not valid base64 ({detail}) — encode the .gpx file with base64"),
    (re.compile(r"^'gpx' is gzip data but won't inflate \((?P<detail>.+)\)$"),
     "'gpx' is gzip data but won't inflate ({detail})"),
    (re.compile(r"^'gpx' is not parseable XML \((?P<detail>.+)\)$"),
     "'gpx' is not parseable XML ({detail})"),
]


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


def _obj_minutes(obj):
    """An activity's length in minutes from explicit fields (a `duration`, or a
    start/end span), or None when it can't be determined."""
    d = _dur(obj.get("duration"))
    if d is not None:
        return d
    sp = _span(obj)
    return (sp[1] - sp[0]) if sp else None


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


# Longest value echoed back in a finding. A field like a hike's base64 `gpx` runs
# to tens of thousands of characters, and quoting the whole blob would bury the
# message it belongs to (and every finding after it).
_MAX_SHOWN = 60


def _shown(value) -> str:
    """``repr(value)``, elided in the middle when it's too long to quote — the
    two ends are what identifies a value, and they're what a reader compares
    against their file."""
    text = repr(value)
    if len(text) <= _MAX_SHOWN:
        return text
    keep = (_MAX_SHOWN - 3) // 2
    return f"{text[:keep]}...{text[-keep:]}"


def _truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "yes", "1", "paid", "paid online")


_UNBUILT = object()  # "the model hasn't been built yet" (None means "won't build")


class _Validator:
    def __init__(self, data, lines, lang=DEFAULT_LANGUAGE):
        self.data = data
        self.lines = lines
        self.lang = lang
        self.findings: list[Finding] = []
        self._gpx_cache: dict[int, object] = {}  # id(hike dict) -> GpxTrack | None
        self._model_cache = _UNBUILT

    def t(self, text):
        return tr(text, self.lang)

    def _terr(self, err):
        """Translate the ``({error})`` detail from a value check/parser. Static
        messages translate directly; a formatted parser error (with an
        interpolated value) is matched back to a template, whose translation is
        re-formatted with the captured pieces. Falls back to English."""
        if not err:
            return err
        direct = self.t(err)
        if direct != err:  # a verbatim translation exists
            return direct
        for rx, template in _ERROR_TEMPLATES:
            m = rx.match(err)
            if m:
                try:
                    return self.t(template).format(**m.groupdict())
                except (KeyError, IndexError, ValueError):
                    return err  # never let a bad template break validation
        return err

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
                            name=spec.name, value=_shown(value), description=desc,
                            expected=expected, error=self._terr(err))))
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

        df = data.get("defaults")
        df_path = ("defaults",) if isinstance(df, dict) else ()
        df_obj = df if isinstance(df, dict) else {}
        self.check_object(df_obj, df_path or (), DEFAULTS)
        self._secondary_currencies(df_obj, df_path or ())
        self._inference_countries(df_obj, df_path or ())
        self._walk_coordinates(data, ())
        self._maps_coherence(df_obj, df_path or ())
        self._buffer_coherence(df_obj, df_path or ())

        days = data.get("days")
        if not isinstance(days, list) or not days:
            self.add("error", ("days",) if "days" in data else (),
                     "required field 'days' is missing or empty — the list of "
                     "days. Expected a non-empty array of day objects.")
        else:
            for i, day in enumerate(days):
                self._day(day, ("days", i))

        transport = data.get("transport")
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
            self.check_object(act, path,
                              PLACE_SCHEDULE if kind == "place" else SCHEDULE)
            self._time_consistency(act, path, tz_aware=False)
        self._magnitudes(act, path, kind)
        if kind == "buffer":
            if _dur(act.get("duration")) == 0:
                self.add("info", path, "this is a zero-minute buffer — it only "
                         "suppresses the trip's default buffer here and draws no line.")
        if kind == "hike":
            self._hike_route_endpoints(act, path)
            self._hike_gpx(act, path)
        if kind == "road":
            self._road_waypoints(act, path)
        if kind == "meal" and act.get("restaurant") and act.get("area"):
            self.add("warning", path, "both 'restaurant' and 'area' are set — "
                     "'area' is ignored when a restaurant is named.")
        if kind in NESTED_ACTIVITY_TYPES:
            self._nested_activities(act, kind, path)
            self._nested_duration_fit(act, path)
        if kind != "buffer":
            self._magnitude_warning(act, path, kind)

    def _magnitude_warning(self, act, path, kind):
        """Warn about the size an activity conveys. A point of interest or place
        warns only when it has no determinable duration; a road or hike is
        expected to give *each* of its magnitude fields (a duration plus
        distance — and, for a hike, elevation) and warns naming any that are
        missing. A duration counts as known when it is given or inferable from
        the start/end times (or, for a road, from its waypoints)."""
        dur_known = _obj_minutes(act) is not None
        if kind == "road":
            wps = act.get("waypoints")
            legs = self._road_legs(str(act.get("start", "")).strip(),
                                   wps if isinstance(wps, list) else [])
            if len(legs) <= 1:
                # a plain departure → arrival drive: the whole road is one leg,
                # so its own duration/distance (or the sole leg's) covers it
                src, dest, has_dur, has_dist = (legs[0] if legs
                                                else (act.get("start"), None, False, False))
                dur_ok = dur_known or has_dur
                dist_ok = act.get("distance_km") is not None or has_dist
                missing = ([] if dur_ok else ["duration"]) + \
                          ([] if dist_ok else ["distance_km"])
                if missing:
                    self.add("warning", path, "this road ({route}) should give a "
                             "duration and a 'distance_km' — missing: {missing}.",
                             route=self._leg_label(src, dest),
                             missing=", ".join(missing))
            else:
                # a multi-stop drive: each named leg is shown on its own, so each
                # should carry its own duration and distance
                for src, dest, has_dur, has_dist in legs:
                    if dest is None:
                        continue  # a trailing unnamed (route-shaping) arrival
                    missing = ([] if has_dur else ["duration"]) + \
                              ([] if has_dist else ["distance_km"])
                    if missing:
                        self.add("warning", path, "this road's leg ({route}) should "
                                 "give a duration and a 'distance_km' — missing: "
                                 "{missing}.", route=self._leg_label(src, dest),
                                 missing=", ".join(missing))
        elif kind == "hike":
            # An embedded GPX measured the walk, so it stands in for the figures
            # it supplies: the distance always, the elevation gain only when the
            # file actually carries elevations.
            track = self._gpx_of(act)
            missing = [] if dur_known else ["duration"]
            if act.get("distance_km") is None and track is None:
                missing.append("distance_km")
            if act.get("elevation_m") is None and (
                    track is None or not track.has_elevation):
                missing.append("elevation_m")
            if missing:
                self.add("warning", path, "this hike ({name}) should give a "
                         "duration, a 'distance_km' and an 'elevation_m' — missing: "
                         "{missing}.", name=self._name_of(act),
                         missing=", ".join(missing))
        elif kind in ("point_of_interest", "place"):
            if not dur_known and not self._nested_duration(act):
                self.add("warning", path, "this activity ({name}) has no duration "
                         "and none can be inferred from its start/end times — add a "
                         "'duration', or a 'start_time' and 'end_time'.",
                         name=self._name_of(act))

    @staticmethod
    def _nested_duration(act):
        """True if a container's length is conveyed by a nested activity that
        itself has a determinable duration."""
        nested = act.get("activities")
        if not isinstance(nested, list):
            return False
        return any(isinstance(s, dict) and _obj_minutes(s) is not None
                   for s in nested)

    @staticmethod
    def _road_legs(start, waypoints):
        """Group raw waypoint dicts into display legs, mirroring the PDF: an
        unnamed (route-shaping) waypoint merges forward into the next named one,
        its duration/distance folded into that leg. Returns a list of
        ``(src, dest_or_None, has_duration, has_distance)`` — one per leg; ``src``
        is the previous named point (or the road ``start`` for the first leg) and
        ``dest`` is ``None`` for a trailing run of unnamed waypoints (an unnamed
        arrival)."""
        legs = []
        prev = start
        has_dur = has_dist = pending = False
        for wp in waypoints:
            if not isinstance(wp, dict):
                continue
            pending = True
            if _dur(wp.get("duration")) is not None:
                has_dur = True
            if wp.get("distance_km") is not None:
                has_dist = True
            loc = str(wp.get("location", "")).strip()
            if loc:
                legs.append((prev, loc, has_dur, has_dist))
                prev = loc
                has_dur = has_dist = pending = False
        if pending:
            legs.append((prev, None, has_dur, has_dist))
        return legs

    @staticmethod
    def _name_of(act):
        return str(act.get("name", "")).strip() or "?"

    @staticmethod
    def _leg_label(src, dest):
        return f"{src or '?'} → {dest or '?'}"

    def _nested_duration_fit(self, act, path):
        """Warn when the nested activities' total (explicit) length exceeds the
        container's own duration — they can't all fit inside it."""
        nested = act.get("activities")
        if not isinstance(nested, list) or not nested:
            return
        parent = _obj_minutes(act)
        if parent is None:
            return
        total, known = 0, False
        for sub in nested:
            if not isinstance(sub, dict):
                continue
            m = _obj_minutes(sub)
            if m is not None:
                total += m
                known = True
        if known and total > parent:
            self.add("warning", path, "the nested activities last {total} in total, "
                     "longer than this activity's {parent} — they can't all fit "
                     "inside it.", total=_format_duration(total),
                     parent=_format_duration(parent))

    def _nested_activities(self, act, container_kind, path):
        """Validate the ``activities`` nested under a container (road / hike /
        place / point of interest). Each entry must be an object whose ``type``
        is one of the container's allowed nested types, and nesting is only one
        level deep — a nested activity must not carry activities of its own."""
        nested = act.get("activities")
        if not isinstance(nested, list):
            return
        allowed = ", ".join(NESTED_ACTIVITY_TYPES[container_kind])
        for k, sub in enumerate(nested):
            spath = path + ("activities", k)
            if not isinstance(sub, dict):
                self.add("error", spath, "a nested activity must be an object with "
                         "a 'type' of one of: {allowed}.", allowed=allowed)
                continue
            kind = sub.get("type")
            if kind not in NESTED_ACTIVITY_TYPES[container_kind]:
                self.add("error", spath + ("type",) if "type" in sub else spath,
                         "a nested activity 'type' must be one of: {allowed} "
                         "(got {kind}).", allowed=allowed, kind=repr(kind))
                continue
            self.check_object(sub, spath, ACTIVITY_SPECS[kind], skip_optional=True)
            if kind == "hike":
                self._hike_route_endpoints(sub, spath)
                self._hike_gpx(sub, spath)
                self._magnitude_warning(sub, spath, kind)
            if kind == "meal" and sub.get("restaurant") and sub.get("area"):
                self.add("warning", spath, "both 'restaurant' and 'area' are set — "
                         "'area' is ignored when a restaurant is named.")
            if sub.get("activities"):
                self.add("error", spath, "a nested activity can't contain its own "
                         "nested activities — nesting is only one level deep.")

    def _road_waypoints(self, act, path):
        """Validate a road's optional ``waypoints`` — each an object with a
        required ``coordinate`` and optional ``location`` / ``duration`` /
        ``distance_km`` / ``off_road`` (all three describing the leg *reaching*
        that waypoint). Warns when the segment durations sum past the road's
        own duration (they can't fit the drive)."""
        raw = act.get("waypoints")
        if raw is None:
            return  # required-field-missing is reported by check_object
        if not isinstance(raw, list):
            self.add("error", path + ("waypoints",),
                     "'waypoints' must be an array of {coordinate, location, "
                     "duration, distance_km, off_road} objects.")
            return
        if not raw:
            self.add("error", path + ("waypoints",),
                     "a road needs at least one 'waypoint' — the route's final "
                     "stop is the arrival.")
            return
        total, known = 0, False
        for k, wp in enumerate(raw):
            wpath = path + ("waypoints", k)
            if not isinstance(wp, dict):
                self.add("error", wpath, "each waypoint must be an object with a "
                         "'coordinate' (a {lat, long} point on the route).")
                continue
            if wp.get("coordinate") in (None, ""):
                self.add("error", wpath, "a waypoint needs a 'coordinate' (a "
                         "{lat, long} object) — it sets a point on the route.")
            dk = wp.get("distance_km")
            if dk is not None:
                err = V_NUMBER(dk)
                if err:
                    self.add("error", wpath + ("distance_km",),
                             "field '{name}' is invalid ({value}) — {error}.",
                             name="distance_km", value=repr(dk), error=self._terr(err))
                elif float(dk) <= 0:
                    self.add("error", wpath + ("distance_km",),
                             "distance_km must be a positive number (got {value}).",
                             value=dk)
            off = wp.get("off_road")
            if off is not None:
                err = V_BOOL(off)
                if err:
                    self.add("error", wpath + ("off_road",),
                             "field '{name}' is invalid ({value}) — {error}.",
                             name="off_road", value=repr(off), error=self._terr(err))
            dur = wp.get("duration")
            if dur is not None:
                err = V_DUR(dur)
                if err:
                    self.add("error", wpath + ("duration",),
                             "field '{name}' is invalid ({value}) — {error}.",
                             name="duration", value=repr(dur), error=self._terr(err))
                else:
                    d = _dur(dur)
                    if d is not None:
                        total += d
                        known = True
        parent = _obj_minutes(act)
        if known and parent is not None and total > parent:
            self.add("warning", path, "the waypoint segments last {total} in "
                     "total, longer than the road's {parent} — the segment times "
                     "don't fit the drive.", total=_format_duration(total),
                     parent=_format_duration(parent))

    def _transport(self, t, path):
        if not isinstance(t, dict):
            self.add("error", path, "each transport must be an object")
            return
        self.check_object(t, path, TRANSPORT_SPECS)
        self._time_consistency(t, path, tz_aware=True)
        self._magnitudes(t, path, "transport")
        if _tmin(t.get("start_time")) is not None and _obj_minutes(t) is None:
            self.add("warning", path, "this transport has no duration and none can "
                     "be inferred from its start/end times — add a 'duration', or "
                     "an 'end_time'.")
        sd, ed = _date(t.get("start_date")), _date(t.get("end_date"))
        if sd and ed and ed < sd:
            self.add("error", path, "transport end_date ({ed}) is before "
                     "start_date ({sd}).", ed=ed, sd=sd)
        ttype = str(t.get("type", "")).strip().lower()
        if t.get("flight_number") and ttype and ttype != "plane":
            self.add("warning", path, "'flight_number' is set but the transport "
                     "type is '{type}', not 'plane'.", type=ttype)
        if t.get("train_number") and ttype and ttype != "train":
            self.add("warning", path, "'train_number' is set but the transport "
                     "type is '{type}', not 'train'.", type=ttype)
        if t.get("status") and not t.get("booking_number"):
            self.add("warning", path, "'status' is set but 'booking_number' is "
                     "missing — a confirmed/booked leg usually has a reference.")
        if t.get("paid") is not None and not self._has_price(t):
            self.add("warning", path, "'paid' is set but 'price' is missing — the "
                     "payment state is given without an amount.")
        self._check_price_currency(t, path)

    def _accommodation(self, a, path):
        if not isinstance(a, dict):
            self.add("error", path, "each accommodation must be an object")
            return
        self.check_object(a, path, ACCOMMODATION_SPECS)
        arr, dep = _date(a.get("arrival")), _date(a.get("departure"))
        if arr and dep and dep <= arr:
            self.add("error", path, "accommodation departure ({dep}) must be "
                     "after arrival ({arr}).", dep=dep, arr=arr)
        if a.get("status") and not a.get("booking_source"):
            self.add("warning", path, "'status' is set but 'booking_source' is "
                     "missing — a confirmed/booked stay usually has a reference.")
        if a.get("paid") is not None and not self._has_price(a):
            self.add("warning", path, "'paid' is set but 'price' is missing — the "
                     "payment state is given without an amount.")
        self._check_price_currency(a, path)

    def _defaults(self):
        """The trip-wide defaults object."""
        df = self.data.get("defaults")
        return df if isinstance(df, dict) else {}

    def _default_currency(self):
        return str(self._defaults().get("currency", "EUR")).strip().upper() or "EUR"

    def _known_currencies(self):
        """The default currency plus every secondary currency's code."""
        codes = {self._default_currency()}
        raw = self._defaults().get("secondary_currencies")
        if isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, dict) and entry.get("currency"):
                    codes.add(str(entry.get("currency")).strip().upper())
        return codes

    def _secondary_currencies(self, df, base_path):
        """Validate the ``secondary_currencies`` array in the defaults object:
        each entry needs a currency code and a positive numeric change rate."""
        raw = df.get("secondary_currencies")
        if raw is None:
            return
        if not isinstance(raw, list):
            self.add("error", base_path + ("secondary_currencies",),
                     "'secondary_currencies' must be an array of "
                     "{currency, change_rate} objects.")
            return
        for i, entry in enumerate(raw):
            epath = base_path + ("secondary_currencies", i)
            if not isinstance(entry, dict):
                self.add("error", epath, "each secondary currency must be an "
                         "object with a 'currency' and a 'change_rate'.")
                continue
            cur = entry.get("currency")
            if cur in (None, ""):
                self.add("error", epath, "a secondary currency needs a 'currency' "
                         "(a 3-letter ISO code like 'USD').")
            elif V_CURRENCY(cur):
                self.add("error", epath + ("currency",),
                         "field 'currency' is invalid ({value}) — {error}.",
                         value=repr(cur), error=self._terr(V_CURRENCY(cur)))
            rate = entry.get("change_rate")
            if rate in (None, ""):
                self.add("error", epath, "a secondary currency needs a "
                         "'change_rate' (units of it per 1 unit of the default).")
            elif V_NUMBER(rate):
                self.add("error", epath + ("change_rate",), "field 'change_rate' "
                         "is invalid ({value}) — must be a number.", value=repr(rate))
            elif float(rate) <= 0:
                self.add("error", epath + ("change_rate",),
                         "change_rate must be a positive number (got {value}).",
                         value=repr(rate))

    def _inference_countries(self, df, base_path):
        """Validate ``inference_countries`` — a list of 2-letter ISO codes."""
        raw = df.get("inference_countries")
        if raw is None:
            return
        entries = [raw] if isinstance(raw, str) else raw
        if not isinstance(entries, list):
            self.add("error", base_path + ("inference_countries",),
                     "'inference_countries' must be an array of 2-letter ISO "
                     "country codes like ['FR'].")
            return
        for i, code in enumerate(entries):
            err = V_ISO_COUNTRY(code)
            if err:
                self.add("error", base_path + ("inference_countries", i),
                         "inference country {value} is invalid — {error}.",
                         value=repr(code), error=self._terr(err))

    def _buffer_coherence(self, df, df_path):
        """``buffer`` and ``auto_sized_buffer`` are two answers to the same
        question — how much room to leave between two activities — so setting
        both is a contradiction rather than a combination. The auto-sized one
        wins; say so where the ignored value sits."""
        if df.get("buffer") in (None, ""):
            return
        if "auto_sized_buffer" in df and not _truthy(df.get("auto_sized_buffer")):
            return  # auto-sizing is off: the fixed buffer is the one in charge
        self.add("warning", df_path + ("buffer",),
                 "'buffer' is ignored — 'auto_sized_buffer' is on (it is by "
                 "default) and sizes the buffers to fill the day instead. Drop one "
                 "of the two.")

    def _maps_coherence(self, df, df_path):
        """Soft checks that only apply when maps are on: a located activity with
        no coordinate won't be mapped, and inference_countries is dead weight
        when inference is off."""
        if not _truthy(df.get("include_maps_in_render")):
            return
        infer = _truthy(df.get("infer_coordinates_from_address"))
        if df.get("inference_countries") and not infer:
            self.add("warning", df_path + ("inference_countries",),
                     "'inference_countries' is set but "
                     "'infer_coordinates_from_address' is off — it is ignored.")
        located = ("point_of_interest", "place", "hike", "meal")
        days = self.data.get("days")
        for di, day in enumerate(days if isinstance(days, list) else []):
            if not isinstance(day, dict):
                continue
            for ai, act in enumerate(day.get("activities", []) or []):
                if not isinstance(act, dict) or act.get("type") not in located:
                    continue
                if "coordinate" in act:
                    continue
                path = ("days", di, "activities", ai)
                if (act.get("type") == "place" and not infer
                        and self._has_shown_sub_coordinate(act)):
                    self.add("info", path, "this area has no 'coordinate' of its "
                             "own — its map pin will be placed at the average "
                             "position of its located sub-activities.")
                    continue
                if not infer:
                    self.add("info", path, "maps are on but this activity has no "
                             "'coordinate' and inference is off — it won't appear "
                             "on the day map.")
                elif not (act.get("name") or act.get("address")
                          or act.get("restaurant") or act.get("area")):
                    self.add("info", path, "maps are on but this activity has no "
                             "'coordinate' and nothing to geocode — it won't appear "
                             "on the day map.")

    def _has_shown_sub_coordinate(self, act):
        """True if any of a place's nested activities carries an explicit
        coordinate that would be plotted. Such a place can be centered on the
        average of those sub-points even without a coordinate of its own."""
        for sub in act.get("activities", []) or []:
            if not isinstance(sub, dict):
                continue
            coord = sub.get("coordinate")
            if isinstance(coord, dict) and _truthy(coord.get("show_on_map", True)):
                return True
        return False

    def _walk_coordinates(self, node, path):
        """Recursively validate every coordinate object (``coordinate`` and the
        segment endpoint variants) wherever it appears in the document."""
        if isinstance(node, dict):
            for key, value in node.items():
                child = path + (key,)
                if key in COORDINATE_KEYS:
                    err = V_COORDINATE(value)
                    if err:
                        self.add("error", child,
                                 "field '{name}' is invalid — {error}.",
                                 name=key, error=self._terr(err))
                else:
                    self._walk_coordinates(value, child)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                self._walk_coordinates(item, path + (i,))

    def _check_price_currency(self, obj, path):
        """A price's explicit ``currency`` must be the default or a declared
        secondary currency — otherwise there's no rate to convert it."""
        cur = obj.get("currency")
        if cur in (None, ""):
            return
        code = str(cur).strip().upper()
        if V_CURRENCY(cur):  # malformed code — the field check already reported it
            return
        if code not in self._known_currencies():
            self.add("error", path + ("currency",),
                     "price currency '{cur}' is neither the default currency "
                     "({default}) nor a declared secondary currency — add it to "
                     "defaults.secondary_currencies or use a known currency.",
                     cur=code, default=self._default_currency())

    def _has_price(self, obj):
        return obj.get("price") not in (None, "")

    def _default_tz(self):
        df = self._defaults()
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
        if cr.get("status") and not cr.get("booking_number"):
            self.add("warning", path, "'status' is set but 'booking_number' is "
                     "missing — a confirmed/booked leg usually has a reference.")
        if cr.get("paid") is not None and not self._has_price(cr):
            self.add("warning", path, "'paid' is set but 'price' is missing — the "
                     "payment state is given without an amount.")
        self._check_price_currency(cr, path)

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

    def _gpx_of(self, act):
        """The parsed :class:`GpxTrack` behind a hike's ``gpx``, or ``None`` when
        it has none or it doesn't parse (the field check reports that). Memoized
        per activity object: a recorded track is thousands of points, and both
        the coherence check and the magnitude warning want to know about it."""
        raw = act.get("gpx")
        if raw in (None, ""):
            return None
        key = id(act)
        if key not in self._gpx_cache:
            try:
                self._gpx_cache[key] = gpx_track(raw)
            except ItineraryError:
                self._gpx_cache[key] = None
        return self._gpx_cache[key]

    def _hike_gpx(self, act, path):
        """What an embedded GPX does and doesn't give the hike. The field's own
        check reports a blob that won't decode; this reports the two things a
        *valid* one can still leave out."""
        track = self._gpx_of(act)
        if track is None:
            return
        if not track.has_elevation:
            self.add("info", path + ("gpx",), "this GPX carries no elevations — "
                     "the trail map is drawn, but not the elevation profile.")
        if not _truthy(self._defaults().get("include_hike_maps", True)):
            self.add("info", path + ("gpx",), "'include_hike_maps' is off, so this "
                     "GPX is parsed but neither the trail map nor the profile is "
                     "drawn.")

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
        df = self._defaults()
        raw = df.get("start_time")
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
                self.add("info", ("days", i),
                         "the night of {d} has both an accommodation and an "
                         "overnight transport — using the accommodation.", d=d)
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
            # A sweep over the start-ordered spans, tracking the furthest end
            # seen so far: any span starting before that end overlaps an earlier
            # item (not necessarily the immediately preceding one — a long item
            # can straddle a later, non-adjacent one).
            spans.sort(key=lambda s: (s[0], s[1]))
            max_end = None
            for start, end, path in spans:
                if max_end is not None and start < max_end:
                    self.add("error", path, "this overlaps an earlier item on the "
                             "day's timeline — their start/end times collide.")
                if max_end is None or end > max_end:
                    max_end = end

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

        # activities ending after the day's end_time (18:00 unless it says)
        try:
            day_end = _parse_time(self._defaults().get("end_time")) or time(18, 0)
        except ItineraryError:
            day_end = None  # invalid value, already reported as an error
        if day_end is not None:
            self._check_end_of_day(day_end)

        # a point of interest visited when it's shut (needs the resolved times)
        self._check_opening()

    def _model(self):
        """The built itinerary — the only place the *resolved* times and dates a
        day's timeline assigns can be read — or ``None`` when the data won't
        build (bigger errors exist, and they're already reported). Built at most
        once: two checks want it, and building walks the whole document."""
        if self._model_cache is _UNBUILT:
            try:
                self._model_cache = Itinerary.from_dict(self.data)
            except ItineraryError:
                self._model_cache = None
        return self._model_cache

    def _resolved_activities(self):
        """Yield ``(built_day, raw_path, built_activity)`` for every non-buffer
        activity of every day, nested ones included — resolved values matched
        back to the line the raw JSON sits on.

        The timeline walk neither drops nor reorders real activities (it only
        inserts and merges buffers), and nested activities are never put on the
        timeline at all, so zipping the raw and built lists lines them up."""
        itinerary = self._model()
        if itinerary is None:
            return
        days_raw = self.data.get("days") or []
        for di, day in enumerate(itinerary.days):
            if di >= len(days_raw) or not isinstance(days_raw[di], dict):
                continue
            raw_acts = days_raw[di].get("activities") or []
            raw_idx = [j for j, a in enumerate(raw_acts)
                       if isinstance(a, dict) and a.get("type") != "buffer"]
            built_acts = [a for a in day.activities if a.kind != "buffer"]
            for j, act in zip(raw_idx, built_acts):
                path = ("days", di, "activities", j)
                yield day, path, act
                raw_nested = raw_acts[j].get("activities") or []
                built_nested = getattr(act, "activities", None) or []
                for k, sub in enumerate(built_nested):
                    if k < len(raw_nested):
                        yield day, path + ("activities", k), sub

    def _check_opening(self):
        """Warn when a point of interest is visited on a day it doesn't open, or
        at an hour it isn't open.

        Reads the resolved timeline rather than the raw JSON: a visit's start
        time is usually *inferred* from the activities before it, so checking
        what the file states would only catch the few stops that pin one. A
        nested stop is never scheduled, so it has a time only if it says so —
        the weekday check still applies to it either way."""
        for day, path, act in self._resolved_activities():
            opening = getattr(act, "opening", None)
            if opening is None:
                continue
            if opening.closed_on(day.date):
                self.add("warning", path,
                         "this visit falls on a {weekday}, but '{name}' only "
                         "opens {days} — it will be closed.",
                         weekday=weekday_name(day.date, self.lang),
                         name=act.title,
                         days=fmt_weekday_runs(opening.day_runs, self.lang,
                                               abbr=False))
            if not opening.covers(act.start_time, act.end_time):
                self.add("warning", path,
                         "this visit ({visit}) falls outside the opening hours "
                         "of '{name}' ({hours}).",
                         visit=act.time_range or f"{act.start_time:%H:%M}",
                         name=act.title, hours=opening.hours_display)

    def _check_end_of_day(self, day_end):
        """Warn about any activity whose computed end time is after the day's
        `default.end_time`. Needs the scheduled times, so it builds the model;
        skipped if the data can't be built (bigger errors exist)."""
        itinerary = self._model()
        if itinerary is None:
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


# The "kind" of each stitch fragment file, used to pick which per-object check
# to run when validating one file on its own.
FRAGMENT_KINDS = ("travel_description", "defaults", "day", "transport",
                  "accommodation", "car_rental")


def _check_fragment(v: _Validator, obj, base, kind: str) -> None:
    """Run the per-object validation appropriate for a single fragment ``obj``
    at path ``base`` (so its line numbers stay relative to the fragment file)."""
    if kind == "travel_description":
        v.check_object(obj, base, TRAVEL_DESCRIPTION)
    elif kind == "defaults":
        v.check_object(obj, base, DEFAULTS)
        v._secondary_currencies(obj, base)
        v._inference_countries(obj, base)
    elif kind == "day":
        v._day(obj, base)
    elif kind == "transport":
        v._transport(obj, base)
    elif kind == "accommodation":
        v._accommodation(obj, base)
    elif kind == "car_rental":
        v._car_rental(obj, base)
    else:
        raise ValueError(f"unknown fragment kind: {kind!r}")


def validate_fragment(text: str, kind: str, lang: str = DEFAULT_LANGUAGE,
                      defaults: dict | None = None) -> list[Finding]:
    """Validate a single stitch fragment file (a ``travel_description`` /
    ``defaults`` object, or one entry of a ``day`` / ``transport`` /
    ``accommodation`` / ``car_rental`` array) *in isolation*.

    Line numbers in the returned findings are relative to ``text`` — the
    fragment file you actually edit — which is the whole point of checking each
    piece before it is merged. ``defaults`` is the trip's already-parsed
    ``defaults`` dict (or None); it is fed in so the cross-cutting checks that
    read it (price currency, timezone) behave as they will after stitching.

    A single array file that holds a JSON list is validated element by element.
    """
    try:
        data, lines = load_with_lines(text)
    except JSONPositionError as exc:
        return [Finding("error", None,
                        tr("invalid JSON — {error}", lang).format(error=exc))]
    seed = {"defaults": defaults} if isinstance(defaults, dict) else {}
    v = _Validator(seed, lines, lang)
    if kind in ("travel_description", "defaults"):
        if not isinstance(data, dict):
            v.add("error", (), "this fragment must be a JSON object.")
        else:
            _check_fragment(v, data, (), kind)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _check_fragment(v, item, (i,), kind)
    else:
        _check_fragment(v, data, (), kind)
    return v.findings
