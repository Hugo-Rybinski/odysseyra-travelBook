"""Data model for a travel itinerary loaded from JSON.

The model is split across submodules:

* :mod:`.parsers` — scalar parsers and ``ItineraryError``;
* :mod:`.activities` — the activity types and the day-scheduling pass;
* :mod:`.transport` — the ``Transport`` leg;
* :mod:`.accommodation` — the ``Accommodation``;
* :mod:`.itinerary` — the ``Day`` and ``Itinerary`` aggregates.
"""

from .accommodation import ACCOMMODATION_TYPES, Accommodation
from .car_rental import CAR_TYPES, CarRental, CarRentalEvent, resolve_car_rental
from .geo import Coordinate, _parse_coordinate
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
    activity_from_dict,
    schedule_activities,
)
from .itinerary import Day, Itinerary
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
)
from .transport import TRANSPORT_TYPES, Transport, resolve_transport

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
    "format_money",
    "SecondaryCurrency",
    "to_default",
    "Hike",
    "Itinerary",
    "ItineraryError",
    "Meal",
    "MEAL_TYPES",
    "NESTED_ACTIVITY_TYPES",
    "Place",
    "POI_CATEGORIES",
    "PointOfInterest",
    "Road",
    "Transport",
    "TRANSPORT_TYPES",
    "activity_from_dict",
    "resolve_car_rental",
    "resolve_transport",
    "schedule_activities",
    "_parse_coordinate",
    "_parse_currency",
    "_parse_price",
]
