"""Per-day map cards: the main day map and the per-area detail maps, embedded
as images with a numbered legend. Only active when the trip opts into maps."""

from __future__ import annotations

import io

from .base import FONT


class DayMapMixin:
    def _maps_enabled(self) -> bool:
        return bool(getattr(self.itinerary, "include_maps_in_render", False))

    def _map_cache(self):
        if not hasattr(self, "_mapcache"):
            from ..maps import Cache
            self._mapcache = Cache.open(getattr(self, "map_cache_dir", None))
        return self._mapcache

    def day_maps(self, day):
        """Render (and memoize) this day's maps, or None. Never raises — a map
        problem (offline, geocode/tile failure) must not break the build."""
        if not self._maps_enabled():
            return None
        try:
            from ..maps import render_day_maps
            dm = render_day_maps(day, self.itinerary, self._map_cache(),
                                 ink_saver=self.ink_saver)
            self._map_cache().save()
            return dm
        except Exception:
            return None

    # -- drawing --------------------------------------------------------
    def _pin_disc(self, x: float, y: float, n: int) -> float:
        """A small accent disc with the pin number (matching the map pins),
        drawn inline before an activity title. Returns its width incl. a gap."""
        d = 4.8
        self.set_fill_color(*self.accent)
        self.ellipse(x, y, d, d, style="F")
        self.set_font(FONT, "B", 7)
        self.set_text_color(255, 255, 255)
        self.set_xy(x, y + 0.85)
        self.cell(d, 3, str(n), align="C")
        return d + 1.8

    def pin_number(self, act) -> int | None:
        """The pin number for ``act`` on this day's maps, if it has one."""
        dm = getattr(self, "_day_maps", None)
        return dm.number_for(act) if dm else None

    def _map_card(self, rendered, caption: str = "") -> None:
        """Embed one rendered map (full width, height-capped). The legend now
        lives in the itinerary text (pin numbers next to activity titles)."""
        img = rendered.image
        w = self.content_width
        h = w * img.height / img.width
        if h > 92:  # keep a map to ~1/3 of the page
            h = 92
            w = h * img.width / img.height
        if self.get_y() + h + 8 > self.h - self.b_margin:
            self.add_page()

        if caption:
            self.set_x(self.l_margin)
            self.set_font(FONT, "B", 8)
            self.set_text_color(*self.accent)
            self.cell(0, 5, caption, new_x="LMARGIN", new_y="NEXT")

        x = self.l_margin + (self.content_width - w) / 2
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        self.image(buf, x=x, w=w, h=h)
        self.ln(3)

    def day_main_map(self, dm) -> None:
        """Draw the main day map near the top of the day page (after the intro)."""
        if dm and dm.main:
            self._map_card(dm.main)

    def day_area_map(self, dm, title: str) -> None:
        """Draw the detail map for the area ``title`` (inline after it), if any."""
        if not dm:
            return
        for area_title, rendered in dm.areas:
            if area_title == title:
                self._map_card(rendered, caption=self.t("Zoom — {area}").format(area=title))
                return
