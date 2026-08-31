"""Activity types (road / point_of_interest / place / hike / meal / buffer) and
the day-scheduling pass."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time

from .geo import Coordinate, _parse_coordinate
from .gpx import GpxTrack, gpx_track
from .parsers import (
    ItineraryError,
    _add_minutes,
    _diff_minutes,
    _format_duration,
    _parse_bool,
    _parse_duration,
    _parse_float,
    _parse_route,
    _parse_time,
    _parse_tz,
)
from .scheduling import Scheduled


@dataclass
class Activity(Scheduled):
    """An item on a day's timeline: the shared :class:`Scheduled` fields plus an
    optional map location."""

    coordinate: Coordinate | None = None  # optional map location


def _sched(d: dict) -> dict:
    """Extract the raw (pre-inference) scheduling fields from an activity dict."""
    return {
        "start_time": _parse_time(d.get("start_time")),
        "end_time": _parse_time(d.get("end_time")),
        "duration_min": _parse_duration(d.get("duration")),
        "start_tz": _parse_tz(d.get("start_tz")),
        "end_tz": _parse_tz(d.get("end_tz")),
        "coordinate": _parse_coordinate(d.get("coordinate")),
    }


def _pages(d: dict) -> str:
    """The optional ``guidebook_pages`` of an activity — the page(s) of the trip's
    guidebook covering it, kept as free text so any of ``14`` / ``15-18`` /
    ``16, 23, 25-30`` round-trips untouched (the validator checks the shape; the
    model only normalizes the whitespace)."""
    return str(d.get("guidebook_pages", "")).strip()


@dataclass
class Buffer(Activity):
    """Free time between two activities (travel, rest, a meal).

    ``auto`` is True when the buffer was inserted automatically — either the
    trip's default buffer or a gap inferred from an explicit ``start_time``.
    """

    kind = "buffer"
    auto: bool = False

    @property
    def title(self) -> str:
        return "Buffer"

    @classmethod
    def from_dict(cls, d: dict) -> "Buffer":
        duration = _parse_duration(d.get("duration"))
        if duration is None:
            raise ItineraryError("A 'buffer' needs a 'duration'")
        return cls(duration_min=duration, auto=False)


@dataclass
class Waypoint:
    """An intermediate stop a drive's route passes through. Carries a required
    ``coordinate`` (the point plotted on the route) plus an optional location
    name and the leg's ``duration``/``distance_km``/``off_road``. When a road has
    waypoints the route runs start → waypoint 1 → … → last waypoint, and the last
    one is the effective destination (the road's ``end_coordinate`` is not
    plotted).

    ``off_road`` describes the **leg reaching this waypoint**, exactly like
    ``duration`` and ``distance_km`` — so a drive can be rough on one stretch
    without the whole road being flagged (``Road.off_road``)."""

    coordinate: Coordinate
    location: str = ""
    duration_min: int | None = None
    distance_km: float | None = None
    off_road: bool = False

    @property
    def duration_display(self) -> str:
        return _format_duration(self.duration_min)

    @classmethod
    def from_dict(cls, d: dict) -> "Waypoint":
        if not isinstance(d, dict):
            raise ItineraryError(
                "a road 'waypoint' must be an object with a 'coordinate'"
            )
        coord = _parse_coordinate(d.get("coordinate"))
        if coord is None:
            raise ItineraryError("a road 'waypoint' needs a 'coordinate'")
        return cls(
            coordinate=coord,
            location=str(d.get("location", "")),
            duration_min=_parse_duration(d.get("duration")),
            distance_km=_parse_float(d.get("distance_km"), "waypoint distance_km"),
            off_road=_parse_bool(d.get("off_road", False)),
        )


@dataclass
class Road(Activity):
    """A drive/transfer. Departs from ``start`` (its optional ``coordinate`` is
    the departure point) and runs through ``waypoints`` — an ordered list whose
    last entry is the arrival. There is no separate ``end``: the destination is
    the final waypoint."""

    kind = "road"
    start: str = ""
    description: str = ""
    guidebook_pages: str = ""
    distance_km: float | None = None
    off_road: bool = False
    waypoints: list[Waypoint] = field(default_factory=list)  # ordered stops; last = arrival
    activities: list[Activity] = field(default_factory=list)

    @property
    def destination(self) -> str:
        """The arrival's name — the last named waypoint (usually the final one)."""
        for wp in reversed(self.waypoints):
            if wp.location:
                return wp.location
        return ""

    @property
    def title(self) -> str:
        if self.start and self.destination:
            return f"{self.start} → {self.destination}"
        return self.start or self.destination or "Road"

    @classmethod
    def from_dict(cls, d: dict) -> "Road":
        if "start" not in d:
            raise ItineraryError("A 'road' activity needs a 'start' address")
        waypoints = [Waypoint.from_dict(w) for w in d.get("waypoints", [])]
        if not waypoints:
            raise ItineraryError(
                "A 'road' activity needs at least one 'waypoint' (the arrival)"
            )
        return cls(
            **_sched(d),  # 'coordinate' here is the departure point
            start=str(d["start"]),
            description=str(d.get("description", "")),
            guidebook_pages=_pages(d),
            distance_km=_parse_float(d.get("distance_km"), "road distance_km"),
            off_road=_parse_bool(d.get("off_road", False)),
            waypoints=waypoints,
            activities=_nested(d, "road"),
        )


POI_CATEGORIES = (
    "museum", "church", "building", "viewpoint", "ruins", "castle", "temple",
    "street", "natural park", "mountain", "lake", "beach", "waterfall", "other",
)


@dataclass
class PointOfInterest(Activity):
    """A visit to a specific point of interest."""

    kind = "point_of_interest"
    name: str = ""
    address: str = ""
    description: str = ""
    guidebook_pages: str = ""
    category: str = "other"
    website: str = ""  # the venue's website
    activities: list[Activity] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.name or "Point of interest"

    @classmethod
    def from_dict(cls, d: dict) -> "PointOfInterest":
        if "name" not in d:
            raise ItineraryError("A 'point_of_interest' activity needs a 'name'")
        category = str(d.get("category", "other")).strip().lower()
        if category not in POI_CATEGORIES:
            raise ItineraryError(
                "point_of_interest category must be one of: "
                f"{', '.join(POI_CATEGORIES)} (got {d.get('category')!r})"
            )
        return cls(
            **_sched(d),
            name=str(d["name"]),
            address=str(d.get("address", "")),
            description=str(d.get("description", "")),
            guidebook_pages=_pages(d),
            category=category,
            website=str(d.get("website", "")),
            activities=_nested(d, "point_of_interest"),
        )


@dataclass
class Place(Activity):
    """A place (a town for instance) grouping several nested activities.

    Unlike the other containers a place has no length of its own — it *is* what
    you do there — so when it gives neither a ``duration`` nor an ``end_time``,
    :meth:`Itinerary.from_dict` fills its duration with its nested activities'
    total (see :func:`nested_duration_total`).
    """

    kind = "place"
    name: str = ""
    description: str = ""
    guidebook_pages: str = ""
    activities: list[Activity] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.name or "Place"

    @classmethod
    def from_dict(cls, d: dict) -> "Place":
        if "name" not in d:
            raise ItineraryError("A 'place' activity needs a 'name'")
        return cls(
            **_sched(d),
            name=str(d["name"]),
            description=str(d.get("description", "")),
            guidebook_pages=_pages(d),
            activities=_nested(d, "place"),
        )


# Which activity types each container kind may nest under its ``activities``.
# Nesting is only one level deep (enforced by the validator).
NESTED_ACTIVITY_TYPES = {
    "road": ("meal",),
    "hike": ("meal",),
    "place": ("point_of_interest", "hike", "meal"),
    "point_of_interest": ("point_of_interest", "hike", "meal"),
}


def _or_list(values) -> str:
    """'a', 'b', 'c' → \"'a', 'b' or 'c'\" (for a human-readable type list)."""
    quoted = [f"'{v}'" for v in values]
    if len(quoted) == 1:
        return quoted[0]
    return ", ".join(quoted[:-1]) + " or " + quoted[-1]


def _nested(d: dict, container_kind: str) -> list[Activity]:
    """Build the ``activities`` nested under a container from its dict."""
    return [_nested_activity(m, container_kind) for m in d.get("activities", [])]


def _nested_activity(entry, container_kind: str) -> Activity:
    """A nested item inside a container (``road`` / ``hike`` / ``place`` /
    ``point_of_interest``): an object whose ``type`` is one of the container's
    allowed nested types."""
    allowed = NESTED_ACTIVITY_TYPES[container_kind]
    if not isinstance(entry, dict):
        raise ItineraryError(
            f"A nested activity must be an object with a 'type' of {_or_list(allowed)}"
        )
    kind = entry.get("type")
    if kind not in allowed:
        raise ItineraryError(
            f"A nested activity 'type' must be {_or_list(allowed)} (got {kind!r})"
        )
    return _ACTIVITY_TYPES[kind].from_dict(entry)


@dataclass
class Hike(Activity):
    """A hike between two points (or a loop).

    An optional ``gpx`` — a base64-encoded GPX file, carried inside the JSON —
    is parsed into ``track``, which is what the renderers draw the trail map and
    the elevation profile from (see :mod:`.gpx`). The track also *fills in* a
    missing ``distance_km`` / ``elevation_m``: it measured them, so making you
    retype them would only be a chance to disagree with it.
    """

    kind = "hike"
    name: str = ""
    description: str = ""
    guidebook_pages: str = ""
    distance_km: float | None = None
    elevation_m: float | None = None
    start: str = ""
    end: str = ""
    route: str = "back_and_forth"  # "loop" or "back_and_forth"
    gpx: str = ""                       # base64 GPX file, as given
    track: GpxTrack | None = None       # parsed from `gpx`
    activities: list[Activity] = field(default_factory=list)

    @property
    def title(self) -> str:
        if self.name:
            return self.name
        if self.start and self.end:
            return f"{self.start} → {self.end}"
        return self.start or "Hike"

    @property
    def route_label(self) -> str:
        return {
            "loop": "Loop",
            "back_and_forth": "Back and forth",
            "one_way": "One way",
        }.get(self.route, self.route)

    @classmethod
    def from_dict(cls, d: dict) -> "Hike":
        if "name" not in d:
            raise ItineraryError("A 'hike' activity needs a 'name'")
        raw_gpx = d.get("gpx")
        track = gpx_track(raw_gpx) if raw_gpx not in (None, "") else None
        hike = cls(
            **_sched(d),
            name=str(d["name"]),
            description=str(d.get("description", "")),
            guidebook_pages=_pages(d),
            distance_km=_parse_float(d.get("distance_km"), "hike distance_km"),
            elevation_m=_parse_float(d.get("elevation_m"), "hike elevation_m"),
            start=str(d.get("start", "")),
            end=str(d.get("end", "")),
            route=_parse_route(d.get("route"), default="back_and_forth"),
            gpx=str(raw_gpx) if raw_gpx else "",
            track=track,
            activities=_nested(d, "hike"),
        )
        if track is not None:
            # The recording measured the walk; an explicit figure still wins, so
            # you can quote the guidebook's round numbers over the GPS's.
            if hike.distance_km is None:
                hike.distance_km = round(track.distance_km, 1)
            if hike.elevation_m is None and track.ascent_m is not None:
                hike.elevation_m = float(round(track.ascent_m))
        return hike


# Valid ``meal_type`` values. Only the first three are ever inferred from the
# start time; the rest (brunch/snack/picnic/meal) must be set explicitly.
MEAL_TYPES = ("breakfast", "lunch", "dinner", "brunch", "snack", "picnic", "meal")

# Default thresholds for inferring a meal's type from its start time: a meal
# starting before ``BREAKFAST_UNTIL`` is breakfast, up to and including
# ``LUNCH_UNTIL`` is lunch, and after that dinner. Overridable per trip via
# ``default.breakfast_until`` / ``default.lunch_until``.
DEFAULT_BREAKFAST_UNTIL = time(10, 0)
DEFAULT_LUNCH_UNTIL = time(16, 0)


def infer_meal_category(
    meal_type: str,
    start_time: time | None,
    breakfast_until: time = DEFAULT_BREAKFAST_UNTIL,
    lunch_until: time = DEFAULT_LUNCH_UNTIL,
) -> str:
    """The resolved meal category: the explicit ``meal_type`` if given, else
    inferred from the start time using the ``breakfast_until`` / ``lunch_until``
    thresholds (falling back to lunch when there is no time)."""
    if meal_type:
        return meal_type
    if start_time is None:
        return "lunch"
    if start_time < breakfast_until:
        return "breakfast"
    if start_time <= lunch_until:
        return "lunch"
    return "dinner"


@dataclass
class Meal(Activity):
    """A meal — breakfast, lunch or dinner — optionally at a named restaurant.

    Scheduled like any other activity (give any two of start_time / end_time /
    duration); the restaurant name and address are both optional. ``meal_type``
    may be given explicitly; otherwise the ``category`` is inferred from the
    start time and the trip's ``breakfast_until`` / ``lunch_until`` thresholds,
    resolved once the timeline is laid out (see ``Itinerary.from_dict``).
    """

    kind = "meal"
    restaurant: str = ""
    address: str = ""
    area: str = ""  # town/region to eat in; used when no restaurant is named
    meal_type: str = ""  # explicit override; "" → infer from the start time
    category: str = ""  # resolved meal category (breakfast/lunch/dinner/…)

    @property
    def title(self) -> str:
        label = (self.category or "meal").capitalize()
        if self.restaurant:
            return f"{label} at {self.restaurant}"
        if self.area:
            return f"{label} near {self.area}"
        return label

    @classmethod
    def from_dict(cls, d: dict) -> "Meal":
        meal_type = str(d.get("meal_type", "")).strip().lower()
        if meal_type and meal_type not in MEAL_TYPES:
            raise ItineraryError(
                "meal meal_type must be one of: "
                f"{', '.join(MEAL_TYPES)} (got {d.get('meal_type')!r})"
            )
        return cls(
            **_sched(d),
            restaurant=str(d.get("restaurant", "")),
            address=str(d.get("address", "")),
            area=str(d.get("area", "")),
            meal_type=meal_type,
            # an explicit type resolves immediately; an inferred one is filled
            # in after scheduling (once the start time is known).
            category=meal_type,
        )


_ACTIVITY_TYPES = {
    c.kind: c for c in (Road, PointOfInterest, Place, Hike, Meal, Buffer)
}


def activity_from_dict(data: dict) -> Activity:
    if not isinstance(data, dict):
        raise ItineraryError("Each activity must be an object with a 'type'")
    kind = data.get("type")
    if kind not in _ACTIVITY_TYPES:
        valid = ", ".join(sorted(_ACTIVITY_TYPES))
        raise ItineraryError(
            f"Activity 'type' must be one of: {valid} (got {kind!r})"
        )
    return _ACTIVITY_TYPES[kind].from_dict(data)


# An auto-sized buffer is rounded down to a whole multiple of this many minutes.
# A printed schedule is a plan you read off a page, so "1h05" is a break and
# "1h04" is a division result; whatever is left over (under five minutes) simply
# isn't spent.
AUTO_BUFFER_STEP = 5


def schedule_activities(
    activities: list[Activity],
    day_start: time,
    default_buffer_min: int = 0,
    day_end: time | None = None,
    auto_sized_buffer: bool = False,
) -> list[Activity]:
    """Lay activities out on a timeline, inserting buffers, and return the
    resulting ordered list (activities plus any :class:`Buffer` items).

    * ``start_time`` — the first activity defaults to ``day_start``; each later
      activity defaults to the previous item's end time.
    * one of ``duration`` / ``end_time`` is inferred from the other.
    * a default buffer (``default_buffer_min``) is inserted between every two
      consecutive activities that don't already have a manual buffer between
      them; a gap left by an explicit ``start_time`` becomes an inferred buffer.
    * ``auto_sized_buffer`` (with a ``day_end``) instead *sizes* those buffers so
      the day spreads out and its last activity lands on ``day_end``, per
      :func:`_auto_buffer_plan`. ``default_buffer_min`` is then ignored — the two
      are alternatives, not layers: a fixed 15 min between every stop and "fill
      the day" are two answers to the same question.
    """
    if not auto_sized_buffer or day_end is None:
        return _lay_out(activities, day_start, default_buffer_min)

    # Packing the day tight is what reveals how much slack there is, so lay it
    # out once for measurement. That mutates the activities, so snapshot the
    # fields the walk fills in and restore them before the real pass — otherwise
    # it would read the first pass's assigned start times as explicit ones and
    # treat every activity as pinned.
    snapshot = [(a.start_time, a.end_time, a.duration_min) for a in activities]
    _lay_out(activities, day_start, 0)
    plan = _auto_buffer_plan(activities, snapshot, day_end)
    for act, (start, end, duration) in zip(activities, snapshot):
        act.start_time, act.end_time, act.duration_min = start, end, duration
    padded: list[Activity] = []
    for i, act in enumerate(activities):
        padded.append(act)
        if plan.get(i):
            padded.append(Buffer(duration_min=plan[i], auto=True))
    return _lay_out(padded, day_start, 0)


def _minute(t: time) -> int:
    """A clock time as minutes since midnight."""
    return t.hour * 60 + t.minute


def _auto_buffer_plan(
    activities: list[Activity], snapshot: list[tuple], day_end: time
) -> dict[int, int]:
    """How long a buffer to insert *after* each activity index so that every
    stretch of the day the timeline is free to move fills the room it has.

    Read from ``activities`` — already laid out tight, so each one's ``end_time``
    is the earliest it can happen — and from ``snapshot``, the ``(start_time,
    end_time, duration)`` they were *given*, which is what pins them.

    The day is cut into stretches at every time the JSON states, because a stated
    time is a promise the spacing may not break: a given ``start_time`` fixes
    where its activity begins, so the stretch before it has to end there, and a
    given ``end_time`` fixes where its activity finishes, so the stretch ends
    with that activity (padding ahead of it would only shorten it). The stretch
    left over is the one running to ``day_end`` — the point of the whole option.

    Each stretch's slack is then shared out evenly over the gaps between its
    consecutive activities, skipping any gap a manual buffer already fills (it
    said how long that pause is) and rounding down to ``AUTO_BUFFER_STEP``.
    """
    n = len(activities)
    plan: dict[int, int] = {}

    # cut after any activity whose end is stated, and before any whose start is
    stretches: list[tuple[int, int]] = []
    first = 0
    for i in range(n):
        closes = snapshot[i][1] is not None
        next_pinned = i + 1 < n and snapshot[i + 1][0] is not None
        if closes or next_pinned or i == n - 1:
            stretches.append((first, i))
            first = i + 1

    for lo, hi in stretches:
        if snapshot[hi][1] is not None:
            continue  # this stretch ends on a stated end_time: nothing may move
        limit = _minute(day_end) if hi == n - 1 else _minute(snapshot[hi + 1][0])
        opens, closes_at = activities[lo].start_time, activities[hi].end_time
        if opens is None or closes_at is None:
            continue
        if _minute(closes_at) < _minute(opens):
            continue  # already spilling past midnight — no room to add any
        slack = limit - _minute(closes_at)
        if slack < AUTO_BUFFER_STEP:
            continue
        if not any(act.duration_min for act in activities[lo:hi + 1]
                   if act.kind != "buffer"):
            # Nothing here says how long it takes, so there is no schedule to
            # space out — spreading would only invent one ("be at the square at
            # 18:00") out of a day the validator is already asking you to time.
            continue
        gaps = [
            i for i in range(lo, hi)
            if activities[i].kind != "buffer" and activities[i + 1].kind != "buffer"
        ]
        if not gaps:
            continue  # nothing between: a lone activity can't be spread out
        base, extra = divmod(slack // AUTO_BUFFER_STEP, len(gaps))
        for j, i in enumerate(gaps):
            size = (base + (1 if j < extra else 0)) * AUTO_BUFFER_STEP
            if size:
                plan[i] = size
    return plan


def _lay_out(
    activities: list[Activity], day_start: time, default_buffer_min: int = 0
) -> list[Activity]:
    """The timeline walk itself — see :func:`schedule_activities`."""
    # 1. Insert the trip's default buffer between adjacent real activities.
    expanded: list[Activity] = []
    for item in activities:
        if (
            default_buffer_min
            and expanded
            and item.kind != "buffer"
            and expanded[-1].kind != "buffer"
        ):
            expanded.append(Buffer(duration_min=default_buffer_min, auto=True))
        expanded.append(item)

    # 2. Walk the timeline assigning times, inferring gap buffers.
    result: list[Activity] = []
    current = day_start
    seen_activity = False
    for item in expanded:
        if item.kind == "buffer":
            item.start_time = current
            item.end_time = _add_minutes(current, item.duration_min or 0)
            current = item.end_time
            result.append(item)
            continue

        if not seen_activity:
            if item.start_time is None:
                item.start_time = current
            current = item.start_time
            seen_activity = True
        elif item.start_time is not None and item.start_time > current:
            gap = _diff_minutes(current, item.start_time)
            result.append(
                Buffer(
                    duration_min=gap,
                    auto=True,
                    start_time=current,
                    end_time=item.start_time,
                )
            )
            current = item.start_time
        elif item.start_time is None:
            item.start_time = current
        else:  # explicit start at or before the running time — honor it
            current = item.start_time

        if item.duration_min is not None and item.end_time is None:
            item.end_time = _add_minutes(item.start_time, item.duration_min)
        elif item.end_time is not None and item.duration_min is None:
            item.duration_min = _diff_minutes(item.start_time, item.end_time)
        elif item.end_time is None and item.duration_min is None:
            item.end_time = item.start_time
            item.duration_min = 0
        current = item.end_time
        result.append(item)

    # 3. Drop empty buffers (e.g. a 0-min manual buffer, whose only job was to
    #    suppress the default), then merge runs of automatic buffers.
    merged: list[Activity] = []
    for item in result:
        if item.kind == "buffer" and not item.duration_min:
            continue
        if (
            item.kind == "buffer"
            and item.auto
            and merged
            and merged[-1].kind == "buffer"
            and merged[-1].auto
        ):
            prev = merged[-1]
            prev.duration_min = (prev.duration_min or 0) + (item.duration_min or 0)
            prev.end_time = item.end_time
            continue
        merged.append(item)
    return merged


def _item_minutes(act: Activity) -> int | None:
    """One activity's length from what it was given: its ``duration``, else the
    span between an explicit ``start_time`` and ``end_time``. ``None`` when
    neither settles it. Mirrors the validator's ``_obj_minutes``, on the model
    side — a *nested* activity is never put on the timeline, so its times are
    whatever the JSON said and nothing more."""
    if act.duration_min is not None:
        return act.duration_min
    if act.start_time is not None and act.end_time is not None:
        return _diff_minutes(act.start_time, act.end_time)
    return None


def nested_duration_total(activities: list[Activity]) -> int | None:
    """The nested activities' lengths added up, or ``None`` when not one of them
    says how long it lasts (so there is nothing to conclude). Items that don't
    say simply contribute nothing — this is a floor for the container, not a
    measurement of it."""
    known = [m for m in (_item_minutes(a) for a in activities) if m is not None]
    return sum(known) if known else None


def resolve_meal_categories(
    activities: list[Activity], breakfast_until: time, lunch_until: time
) -> None:
    """Fill each meal's ``category`` in place (recursing into nested activities),
    from the trip thresholds and the now-scheduled start time. Meals given an
    explicit ``meal_type`` already have a category and are left untouched."""
    for act in activities:
        if act.kind == "meal" and not act.category:
            act.category = infer_meal_category(
                act.meal_type, act.start_time, breakfast_until, lunch_until
            )
        resolve_meal_categories(
            getattr(act, "activities", []) or [], breakfast_until, lunch_until
        )
