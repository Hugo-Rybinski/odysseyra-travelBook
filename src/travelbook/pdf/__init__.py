"""Render an :class:`~travelbook.models.Itinerary` to a polished PDF.

``TravelPDF`` is assembled from per-section mixins: :mod:`.cover`, :mod:`.days`,
:mod:`.transport` and :mod:`.accommodation`, on top of :mod:`.base`.
"""

from __future__ import annotations

from pathlib import Path

from ..lang import DEFAULT_LANGUAGE
from ..models import Itinerary
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
              lang: str = DEFAULT_LANGUAGE, ink_saver: bool = False) -> Path:
    """Render ``itinerary`` and write it to ``output``. Returns the path.

    When ``ink_saver`` is set, large solid accent fills (the cover banner, the
    per-page header bands, card backgrounds) are drawn as outlines and thin
    rules instead, so the print uses far less colored ink."""
    pdf = TravelPDF(itinerary, lang, ink_saver)
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
