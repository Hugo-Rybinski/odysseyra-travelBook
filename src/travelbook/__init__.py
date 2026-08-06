"""travelbook — turn a JSON travel itinerary into a polished PDF."""

from .models import (
    Accommodation,
    Activity,
    Buffer,
    Day,
    Hike,
    Itinerary,
    ItineraryError,
    Place,
    PointOfInterest,
    Road,
    Transport,
    activity_from_dict,
    resolve_transport,
    schedule_activities,
)
from .pdf import build_pdf
from .validate import Finding, format_findings, validate_text

__version__ = "0.7.0"

__all__ = [
    "Accommodation",
    "Activity",
    "Buffer",
    "Day",
    "Hike",
    "Itinerary",
    "ItineraryError",
    "Place",
    "PointOfInterest",
    "Road",
    "Transport",
    "Finding",
    "activity_from_dict",
    "resolve_transport",
    "schedule_activities",
    "build_pdf",
    "validate_text",
    "format_findings",
]
