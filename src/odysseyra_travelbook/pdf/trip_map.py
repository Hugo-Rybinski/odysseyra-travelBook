"""The whole-trip map page: every day's located points on a single map, pinned
with their day number. Only produced when the trip opts into maps.

The geometry and framing come from :func:`maps.build.render_trip_map`, which is a
port of the viewer's 🗺️ Overview map (``web/src/render/tripGeo.ts``) — the two
should stay in step.
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger("odysseyra_travelbook.pdf")


class TripMapMixin:
    def trip_map(self) -> None:
        """Add the whole-trip map page (right after the cover).

        Does nothing when maps are off, when nothing on the trip is located, or
        when the render fails — like the day maps, a map problem (offline,
        geocode/tile failure) must never break the build.
        """
        if not self._maps_enabled():
            return
        try:
            from ..maps import render_trip_map
            img = render_trip_map(self.itinerary, self._map_cache(),
                                  ink_saver=self.ink_saver, lang=self.lang)
            self._map_cache().save()
        except Exception as exc:
            logger.warning("The whole-trip map failed (%s); the page is skipped.", exc)
            return
        if img is None:
            return

        self.add_page()
        it = self.itinerary
        dates = ""
        if it.start_date and it.end_date:
            dates = f"{self.d(it.start_date, 'md')} – {self.d(it.end_date, 'md')}"
        elif it.start_date:
            dates = self.d(it.start_date, "md")
        self._band_header(self.t("MAP"), self.t("Whole trip"), dates)

        # Fill the page under the band, keeping the image's aspect ratio. The
        # 4 mm slack keeps a full-height map clear of the page footer.
        w = self.content_width
        avail = self.h - self.b_margin - self.get_y() - 4
        h = w * img.height / img.width
        if h > avail:
            h = avail
            w = h * img.width / img.height
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        self.image(buf, x=self.l_margin + (self.content_width - w) / 2,
                   y=self.get_y(), w=w, h=h)
