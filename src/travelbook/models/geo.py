"""Geographic coordinates attached to itinerary objects for the day maps."""

from __future__ import annotations

from dataclasses import dataclass

from .parsers import ItineraryError, _parse_bool, _parse_float


@dataclass
class Coordinate:
    """A point on the map. ``show_on_map`` defaults to True whenever a
    coordinate is given — set it False to keep the point for reference without
    plotting it."""

    lat: float
    long: float
    show_on_map: bool = True

    @classmethod
    def from_dict(cls, d: dict, name: str = "coordinate") -> "Coordinate":
        if not isinstance(d, dict):
            raise ItineraryError(f"{name} must be an object with 'lat' and 'long'")
        lat = _parse_float(d.get("lat"), f"{name}.lat")
        long = _parse_float(d.get("long"), f"{name}.long")
        if lat is None or long is None:
            raise ItineraryError(f"{name} needs both 'lat' and 'long'")
        if not -90 <= lat <= 90:
            raise ItineraryError(f"{name}.lat must be between -90 and 90 (got {lat})")
        if not -180 <= long <= 180:
            raise ItineraryError(
                f"{name}.long must be between -180 and 180 (got {long})"
            )
        show = d.get("show_on_map", True)
        return cls(lat=lat, long=long, show_on_map=_parse_bool(show))


def _parse_coordinate(value, name: str = "coordinate") -> Coordinate | None:
    """Parse an optional coordinate object (``None`` when unset)."""
    if value in (None, ""):
        return None
    return Coordinate.from_dict(value, name)
