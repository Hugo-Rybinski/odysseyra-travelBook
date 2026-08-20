"""Render an :class:`~odysseyra_travelbook.models.Itinerary` to a polished PDF.

``TravelPDF`` is assembled from per-section mixins: :mod:`.cover`, :mod:`.days`,
:mod:`.transport` and :mod:`.accommodation`, on top of :mod:`.base`.
"""

from __future__ import annotations

from pathlib import Path

from ..lang import DEFAULT_LANGUAGE
from ..models import DEFAULT_MAP_PROVIDER, Itinerary
from .accommodation import AccommodationMixin
from .base import _PDFBase
from .car_rental import CarRentalMixin
from .cover import CoverMixin
from .day_map import DayMapMixin
from .days import DayMixin
from .transport import TransportMixin


class TravelPDF(CoverMixin, DayMixin, DayMapMixin, TransportMixin,
                AccommodationMixin, CarRentalMixin, _PDFBase):
    """The travel-book PDF, assembled from per-section mixins."""


def build_pdf(itinerary: Itinerary, output: str | Path,
              lang: str = DEFAULT_LANGUAGE, ink_saver: bool = False,
              maps: bool | None = None, cache_dir: str | Path | None = None,
              map_provider: str = DEFAULT_MAP_PROVIDER) -> Path:
    """Render ``itinerary`` and write it to ``output``. Returns the path.

    When ``ink_saver`` is set, large solid accent fills (the cover banner, the
    per-page header bands, card backgrounds) are drawn as outlines and thin
    rules instead, so the print uses far less colored ink.

    ``maps`` overrides ``defaults.include_maps_in_render`` for this build;
    ``cache_dir`` overrides where map tiles/geocode/route results are cached.
    ``map_provider`` picks which app the inline "(Navigate)" links open (see
    :data:`~odysseyra_travelbook.models.MAP_PROVIDERS`; default Google Maps)."""
    if maps is not None:
        itinerary.include_maps_in_render = maps
    pdf = TravelPDF(itinerary, lang, ink_saver, map_provider)
    if cache_dir is not None:
        pdf.map_cache_dir = cache_dir
    pdf.cover()
    for i, day in enumerate(itinerary.days, start=1):
        pdf.day(i, day)
    if itinerary.transports or itinerary.car_rentals:
        pdf.transports()
    if itinerary.accommodations:
        pdf.accommodations()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output))
    return output


__all__ = ["TravelPDF", "build_pdf"]
