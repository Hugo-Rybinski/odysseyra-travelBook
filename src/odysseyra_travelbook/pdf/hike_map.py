"""A hike's GPX block: the trail map and the elevation profile, drawn inline in
the day's itinerary right under the hike that carries the ``gpx``.

Two different techniques on purpose. The **map** is a raster image, stitched from
basemap tiles by :func:`maps.build.render_hike_map` — the same pipeline (and the
same tile cache) as the day and trip maps, so the trail is drawn over the same
cartography. The **profile** is drawn natively with fpdf's vector primitives: it
is a chart of numbers the itinerary already carries, so it needs no tiles, no
network and no Pillow, stays crisp at any print resolution, and — the practical
part — still appears when the map can't be fetched at all.

Governed by ``defaults.include_hike_maps`` (on by default), independently of
``defaults.include_maps_in_render``: the geometry came attached to the hike, so
attaching it *is* the opt-in. The viewer draws the same two things from the same
resolved ``track`` (``web/src/render/HikeTrack.tsx``) — keep the two in step.
"""

from __future__ import annotations

import io
import logging

from .base import FAINT, FONT, MUTED, _tint

logger = logging.getLogger("odysseyra_travelbook.pdf")

# Height of the profile chart's plot area, and the room its labels need above
# (the header line) and below (the distance axis).
_PLOT_H = 22.0
_HEAD_H = 5.0
_AXIS_H = 4.0

# The trail map's drawn height is capped here (mm). A day page has an itinerary
# to fit around it, so the map is a figure in the flow, not the page.
_MAP_MAX_H = 68.0


class HikeMapMixin:
    def _hike_maps_enabled(self) -> bool:
        return bool(getattr(self.itinerary, "include_hike_maps", True))

    def hike_track(self, hike, x: float, w: float) -> None:
        """Draw ``hike``'s trail map and elevation profile, if it has a track.

        A no-op when the hike embeds no ``gpx`` or the trip switched hike maps
        off. Each half degrades on its own: a tile failure loses the map but
        keeps the profile, and a GPX without elevations draws the map alone.
        """
        track = getattr(hike, "track", None)
        if track is None or not self._hike_maps_enabled():
            return
        # The map is centred and usually narrower than the column (its aspect is
        # fixed, the column's isn't), so the profile takes the map's box rather
        # than the column's: the two then read as one stacked figure instead of
        # two charts of unrelated widths.
        box = self._hike_map(hike, track, x, w)
        self._hike_profile(track, *(box or (x, w)))

    # -- the trail map ---------------------------------------------------
    def _hike_map(self, hike, track, x: float, w: float) -> tuple[float, float] | None:
        """The GPX line over basemap tiles, captioned with the hike's name.
        Returns the ``(x, width)`` it drew at, or ``None`` when it drew nothing.

        Never raises: like every other map here, a fetch failure must not take
        the build down with it."""
        try:
            from ..maps import render_hike_map
            img = render_hike_map(track, self.itinerary.cover_color,
                                  self._map_cache(), ink_saver=self.ink_saver,
                                  lang=self.lang)
            self._map_cache().save()
        except Exception as exc:
            logger.warning("Hike trail map failed (%s); the elevation profile "
                           "is still drawn.", exc)
            return None
        if img is None:
            return None

        iw, ih = w, w * img.height / img.width
        if ih > _MAP_MAX_H:
            ih = _MAP_MAX_H
            iw = ih * img.width / img.height
        # `image()` draws wherever it's told — it doesn't trigger fpdf's auto
        # page break — so an over-long figure has to break the page itself.
        if self.get_y() + ih + 8 > self.h - self.b_margin:
            self.add_page()

        self.ln(1)
        ix = x + (w - iw) / 2
        caption = self.t("Trail — {name}").format(name=hike.title)
        self.set_font(FONT, "B", 7.5)
        self.set_text_color(*self.accent)
        self.set_xy(ix - self.c_margin, self.get_y())  # cancel the cell's inner pad
        self.cell(iw, 4.5, caption, new_x="LMARGIN", new_y="NEXT")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        self.image(buf, x=ix, y=self.get_y(), w=iw, h=ih)
        self.set_y(self.get_y() + ih)
        self.ln(1.5)
        return (ix, iw)

    # -- the elevation profile -------------------------------------------
    def _hike_profile(self, track, x: float, w: float) -> None:
        """Distance (x) against elevation (y), as a filled accent area under an
        accent curve: a header line naming it with the total climb and descent,
        the high mark inside the band, and the low mark and the length sharing
        the axis row beneath it.

        The y range is padded by a tenth of the climb so a flat walk reads as a
        flat line across the middle rather than a curve pinned to the floor and
        ceiling of its own noise.
        """
        profile = track.profile
        if len(profile) < 2:
            return  # no elevations in the file — the map stands alone
        total_h = _HEAD_H + _PLOT_H + _AXIS_H
        if self.get_y() + total_h + 4 > self.page_break_trigger:
            self.add_page()

        lo = min(p[1] for p in profile)
        hi = max(p[1] for p in profile)
        pad = max((hi - lo) * 0.1, 5.0)
        lo, hi = lo - pad, hi + pad
        km = profile[-1][0]

        # header: "Elevation profile   ↑ 780 m · ↓ 760 m"
        self.set_x(x)
        self.set_font(FONT, "B", 7.5)
        self.set_text_color(*self.accent)
        head = self.t("Elevation profile")
        self.cell(self.get_string_width(head) + 1, _HEAD_H, head)
        # A non-empty profile means the file carried elevations, so the climb
        # figures are always there to show alongside it.
        climb = "  ·  ".join((
            self.t("↑ {m} m").format(m=round(track.ascent_m or 0)),
            self.t("↓ {m} m").format(m=round(track.descent_m or 0)),
        ))
        self.set_font(FONT, "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, _HEAD_H, "   " + climb, new_x="LMARGIN", new_y="NEXT")

        top = self.get_y()
        bottom = top + _PLOT_H

        def px(k: float) -> float:
            return x + (w * k / km if km > 0 else 0)

        def py(m: float) -> float:
            return bottom - _PLOT_H * (m - lo) / (hi - lo)

        curve = [(px(k), py(m)) for k, m in profile]

        # a light baseline stands in for the x axis, without boxing the band in
        self.set_draw_color(*_tint(self.accent, 0.75))
        self.set_line_width(0.2)
        self.line(x, bottom, x + w, bottom)

        if not self.ink_saver:
            self.set_fill_color(*_tint(self.accent, 0.82))
            self.polygon([(x, bottom), *curve, (x + w, bottom)], style="F")
        self.set_draw_color(*self.accent)
        self.set_line_width(0.35)
        self.polyline(curve, style="D")

        # The high mark rides inside the band's top-left corner, where the curve
        # can't reach it (the padding above ``hi`` is what keeps that clear). The
        # low mark would collide with the curve at every trailhead, so it goes
        # *under* the baseline, sharing the axis row with the total distance.
        self.set_font(FONT, "", 6.5)
        self.set_text_color(*FAINT)
        self.set_xy(x + 0.6, top + 0.2)
        self.cell(w, 3, f"{round(hi - pad)} m")
        self.set_xy(x + 0.6, bottom + 0.2)
        self.cell(w / 2, _AXIS_H, f"{round(lo + pad)} m")
        self.set_xy(x + w / 2, bottom + 0.2)
        self.cell(w / 2 - 0.6, _AXIS_H, f"{km:.1f} km", align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)
