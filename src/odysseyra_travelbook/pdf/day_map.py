"""Per-day map cards: the main day map and the per-area detail maps, embedded
as images with a numbered legend. Only active when the trip opts into maps."""

from __future__ import annotations

import io
import logging

from .base import FONT

logger = logging.getLogger("odysseyra_travelbook.pdf")

# The inline pin disc: its diameter, and the horizontal room it takes including
# the gap to the text it labels. Published because a caller that wants to place
# a disc *inside* a line (see `_route_with_pins`) has to measure the line before
# drawing any of it.
PIN_D = 4.8
PIN_DISC_W = PIN_D + 1.8


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
                                 ink_saver=self.ink_saver, lang=self.lang)
            self._map_cache().save()
            return dm
        except Exception as exc:
            # Loud, because the alternative is a book that prints no maps while
            # the build reports success — the failure has to name itself.
            logger.warning("Day map for %r failed (%s); the day prints without one.",
                           getattr(day, "title", "?"), exc)
            return None

    # -- drawing --------------------------------------------------------
    def _pin_disc(self, x: float, y: float, label: str) -> float:
        """A small accent disc with the pin label (matching the map pins),
        drawn inline before an activity title. Returns its width incl. a gap."""
        d = PIN_D
        self.set_fill_color(*self.accent)
        self.ellipse(x, y, d, d, style="F")
        self.set_font(FONT, "B", 7)
        self.set_text_color(255, 255, 255)
        self.set_xy(x, y)
        self.cell(d, d, str(label), align="C")  # centered in the disc (h=d)
        return PIN_DISC_W

    def _route_width(self, ends, *, sep: str, size: float, style: str,
                     lead: str = "") -> float:
        """The width :meth:`_route_with_pins` would draw ``ends`` in. Separate
        from the drawing so a caller can decide whether the whole route fits one
        line *before* committing any of it to the page (the disc is drawn as it
        goes, so there is no backing out halfway)."""
        self.set_font(FONT, style, size)
        pad = 2 * self.c_margin  # a cell's own left+right inner padding
        total = self.get_string_width(lead) + pad if lead else 0.0
        for i, (pin, name) in enumerate(ends):
            text = name if i == len(ends) - 1 else name + sep
            total += self._end_width(pin, text)
        return total

    def _end_width(self, pin, text: str) -> float:
        """The room one end of a route takes — its disc, its text and the cell's
        own padding. The font must already be set (see :meth:`_route_width`)."""
        return (PIN_DISC_W if pin else 0.0) + self.get_string_width(text) \
            + 2 * self.c_margin

    def _route_with_pins(self, x: float, y: float, ends, *, sep: str, h: float,
                         size: float, style: str, color, lead: str = "",
                         max_w: float | None = None,
                         indent: float = 0.0) -> tuple[float, float]:
        """``(1) Amboise  →  (4) Sarlat-la-Canéda`` — a route with each end's map
        pin **beside the name it labels**, not bunched at the front. A pin number
        exists to point at one place, so a route with two pinned ends needs two
        discs in the right two spots; the alternative (both discs leading the
        line) reads as if they both belonged to the departure.

        ``ends`` is ``[(pin | None, name), …]`` and ``lead`` an optional prefix
        (the VIA list's bullet). Returns the ``(x, y)`` it ended at.
        ``_pin_disc`` sets its own font and colour, so both are re-applied for
        every text run.

        Given ``max_w`` the route breaks **between two ends** — after the arrow,
        onto a fresh line indented by ``indent`` — rather than running off the
        column. Two long place names are the one route that doesn't fit a line,
        and paper can't reflow; breaking there keeps each name's disc against
        it, which wrapping the whole thing as prose would lose (that is the
        concession :meth:`_road_title` makes, and why it declines the job
        instead). The break is greedy and per end, so a caller can predict the
        line count from :meth:`_end_width` alone."""
        tx, ty = x, y

        def run(text: str) -> None:
            nonlocal tx
            self.set_font(FONT, style, size)
            self.set_text_color(*color)
            self.set_xy(tx, ty)
            self.cell(self.get_string_width(text) + 2 * self.c_margin, h, text)
            tx = self.get_x()

        if lead:
            run(lead)
        for i, (pin, name) in enumerate(ends):
            text = name if i == len(ends) - 1 else name + sep
            self.set_font(FONT, style, size)
            if i and max_w is not None and \
                    tx + self._end_width(pin, text) > x + max_w:
                tx, ty = x + indent, ty + h
            if pin:
                tx += self._pin_disc(tx, ty + (h - PIN_D) / 2, pin)
            run(text)
        return tx, ty

    def pin_label(self, act):
        """The pin label (number, area letter or '*') for ``act``, if it has one."""
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

        # The map is centered when narrower than the text column; align the
        # caption to the map's left edge (not the page margin) so they line up.
        x = self.l_margin + (self.content_width - w) / 2
        if caption:
            self.set_font(FONT, "B", 8)
            self.set_text_color(*self.accent)
            self.set_xy(x - self.c_margin, self.get_y())  # cancel the cell's inner pad
            self.cell(w, 5, caption, new_x="LMARGIN", new_y="NEXT")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        self.image(buf, x=x, w=w, h=h)
        self.ln(3)

    def day_main_map(self, dm, index: int) -> None:
        """Draw the main day map near the top of the day page (after the intro)."""
        if dm and dm.main:
            caption = self.t("Day {index} overview").format(index=index)
            self._map_card(dm.main, caption=caption)

    def day_area_map(self, dm, title: str) -> None:
        """Draw the detail map for the area ``title`` (inline after it), if any."""
        if not dm:
            return
        for area_title, rendered in dm.areas:
            if area_title == title:
                self._map_card(rendered, caption=self.t("Zoom — {area}").format(area=title))
                return
