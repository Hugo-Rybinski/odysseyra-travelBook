"""Field specifications and value validators used by the validator."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import (
    ItineraryError,
    _parse_coordinate,
    _parse_date,
    _parse_duration,
    _parse_paid,
    _parse_route,
    _parse_time,
    _parse_tz,
)


@dataclass
class Spec:
    name: str
    required: bool
    description: str
    expected: str
    default: str = ""
    check: object = None  # callable(value) -> error string | None
    warn_if_missing: bool = False  # a ⚠️ warning (not ℹ️ info) when absent


def _v(parser):
    def check(value):
        try:
            parser(value)
            return None
        except ItineraryError as exc:
            return str(exc)
    return check


V_DATE = _v(_parse_date)
V_TIME = _v(_parse_time)
V_DUR = _v(_parse_duration)
V_TZ = _v(_parse_tz)
V_ROUTE = _v(_parse_route)
V_PAID = _v(_parse_paid)


def V_NUMBER(value):
    if isinstance(value, bool):
        return "must be a number, not a boolean"
    if isinstance(value, (int, float)):
        return None
    try:
        float(value)
        return None
    except (TypeError, ValueError):
        return "must be a number"


def V_BOOL(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().lower() in (
        "true", "false", "yes", "no", "1", "0"
    ):
        return None
    return "must be true or false"


def V_STATUS(value):
    if str(value).strip().lower() in ("booked", "confirmed"):
        return None
    return "must be 'booked' or 'confirmed'"


def V_COUNT(value):
    if isinstance(value, bool):
        return "must be a whole number"
    try:
        n = int(value)
    except (TypeError, ValueError):
        return "must be a whole number"
    if n < 0:
        return "must be zero or more"
    return None


from ..models import (  # noqa: E402
    ACCOMMODATION_TYPES,
    CAR_TYPES,
    MEAL_TYPES,
    POI_CATEGORIES,
    TRANSPORT_TYPES,
)


def _enum_check(values):
    def check(value):
        if str(value).strip().lower() in values:
            return None
        return "must be one of: " + ", ".join(values)
    return check


V_CATEGORY = _enum_check(POI_CATEGORIES)
V_TTYPE = _enum_check(TRANSPORT_TYPES)
V_ATYPE = _enum_check(ACCOMMODATION_TYPES)
V_MEAL = _enum_check(MEAL_TYPES)
V_CAR_TYPE = _enum_check(CAR_TYPES)


def V_HEX(value):
    s = str(value).lstrip("#")
    if len(s) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in s):
        return None
    return "must be a hex color like '#2f6b4f'"


def V_CURRENCY(value):
    s = str(value).strip()
    if len(s) == 3 and s.isalpha():
        return None
    return "must be a 3-letter currency code like 'EUR'"


V_COORDINATE = _v(_parse_coordinate)


def V_ISO_COUNTRY(value):
    s = str(value).strip()
    if len(s) == 2 and s.isalpha():
        return None
    return "must be a 2-letter ISO country code like 'FR'"


# Trip-level groups
TRAVEL_DESCRIPTION = [
    Spec("title", True, "the trip title shown on the cover", "any text"),
    Spec("subtitle", False, "the subtitle under the cover title", "any text",
         '"" (no subtitle shown)'),
    Spec("start_date", False, "the trip start date (overrides inference)",
         "a date YYYY-MM-DD", "inferred from the earliest date", V_DATE),
    Spec("end_date", False, "the trip end date (overrides inference)",
         "a date YYYY-MM-DD", "inferred from the latest date", V_DATE),
    Spec("cover_color", False, "the accent color for the whole document",
         "a hex color like '#2f6b4f'", '"#1f4e5f" (teal)', V_HEX),
    Spec("summary", False, "a paragraph shown on the cover", "any text",
         '"" (no summary shown)'),
]

DEFAULTS = [
    Spec("start_time", False, "the day's default start time (first activity)",
         "a time HH:MM", '"08:00"', V_TIME),
    Spec("end_time", False, "the latest an activity should end each day",
         "a time HH:MM", "none (no end-of-day check)", V_TIME),
    Spec("buffer", False, "a buffer inserted between consecutive activities",
         "a duration like '15 min'", "0 (no buffer)", V_DUR),
    Spec("timezone", False, "the default UTC offset for all times",
         "an offset like '+02:00', 'UTC-3' or 'Z'", "GMT (UTC+0)", V_TZ),
    Spec("breakfast_until", False,
         "meals starting before this are categorized as breakfast",
         "a time HH:MM", '"10:00"', V_TIME),
    Spec("lunch_until", False,
         "meals starting up to this (after breakfast) are lunch, later ones dinner",
         "a time HH:MM", '"16:00"', V_TIME),
    Spec("meal_duration", False,
         "the default length of a meal that gives no duration or end time",
         "a duration like '1h'", "0 (instant)", V_DUR),
    Spec("currency", False, "the default currency all prices are given in",
         "a 3-letter ISO code like 'EUR'", '"EUR"', V_CURRENCY),
    Spec("secondary_currencies", False,
         "extra currencies to also show each price in, converted from the default",
         "an array of {currency, change_rate} objects", "[] (none shown)"),
    Spec("include_maps_in_render", False,
         "whether to draw a per-day OpenStreetMap with a pin for each activity",
         "true or false", "false (no maps)", V_BOOL),
    Spec("infer_coordinates_from_address", False,
         "whether to geocode activities that lack an explicit coordinate",
         "true or false",
         "false (only activities with an explicit coordinate are mapped)", V_BOOL),
    Spec("inference_countries", False,
         "ISO country codes to restrict geocoding to (when inferring coordinates)",
         "an array of 2-letter ISO codes like ['FR']", "[] (any country)"),
]

# Activity scheduling fields (shared by every non-buffer activity)
SCHEDULE = [
    Spec("start_time", False, "the clock time the activity starts", "a time HH:MM",
         "the previous activity's end, or the day's default start", V_TIME),
    Spec("end_time", False, "the clock time the activity ends", "a time HH:MM",
         "start_time + duration", V_TIME),
    Spec("duration", False, "how long the activity lasts",
         "a duration like '1h30' or '45 min'", "inferred from end_time, else 0", V_DUR),
    Spec("start_tz", False, "the start time zone", "a UTC offset like '+02:00'",
         "the trip's default timezone", V_TZ),
    Spec("end_tz", False, "the end time zone", "a UTC offset like '+02:00'",
         "the trip's default timezone", V_TZ),
]

ACTIVITY_SPECS = {
    "road": [
        Spec("start", True, "the departure address", "any text"),
        Spec("end", True, "the arrival address", "any text"),
        Spec("distance_km", False, "the driving distance in km", "a number",
             "none (not shown)", V_NUMBER),
        Spec("off_road", False, "whether part of the drive is off-road",
             "true or false", "false", V_BOOL),
        Spec("activities", False, "nested meals (a stop along the drive)",
             "an array of meal objects, each with a 'type'", "[] (none nested)"),
    ],
    "point_of_interest": [
        Spec("name", True, "the point-of-interest name", "any text"),
        Spec("category", False, "the kind of place, shown as the badge",
             "one of: " + ", ".join(POI_CATEGORIES), '"other"', V_CATEGORY),
        Spec("address", False, "the address", "any text", '""'),
        Spec("description", False, "a description", "any text", '""'),
        Spec("activities", False, "nested points of interest, hikes and meals",
             "an array of point_of_interest, hike or meal objects, each with a 'type'",
             "[] (none nested)"),
    ],
    "place": [
        Spec("name", True, "the place name", "any text"),
        Spec("description", False, "a description of the place", "any text", '""'),
        Spec("activities", False, "nested points of interest, hikes and meals",
             "an array of point_of_interest, hike or meal objects, each with a 'type'",
             "[] (none nested)"),
    ],
    "hike": [
        Spec("name", True, "the hike name", "any text"),
        Spec("description", False, "a description of the hike", "any text", '""'),
        Spec("distance_km", False, "the hike distance in km", "a number",
             "none", V_NUMBER, warn_if_missing=True),
        Spec("elevation_m", False, "the elevation gain in m", "a number",
             "none", V_NUMBER),
        Spec("start", False, "the trailhead address", "any text", '""'),
        Spec("end", False, "the end address", "any text", '""'),
        Spec("route", False, "the route shape",
             "'loop', 'back_and_forth' or 'one_way'", '"back_and_forth"', V_ROUTE),
        Spec("activities", False, "nested meals (a stop along the hike)",
             "an array of meal objects, each with a 'type'", "[] (none nested)"),
    ],
    "meal": [
        Spec("meal_type", False, "which meal it is",
             "one of: " + ", ".join(MEAL_TYPES), "inferred from the start time",
             V_MEAL),
        Spec("restaurant", False, "the restaurant name", "any text", '""'),
        Spec("area", False, "the town/region to eat in (used when no restaurant "
             "is named)", "any text", '""'),
        Spec("address", False, "the address", "any text", '""'),
    ],
    "buffer": [
        Spec("duration", True, "the length of the free time",
             "a duration like '30 min'", "", V_DUR),
    ],
}

DAY_SPECS = [
    Spec("title", True, "the day's title", "any text"),
    Spec("city", False, "the city/region label", "any text", '"" '),
    Spec("date", False, "the day's date", "a date YYYY-MM-DD",
         "the trip start date + the day's index in 'days'", V_DATE),
    Spec("description", False, "an intro paragraph for the day", "any text", '""'),
]

TRANSPORT_SPECS = [
    Spec("type", False, "the transport type", "one of: " + ", ".join(TRANSPORT_TYPES),
         '"other"', V_TTYPE),
    Spec("start", True, "the departure address", "any text"),
    Spec("end", True, "the arrival address", "any text"),
    Spec("start_date", True, "the departure date", "a date YYYY-MM-DD", "", V_DATE),
    Spec("end_date", False, "the arrival date", "a date YYYY-MM-DD",
         "inferred (+1 day if it crosses midnight)", V_DATE),
    Spec("start_time", True, "the departure time", "a time HH:MM", "", V_TIME),
    Spec("end_time", False, "the arrival time", "a time HH:MM",
         "none / inferred from start_time + duration", V_TIME),
    Spec("start_tz", False, "the departure time zone", "a UTC offset like '-04:00'",
         "the trip's default timezone", V_TZ),
    Spec("end_tz", False, "the arrival time zone", "a UTC offset like '+02:00'",
         "the trip's default timezone", V_TZ),
    Spec("duration", False, "the travel time", "a duration like '4h20'",
         "inferred from the two times", V_DUR),
    Spec("flight_number", False, "the flight number (planes only)", "any text", '""'),
    Spec("train_number", False, "the train number (trains only)", "any text", '""'),
    Spec("booking_number", False, "the reservation reference", "any text", '""'),
    Spec("booking_source", False, "where it was booked", "any text", '""'),
    Spec("status", False, "the reservation status", "'booked' or 'confirmed'",
         "none (no badge)", V_STATUS),
    Spec("price", False, "the ticket price", "a number", "none (no price shown)",
         V_NUMBER),
    Spec("currency", False, "the currency this price is in",
         "a 3-letter ISO code like 'USD'", "the trip's default currency", V_CURRENCY),
    Spec("paid", False, "the payment state", "'paid' or 'to pay'",
         "none (no badge)", V_PAID),
]

ACCOMMODATION_SPECS = [
    Spec("name", True, "the accommodation name", "any text"),
    Spec("arrival", True, "the check-in date", "a date YYYY-MM-DD", "", V_DATE),
    Spec("departure", True, "the check-out date", "a date YYYY-MM-DD", "", V_DATE),
    Spec("city", True, "the town, for the cover overview", "any text"),
    Spec("type", False, "the kind of accommodation",
         "one of: " + ", ".join(ACCOMMODATION_TYPES), '"hotel"', V_ATYPE),
    Spec("address", False, "the street address", "any text", '""'),
    Spec("contact", False, "a phone or email", "any text", '""'),
    Spec("booking_source", False, "where it was booked", "any text", '""'),
    Spec("price", False, "the price", "a number", "none (no price shown)", V_NUMBER),
    Spec("currency", False, "the currency this price is in",
         "a 3-letter ISO code like 'USD'", "the trip's default currency", V_CURRENCY),
    Spec("paid_online", False, "whether it is already paid", "true or false",
         "false (shows a 'To pay' badge)", V_BOOL),
    Spec("breakfast_included", False, "whether breakfast is included",
         "true or false", "false", V_BOOL),
]

CAR_RENTAL_SPECS = [
    Spec("booking_start_date", True, "the booking start date",
         "a date YYYY-MM-DD", "", V_DATE),
    Spec("booking_start_time", True, "the booking start time",
         "a time HH:MM", "", V_TIME),
    Spec("booking_end_date", True, "the booking end date",
         "a date YYYY-MM-DD", "", V_DATE),
    Spec("booking_end_time", True, "the booking end time",
         "a time HH:MM", "", V_TIME),
    Spec("pickup_date", True, "the pick-up date", "a date YYYY-MM-DD", "", V_DATE),
    Spec("pickup_time", True, "the pick-up time", "a time HH:MM", "", V_TIME),
    Spec("dropoff_date", True, "the drop-off date", "a date YYYY-MM-DD", "", V_DATE),
    Spec("dropoff_time", True, "the drop-off time", "a time HH:MM", "", V_TIME),
    Spec("pickup_location", True, "where you pick up the car", "any text"),
    Spec("dropoff_location", False, "where you drop off the car", "any text",
         "the pick-up location"),
    Spec("booking_start_tz", False, "the booking start time zone",
         "a UTC offset like '+02:00'", "the trip's default timezone", V_TZ),
    Spec("booking_end_tz", False, "the booking end time zone",
         "a UTC offset like '+02:00'", "the trip's default timezone", V_TZ),
    Spec("pickup_tz", False, "the pick-up time zone",
         "a UTC offset like '+02:00'", "the trip's default timezone", V_TZ),
    Spec("dropoff_tz", False, "the drop-off time zone",
         "a UTC offset like '+02:00'", "the trip's default timezone", V_TZ),
    Spec("company", False, "the rental company", "any text", '""'),
    Spec("booking_number", False, "the reservation reference", "any text", '""'),
    Spec("price", False, "the rental price", "a number", "none (no price shown)",
         V_NUMBER),
    Spec("currency", False, "the currency this price is in",
         "a 3-letter ISO code like 'USD'", "the trip's default currency", V_CURRENCY),
    Spec("paid", False, "the payment state", "'paid' or 'to pay'",
         "none (no badge)", V_PAID),
    Spec("car_type", False, "the car category",
         "one of: " + ", ".join(CAR_TYPES), '"regular"', V_CAR_TYPE),
    Spec("car_model", False, "the car make/model", "any text", '""'),
    Spec("contact", False, "a phone or email for the rental company",
         "any text", '""'),
    Spec("additional_drivers", False, "the number of additional drivers",
         "a whole number", "0", V_COUNT),
    Spec("pickup_duration", False, "how long the pick-up takes",
         "a duration like '30 min'", "none (not shown)", V_DUR),
    Spec("dropoff_duration", False, "how long the drop-off takes",
         "a duration like '30 min'", "none (not shown)", V_DUR),
]

