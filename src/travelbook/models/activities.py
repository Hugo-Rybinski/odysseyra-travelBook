"""Activity types (road / point_of_interest / place / hike / meal / buffer) and
the day-scheduling pass."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time

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


@dataclass
class Activity:
    """Common scheduling fields shared by every activity type."""

    start_time: time | None = None
    end_time: time | None = None
    duration_min: int | None = None
    start_tz: int | None = None  # UTC offset; None means "use the trip default"
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


def _sched(d: dict) -> dict:
    """Extract the raw (pre-inference) scheduling fields from an activity dict."""
    return {
        "start_time": _parse_time(d.get("start_time")),
        "end_time": _parse_time(d.get("end_time")),
        "duration_min": _parse_duration(d.get("duration")),
        "start_tz": _parse_tz(d.get("start_tz", d.get("start_timezone"))),
        "end_tz": _parse_tz(d.get("end_tz", d.get("end_timezone"))),
    }


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
class Road(Activity):
    """A drive/transfer between two places."""

    kind = "road"
    start: str = ""
    end: str = ""
    distance_km: float | None = None
    off_road: bool = False
    activities: list[Activity] = field(default_factory=list)

    @property
    def title(self) -> str:
        if self.start and self.end:
            return f"{self.start} → {self.end}"
        return self.start or self.end or "Road"

    @classmethod
    def from_dict(cls, d: dict) -> "Road":
        if "start" not in d or "end" not in d:
            raise ItineraryError(
                "A 'road' activity needs a 'start' and an 'end' address"
            )
        return cls(
            **_sched(d),
            start=str(d["start"]),
            end=str(d["end"]),
            distance_km=_parse_float(d.get("distance_km"), "road distance_km"),
            off_road=_parse_bool(d.get("off_road", False)),
            activities=[_nested_activity(m, "road") for m in d.get("activities", [])],
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
    category: str = "other"
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
            category=category,
            activities=[_nested_activity(m, "point_of_interest")
                        for m in d.get("activities", [])],
        )


@dataclass
class Place(Activity):
    """A place (a town for instance) grouping several nested activities."""

    kind = "place"
    name: str = ""
    description: str = ""
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
            activities=[_nested_activity(m, "place") for m in d.get("activities", [])],
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
    """A hike between two points (or a loop)."""

    kind = "hike"
    name: str = ""
    description: str = ""
    distance_km: float | None = None
    elevation_m: float | None = None
    start: str = ""
    end: str = ""
    route: str = "back_and_forth"  # "loop" or "back_and_forth"
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
        return cls(
            **_sched(d),
            name=str(d["name"]),
            description=str(d.get("description", "")),
            distance_km=_parse_float(d.get("distance_km"), "hike distance_km"),
            elevation_m=_parse_float(d.get("elevation_m"), "hike elevation_m"),
            start=str(d.get("start", "")),
            end=str(d.get("end", "")),
            route=_parse_route(d.get("route"), default="back_and_forth"),
            activities=[_nested_activity(m, "hike") for m in d.get("activities", [])],
        )


# Valid ``meal_type`` values. Only the first three are ever inferred from the
# start time; the rest (brunch/snack/picnic/meal) must be set explicitly.
MEAL_TYPES = ("breakfast", "lunch", "dinner", "brunch", "snack", "picnic", "meal")

# Default thresholds for inferring a meal's type from its start time: a meal
# starting before ``BREAKFAST_UNTIL`` is breakfast, up to and including
# ``LUNCH_UNTIL`` is lunch, and after that dinner. Overridable per trip via
# ``default.breakfast_until`` / ``default.lunch_until``.
DEFAULT_BREAKFAST_UNTIL = time(10, 0)
DEFAULT_LUNCH_UNTIL = time(16, 0)


@dataclass
class Meal(Activity):
    """A meal — breakfast, lunch or dinner — optionally at a named restaurant.

    Scheduled like any other activity (give any two of start_time / end_time /
    duration); the restaurant name and address are both optional. ``meal_type``
    may be given explicitly, otherwise it is inferred from the start time using
    the ``breakfast_until`` / ``lunch_until`` thresholds (defaulting to 10:00
    and 16:00, but set per trip from the ``default`` object).
    """

    kind = "meal"
    restaurant: str = ""
    address: str = ""
    area: str = ""  # town/region to eat in; used when no restaurant is named
    meal_type: str = ""  # explicit override; "" → infer from the start time
    breakfast_until: time = DEFAULT_BREAKFAST_UNTIL
    lunch_until: time = DEFAULT_LUNCH_UNTIL

    @property
    def type(self) -> str:
        """The meal type — the explicit ``meal_type`` if set, else inferred from
        the (possibly inferred) start time; falls back to lunch with no time."""
        if self.meal_type:
            return self.meal_type
        t = self.start_time
        if t is None:
            return "lunch"
        if t < self.breakfast_until:
            return "breakfast"
        if t <= self.lunch_until:
            return "lunch"
        return "dinner"

    @property
    def title(self) -> str:
        label = self.type.capitalize()
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


def schedule_activities(
    activities: list[Activity], day_start: time, default_buffer_min: int = 0
) -> list[Activity]:
    """Lay activities out on a timeline, inserting buffers, and return the
    resulting ordered list (activities plus any :class:`Buffer` items).

    * ``start_time`` — the first activity defaults to ``day_start``; each later
      activity defaults to the previous item's end time.
    * one of ``duration`` / ``end_time`` is inferred from the other.
    * a default buffer (``default_buffer_min``) is inserted between every two
      consecutive activities that don't already have a manual buffer between
      them; a gap left by an explicit ``start_time`` becomes an inferred buffer.
    """
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
