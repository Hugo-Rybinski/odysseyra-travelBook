"""Data model for a travel itinerary loaded from JSON.

The model is split across submodules:

* :mod:`.parsers` — scalar parsers and ``ItineraryError``;
* :mod:`.activities` — the activity types and the day-scheduling pass;
* :mod:`.gpx` — a hike's embedded GPX track (decode, parse, measure);
* :mod:`.gpx_export` — writing computed geometry back out as a GPX route;
* :mod:`.opening` — a point of interest's opening days and hours;
* :mod:`.misc` — the ``misc`` group (the trip's emergency contacts);
* :mod:`.transport` — the ``Transport`` booking and its ``TransportLeg``s;
* :mod:`.accommodation` — the ``Accommodation``;
* :mod:`.itinerary` — the ``Day`` and ``Itinerary`` aggregates.
"""

from .accommodation import ACCOMMODATION_TYPES, Accommodation
from .car_rental import CAR_TYPES, CarRental, CarRentalEvent, resolve_car_rental
from .geo import (
    DEFAULT_MAP_PROVIDER,
    MAP_PROVIDERS,
    Coordinate,
    maps_url,
    _parse_coordinate,
)
from .gpx import GpxTrack, decode_gpx, gpx_track, parse_gpx
from .gpx_export import route_gpx
from .opening import (
    WEEKDAYS,
    Opening,
    _parse_opening_days,
    _parse_opening_hours,
    parse_opening,
)
from .currency import (
    CURRENCY_SYMBOLS,
    SecondaryCurrency,
    format_money,
    to_default,
)
from .activities import (
    MEAL_TYPES,
    NESTED_ACTIVITY_TYPES,
    POI_CATEGORIES,
    Activity,
    Buffer,
    Hike,
    Meal,
    Place,
    PointOfInterest,
    Road,
    Waypoint,
    activity_from_dict,
    nested_duration_total,
    resolve_detours,
    schedule_activities,
)
from .itinerary import Day, Itinerary
from .misc import EmergencyContact, parse_emergency_contacts
from .moon import MoonPhase, moon_phase
from .serialize import to_dict
from .scheduling import Scheduled, Stamp
from .sun import SunTimes, sun_times
from .parsers import (
    ItineraryError,
    _format_duration,
    _format_tz,
    _parse_bool,
    _parse_currency,
    _parse_date,
    _parse_duration,
    _parse_paid,
    _parse_price,
    _parse_route,
    _parse_time,
    _parse_tz,
    format_elevation,
    format_km,
    round_elevation,
    round_km,
)
from .transport import (
    TRANSPORT_TYPES,
    Transport,
    TransportLeg,
    resolve_transport,
)

__all__ = [
    "Accommodation",
    "ACCOMMODATION_TYPES",
    "Activity",
    "Buffer",
    "CarRental",
    "CarRentalEvent",
    "CAR_TYPES",
    "Coordinate",
    "CURRENCY_SYMBOLS",
    "Day",
    "EmergencyContact",
    "parse_emergency_contacts",
    "format_money",
    "format_elevation",
    "format_km",
    "round_elevation",
    "round_km",
    "GpxTrack",
    "decode_gpx",
    "gpx_track",
    "parse_gpx",
    "route_gpx",
    "SecondaryCurrency",
    "to_default",
    "Hike",
    "Itinerary",
    "maps_url",
    "MAP_PROVIDERS",
    "DEFAULT_MAP_PROVIDER",
    "ItineraryError",
    "Meal",
    "MEAL_TYPES",
    "MoonPhase",
    "moon_phase",
    "NESTED_ACTIVITY_TYPES",
    "Opening",
    "parse_opening",
    "WEEKDAYS",
    "Place",
    "POI_CATEGORIES",
    "PointOfInterest",
    "Road",
    "Scheduled",
    "Stamp",
    "SunTimes",
    "sun_times",
    "to_dict",
    "Waypoint",
    "Transport",
    "TransportLeg",
    "TRANSPORT_TYPES",
    "activity_from_dict",
    "nested_duration_total",
    "resolve_car_rental",
    "resolve_detours",
    "resolve_transport",
    "schedule_activities",
    "_parse_coordinate",
    "_parse_currency",
    "_parse_opening_days",
    "_parse_opening_hours",
    "_parse_price",
]
