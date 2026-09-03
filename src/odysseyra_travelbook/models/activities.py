"""Activity types (road / point_of_interest / place / hike / meal / buffer) and
the day-scheduling pass."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import time

from .geo import Coordinate, _parse_coordinate
from .gpx import GpxTrack, gpx_track
from .opening import Opening, parse_opening
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
    optional map location.

    ``detour`` marks a stop you probably *won't* make but want the book to carry
    anyway, in case the day goes differently — so it is kept beside the day
    rather than on it: it takes no time in the schedule, gets no buffer before
    it, and shows its ``duration`` (how long it *would* take) without any clock
    time, since it has none to have. See :func:`schedule_activities`.
    """

    coordinate: Coordinate | None = None  # optional map location
    detour: bool = False  # kept for reference; not placed on the timeline


def _sched(d: dict) -> dict:
    """Extract the raw (pre-inference) scheduling fields from an activity dict."""
    return {
        "start_time": _parse_time(d.get("start_time")),
        "end_time": _parse_time(d.get("end_time")),
        "duration_min": _parse_duration(d.get("duration")),
        "start_tz": _parse_tz(d.get("start_tz")),
        "end_tz": _parse_tz(d.get("end_tz")),
        "coordinate": _parse_coordinate(d.get("coordinate")),
        # Every activity but a `buffer` can be a detour — a buffer *is* time, and
        # a detour is the absence of any (`Buffer.from_dict` doesn't come here).
        "detour": _parse_bool(d.get("detour", False)),
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
    """One point of a drive's route, as the model carries it: a required
    ``coordinate`` (plotted on the route) plus an optional location name and the
    figures of the leg *reaching* it (``duration`` / ``distance_km`` /
    ``off_road``). The route runs start → waypoint 1 → … → last waypoint, and the
    last named one is the destination.

    This is the **lowered** form of the input's ``legs`` (see
    :func:`_road_chain`), not something written by hand: a leg contributes its
    route-shaping points as unnamed waypoints and then its arrival as a named one
    carrying that leg's figures. Everything downstream — the PDF, the resolved
    document the viewer renders, the maps, the ``.ics`` — reads this chain, which
    is why moving the input onto legs changed no renderer.

    ``off_road`` describes the **leg reaching this waypoint**, exactly like
    ``duration`` and ``distance_km`` — so a drive can be rough on one stretch
    without the whole road being flagged (``Road.off_road``).

    So does ``gpx``/``track``: the recording of the drive *up to* this point.
    Unlike a hike's it is never drawn as a figure of its own — no trail map, no
    elevation profile — it **is** the leg's line on the day map, replacing the
    routed guess (see ``maps/build.py``).

    ``coordinate`` is typed optional for one transient state only: a road with
    ``same_end_as_next_activity`` may leave its arrival unlocated in the JSON, and
    the point is then filled in from the next activity by
    :func:`resolve_shared_road_endpoints` before the day is observable. Anything
    downstream may treat it as set."""

    coordinate: Coordinate | None
    location: str = ""
    duration_min: int | None = None
    distance_km: float | None = None
    off_road: bool = False
    gpx: str = ""                       # base64 GPX of the leg reaching here
    track: GpxTrack | None = None       # parsed from `gpx`

    @property
    def duration_display(self) -> str:
        return _format_duration(self.duration_min)


def _leg_text(leg: dict | None, key: str) -> str:
    return str(leg.get(key) or "").strip() if leg else ""


def _leg_off_road(leg: dict) -> bool:
    return _parse_bool(leg.get("off_road", False))


def _road_chain(
    legs: list[dict], *, borrow_start: bool = False, borrow_end: bool = False,
) -> tuple[str, Coordinate | None, list[Waypoint], bool]:
    """Lower a road's input ``legs`` onto the chain :class:`Road` carries: the
    departure (name + optional coordinate), the ordered :class:`Waypoint` list,
    and whether the whole drive is off-road.

    Each leg contributes its route-shaping ``waypoints`` — bare coordinates that
    bend the drawn route and get no row of their own — followed by its arrival,
    a named waypoint carrying that leg's ``duration`` / ``distance_km`` /
    ``off_road``.

    A leg may leave out the endpoint its neighbour already states:
    ``start_location`` / ``start_coordinate`` fall back to the previous leg's
    ``end_*``, and ``end_location`` / ``end_coordinate`` to the next leg's
    ``start_*``, so a junction between two legs is written once. The first leg
    must name its own departure and the last its own arrival; a junction neither
    side names can't be deduced and raises. Where both sides state it, the
    earlier leg's ``end_*`` wins (the validator warns when the two disagree).

    The departure *coordinate* stays optional, as the road's own ``coordinate``
    always was: with maps on it is geocoded from ``start_location`` when absent.
    Every other point of the route is plotted from its coordinate, so those are
    required — exactly what a hand-written waypoint always demanded.

    ``borrow_start`` / ``borrow_end`` are the road's ``same_start_as_previous_``
    ``activity`` / ``same_end_as_next_activity``: the one endpoint that has no
    neighbouring *leg* to inherit from then has a neighbouring *activity*
    instead, so it is left blank here and filled in by
    :func:`resolve_shared_road_endpoints` once the day's other activities exist.
    That is the only reason this function ever returns a nameless ``start`` or an
    unlocated final waypoint."""
    start = _leg_text(legs[0], "start_location")
    if not start and not borrow_start:
        raise ItineraryError(
            "the first road 'leg' needs a 'start_location' — there is no "
            "previous leg to take its departure from (set "
            "'same_start_as_previous_activity' to take it from the previous "
            "activity instead)"
        )
    waypoints: list[Waypoint] = []
    for i, leg in enumerate(legs):
        nxt = legs[i + 1] if i + 1 < len(legs) else None
        last = nxt is None
        end = _leg_text(leg, "end_location") or _leg_text(nxt, "start_location")
        if not end and not (last and borrow_end):
            raise ItineraryError(
                f"road leg {i + 1} needs an 'end_location' — neither it nor the "
                "next leg's 'start_location' names where it arrives"
                if nxt else
                "the last road 'leg' needs an 'end_location' — there is no next "
                "leg to take its arrival from (set 'same_end_as_next_activity' "
                "to take it from the next activity instead)"
            )
        coord = _parse_coordinate(leg.get("end_coordinate"))
        if coord is None and nxt is not None:
            coord = _parse_coordinate(nxt.get("start_coordinate"))
        if coord is None and not (last and borrow_end):
            raise ItineraryError(
                f"road leg {i + 1} needs an 'end_coordinate' — {end} is a point "
                "on the route, so it has to be located"
            )
        shaping = leg.get("waypoints") or []
        if not isinstance(shaping, list):
            raise ItineraryError(
                "a road leg's 'waypoints' must be a list of coordinates"
            )
        for raw in shaping:
            point = _parse_coordinate(raw)
            if point is None:
                raise ItineraryError(
                    "each of a road leg's 'waypoints' must be a coordinate with "
                    "a 'lat' and a 'long'"
                )
            waypoints.append(Waypoint(coordinate=point))
        raw_gpx = leg.get("gpx")
        waypoints.append(Waypoint(
            coordinate=coord,
            location=end,
            duration_min=_parse_duration(leg.get("duration")),
            distance_km=_parse_float(leg.get("distance_km"), "road leg distance_km"),
            off_road=_leg_off_road(leg),
            gpx=str(raw_gpx) if raw_gpx else "",
            track=gpx_track(raw_gpx) if raw_gpx not in (None, "") else None,
        ))
    # The drive as a whole is off-road only when every one of its legs is; a
    # single rough stretch stays that leg's own flag.
    return (start, _parse_coordinate(legs[0].get("start_coordinate")), waypoints,
            all(_leg_off_road(leg) for leg in legs))


@dataclass
class Road(Activity):
    """A drive/transfer, written as an ordered chain of ``legs`` — one per hop,
    each with its endpoints, its driving time and distance, whether it runs
    off-road, and the intermediate points its route bends through.

    The legs are lowered on load (:func:`_road_chain`) onto the fields carried
    here: ``start`` (with the inherited ``coordinate``) is the departure and
    ``waypoints`` the ordered points through to the arrival, each leg's arrival
    carrying that leg's figures. There is no separate ``end``: the destination is
    the last named waypoint.

    The three ``display_*_on_maps`` switches say which of the drive's own points
    earn a **numbered pin** on the day map — the very first departure, the very
    last arrival, and every junction in between. A drive is drawn as a route
    either way; these only add pins, and with all three on every named point of
    the road is pinned (see :func:`.maps.build.resolve_day`).

    ``display_intermediate_point_on_maps`` is **on**, the two ends **off**. A
    junction is the one point of a drive that has nothing else to identify it:
    splitting the drive there is what says it matters, and the reader has no way
    to find it on the map otherwise. The two ends are usually the activity before
    and after (the drive leaves the château and arrives at the hotel), so pinning
    them by default would number the same place twice — which is what
    ``same_start_as_previous_activity`` / ``same_end_as_next_activity`` are for.

    ``same_start_as_previous_activity`` / ``same_end_as_next_activity`` say that
    an end of the drive **is** the neighbouring activity's place rather than a
    place of its own — you drive away from the museum you just visited, and on to
    the hotel listed next. Two consequences, and they are independent:

    * the leg endpoint there may be left blank and is filled in from that
      activity (:func:`resolve_shared_road_endpoints`);
    * that end never earns a pin of its own, whatever the ``display_*`` switch
      says — it *shares* the neighbour's, so one place keeps one number.

    ``start_shared_with`` / ``end_shared_with`` hold the neighbour a flag
    resolved to, which is what the maps read to alias the pin. They are filled in
    by the day, never by the JSON."""

    kind = "road"
    start: str = ""
    description: str = ""
    guidebook_pages: str = ""
    distance_km: float | None = None
    off_road: bool = False
    display_start_on_maps: bool = False
    display_end_on_maps: bool = False
    display_intermediate_point_on_maps: bool = True  # opt-out, unlike the two ends
    same_start_as_previous_activity: bool = False
    same_end_as_next_activity: bool = False
    start_shared_with: Activity | None = None  # resolved by the day, not the JSON
    end_shared_with: Activity | None = None
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
    def named_waypoints(self) -> list[Waypoint]:
        """The waypoints that end a leg — the ones with a name, i.e. everything
        but the route-shaping points."""
        return [wp for wp in self.waypoints if wp.location]

    def pinned_waypoints(self) -> list[Waypoint]:
        """The named waypoints that earn a numbered pin: the last one under
        ``display_end_on_maps`` (off by default), the earlier ones under
        ``display_intermediate_point_on_maps`` (**on**), so a multi-leg drive
        pins its junctions unless told not to. A point whose coordinate is
        ``show_on_map: false`` is never pinned — that flag hides a pin wherever
        it appears."""
        named = self.named_waypoints
        out = []
        for i, wp in enumerate(named):
            last = i == len(named) - 1
            if last and self.end_shared_with is not None:
                # The arrival is the next activity's place: it wears that
                # activity's pin (see `maps.build.pin_aliases`), so pinning it
                # again here would put two numbers on one point.
                continue
            shown = (self.display_end_on_maps if last
                     else self.display_intermediate_point_on_maps)
            if shown and wp.coordinate is not None and wp.coordinate.show_on_map:
                out.append(wp)
        return out

    @property
    def title(self) -> str:
        if self.start and self.destination:
            return f"{self.start} → {self.destination}"
        return self.start or self.destination or "Road"

    @classmethod
    def from_dict(cls, d: dict) -> "Road":
        raw = d.get("legs")
        if not isinstance(raw, list) or not raw:
            raise ItineraryError(
                "A 'road' activity needs a non-empty 'legs' array — one entry "
                "per hop of the drive (a plain A → B drive has one)"
            )
        for leg in raw:
            if not isinstance(leg, dict):
                raise ItineraryError(
                    "each road 'leg' must be an object with a 'start_location' "
                    "and an 'end_location'"
                )
        borrow_start = _parse_bool(d.get("same_start_as_previous_activity", False))
        borrow_end = _parse_bool(d.get("same_end_as_next_activity", False))
        start, coordinate, waypoints, off_road = _road_chain(
            raw, borrow_start=borrow_start, borrow_end=borrow_end)
        sched = _sched(d)
        # A road has no 'coordinate' of its own any more: its departure point is
        # the first leg's 'start_coordinate'.
        sched["coordinate"] = coordinate
        return cls(
            **sched,
            start=start,
            description=str(d.get("description", "")),
            guidebook_pages=_pages(d),
            distance_km=_parse_float(d.get("distance_km"), "road distance_km"),
            off_road=off_road,
            display_start_on_maps=_parse_bool(d.get("display_start_on_maps", False)),
            display_end_on_maps=_parse_bool(d.get("display_end_on_maps", False)),
            display_intermediate_point_on_maps=_parse_bool(
                d.get("display_intermediate_point_on_maps", True)),
            same_start_as_previous_activity=borrow_start,
            same_end_as_next_activity=borrow_end,
            waypoints=waypoints,
            activities=_nested(d, "road"),
        )


POI_CATEGORIES = (
    "museum", "church", "building", "viewpoint", "ruins", "castle", "temple",
    "street", "natural park", "mountain", "lake", "beach", "waterfall", "other",
)


@dataclass
class PointOfInterest(Activity):
    """A visit to a specific point of interest.

    ``opening`` is the optional ``opening_days`` / ``opening_hours`` pair reduced
    to one :class:`.opening.Opening` (``None`` when neither is given): both
    renderers print it under the address, and the validator warns when the visit
    lands on a closed day or outside the hours.
    """

    kind = "point_of_interest"
    name: str = ""
    address: str = ""
    description: str = ""
    guidebook_pages: str = ""
    category: str = "other"
    website: str = ""  # the venue's website
    opening: Opening | None = None
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
            opening=parse_opening(d),
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


def _place_name(act: Activity, side: str) -> str:
    """The name of the *place* ``act`` puts you at — its ``start`` side (where it
    begins) or its ``end`` side (where it leaves you).

    Only a road distinguishes the two: it is the one activity that is two places.
    Everywhere else both sides are the activity's single location, which is its
    place name rather than its :attr:`title` — a meal's title is
    "Lunch at Chez Bruno", and you don't drive to that."""
    if act.kind == "road":
        return act.start if side == "start" else act.destination
    if act.kind == "meal":
        return act.restaurant or act.area
    return getattr(act, "name", "")


def _place_coord(act: Activity, side: str) -> Coordinate | None:
    """The coordinate of the place :func:`_place_name` names, or ``None`` — as a
    **copy**, since ``Coordinate`` is mutable and the two objects are meant to
    agree today, not forever.

    Deliberately only what the JSON states: a ``place`` that is located on the
    map by the centroid of its nested points still lends none here, because that
    centroid is a *drawing* decision made in ``maps/build.py``. Sharing the pin
    covers that case anyway — the drive's end wears the place's number wherever
    the place ended up."""
    if act.kind == "road":
        if side == "start":
            return replace(act.coordinate) if act.coordinate else None
        for wp in reversed(act.waypoints):
            if wp.location:
                return replace(wp.coordinate) if wp.coordinate else None
        return None
    return replace(act.coordinate) if act.coordinate else None


def _neighbour(activities: list[Activity], index: int, step: int) -> Activity | None:
    """The nearest activity before (``step=-1``) or after (``step=+1``) ``index``
    that is somewhere you can be. Buffers are skipped: free time is a length, not
    a location, so ``[museum, 45 min buffer, drive]`` departs from the museum."""
    i = index + step
    while 0 <= i < len(activities):
        if activities[i].kind != "buffer":
            return activities[i]
        i += step
    return None


def resolve_shared_road_endpoints(activities: list[Activity]) -> None:
    """Settle every road's ``same_start_as_previous_activity`` /
    ``same_end_as_next_activity`` against the day's other activities, in place.

    A flag does two things (see :class:`Road`): it lets that leg endpoint be left
    blank, filling it in from the neighbour, and it records the neighbour in
    ``start_shared_with`` / ``end_shared_with`` so the maps can alias the pin. The
    fill is a *fallback* — an endpoint the JSON states wins, and the pin is shared
    either way, which is the point of keeping the two apart: "this is the same
    place" is worth saying even when you also want to name it yourself.

    Raises when the flag has nothing to resolve against: no neighbouring activity
    at all (the road is first or last in the day), or one that names no place. An
    arrival additionally has to end up *located*, since it is a point on the drawn
    route — the same requirement the last leg's ``end_coordinate`` always carried.

    Roads are settled left to right, so a drive can hand its arrival to the next
    drive's departure. Two drives pointing at each other resolve to nothing and
    raise, which is the honest answer: neither states the junction they share.
    """
    for i, act in enumerate(activities):
        if act.kind != "road":
            continue
        if act.same_start_as_previous_activity:
            prev = _neighbour(activities, i, -1)
            _share_start(act, prev)
        if act.same_end_as_next_activity:
            nxt = _neighbour(activities, i, +1)
            _share_end(act, nxt)


def _share_start(road: Road, prev: Activity | None) -> None:
    if prev is None:
        # Named by its arrival, since its departure is the very thing missing.
        raise ItineraryError(
            "'same_start_as_previous_activity' is set on the day's first "
            f"activity, the drive to {road.destination or 'nowhere named'} — "
            "there is no previous activity to take the departure from"
        )
    name = _place_name(prev, "end")
    if not road.start:
        if not name:
            raise ItineraryError(
                "'same_start_as_previous_activity' is set, but the previous "
                f"activity ({prev.title}) names no place to depart from — give "
                "the first leg a 'start_location'"
            )
        road.start = name
    if road.coordinate is None:
        # Still optional after this: a departure with only a name is geocoded,
        # exactly as a road's own start always was.
        road.coordinate = _place_coord(prev, "end")
    road.start_shared_with = prev


def _share_end(road: Road, nxt: Activity | None) -> None:
    if nxt is None:
        raise ItineraryError(
            "'same_end_as_next_activity' is set on the day's last activity, the "
            f"drive from {road.start or 'nowhere named'} — there is no next "
            "activity to take the arrival from"
        )
    if not road.waypoints:  # unreachable: 'legs' is required and non-empty
        return
    arrival = road.waypoints[-1]
    name = _place_name(nxt, "start")
    if not arrival.location:
        if not name:
            raise ItineraryError(
                "'same_end_as_next_activity' is set, but the next activity "
                f"({nxt.title}) names no place to arrive at — give the last leg "
                "an 'end_location'"
            )
        arrival.location = name
    if arrival.coordinate is None:
        arrival.coordinate = _place_coord(nxt, "start")
    if arrival.coordinate is None:
        raise ItineraryError(
            "'same_end_as_next_activity' is set, but the next activity "
            f"({nxt.title}) has no 'coordinate' — a drive's arrival is a point "
            "on its route, so it has to be located: give it one, or give the "
            "last leg an 'end_coordinate'"
        )
    road.end_shared_with = nxt


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
    * a **detour** is left out of the walk entirely and spliced back where the
      JSON wrote it (:func:`_splice_detours`), so it costs the day nothing: no
      minutes, and no buffer between it and the activity before it.
    """
    if any(act.detour for act in activities):
        planned = [act for act in activities if not act.detour]
        laid = schedule_activities(planned, day_start, default_buffer_min,
                                   day_end, auto_sized_buffer)
        return _splice_detours(laid, activities)

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


def resolve_detours(activities: list[Activity]) -> None:
    """Take every detour off the clock, in place, nested ones included: it keeps
    its ``duration`` — the one figure worth printing, since it says how long the
    stop *would* take — and loses both clock times, because it has no place on
    the timeline to have one.

    A stated ``start_time``/``end_time`` pair is folded into the duration first,
    so writing the visit as 10:00 → 11:30 and then marking it a detour still
    prints "1h30" (the validator warns that the times themselves are dropped).
    Doing it here rather than hiding the times per renderer is what makes "a
    detour has no time" true everywhere at once — the two books, the calendar
    export, the validator's opening-hours check.

    Run from :meth:`Day.from_dict` before the timeline pass, which then only has
    to leave the detours out of the walk (see :func:`schedule_activities`)."""
    for act in activities:
        if act.detour:
            if act.duration_min is None:
                act.duration_min = _item_minutes(act)
            act.start_time = act.end_time = None
        resolve_detours(getattr(act, "activities", []) or [])


def _splice_detours(laid: list[Activity], original: list[Activity]) -> list[Activity]:
    """Put the detours back into a laid-out day where the JSON wrote them —
    immediately after the activity they followed (or at the head of the day, for
    one written first), and ahead of any buffer that came after it: the buffer
    belongs to the two scheduled activities it separates, not to the stop hanging
    off between them.

    Matching is by identity, since two activities written alike compare equal as
    dataclasses."""
    out = list(laid)
    for i, act in enumerate(original):
        if not act.detour:
            continue
        anchor = next((a for a in reversed(original[:i]) if not a.detour), None)
        pos = 0 if anchor is None else _index_of(out, anchor) + 1
        # several detours in a row keep the order they were written in
        while pos < len(out) and out[pos].detour:
            pos += 1
        out.insert(pos, act)
    return out


def _index_of(items: list[Activity], target: Activity) -> int:
    for i, item in enumerate(items):
        if item is target:
            return i
    return len(items) - 1  # unreachable: `laid` never drops a real activity


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
    measurement of it.

    A nested **detour** contributes nothing either, for the same reason a
    top-level one takes no room on the timeline: the container is as long as what
    you actually plan to do inside it."""
    known = [m for m in (_item_minutes(a) for a in activities if not a.detour)
             if m is not None]
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
