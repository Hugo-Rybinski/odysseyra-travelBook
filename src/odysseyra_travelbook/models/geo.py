"""Geographic coordinates attached to itinerary objects for the day maps."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

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


# The navigation apps a "(Navigate)" link can target. Mirrors the web viewer's
# MAP_PROVIDERS (see web/src/render/nav.ts) so the two stay in step.
MAP_PROVIDERS = ("google", "apple", "osm", "waze", "mapsme")
DEFAULT_MAP_PROVIDER = "google"


def maps_url(
    coordinate: "Coordinate | None",
    *query_parts: str,
    provider: str = DEFAULT_MAP_PROVIDER,
) -> str:
    """A map/navigation URL pointing at the first available location: the exact
    ``coordinate`` when set, otherwise the first non-empty text part (an address
    or place name). Returns ``""`` when there is nothing locatable.

    ``provider`` picks the target app (see :data:`MAP_PROVIDERS`); it defaults to
    Google Maps. Opening the link on a phone launches that maps / navigation app
    with the destination pre-filled (a tap away from turn-by-turn directions); in
    a desktop browser the ``https`` providers open their web map. Google, Apple,
    OpenStreetMap and Waze are plain cross-platform ``https`` URLs; MAPS.ME uses
    its app-scheme deep link (no web fallback)."""
    if coordinate is not None:
        lat, long = coordinate.lat, coordinate.long
        if provider == "apple":
            ll = f"{lat},{long}"
            return f"https://maps.apple.com/?ll={ll}&q={quote(ll, safe=',')}"
        if provider == "osm":
            return (
                f"https://www.openstreetmap.org/?mlat={lat}&mlon={long}"
                f"#map=16/{lat}/{long}"
            )
        if provider == "waze":
            return f"https://waze.com/ul?ll={lat},{long}&navigate=yes"
        if provider == "mapsme":
            return f"mapsme://map?v=1&ll={lat},{long}&zoom=16"
        return f"https://www.google.com/maps/search/?api=1&query={lat},{long}"

    query = next((p.strip() for p in query_parts if p and p.strip()), "")
    if not query:
        return ""
    q = quote(query, safe=",")
    if provider == "apple":
        return f"https://maps.apple.com/?q={q}"
    if provider == "osm":
        return f"https://www.openstreetmap.org/search?query={q}"
    if provider == "waze":
        return f"https://waze.com/ul?q={q}&navigate=yes"
    if provider == "mapsme":
        return f"mapsme://search?query={q}"
    return "https://www.google.com/maps/search/?api=1&query=" + q
