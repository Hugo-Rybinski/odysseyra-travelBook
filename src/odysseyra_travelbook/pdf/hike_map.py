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

from ..models import elevation_grid, format_km, round_elevation
from .base import FAINT, FONT, MUTED, _tint

logger = logging.getLogger("odysseyra_travelbook.pdf")

# Height of the profile chart's plot area, and the room its labels need above
# (the header line) and below (the distance axis). The band is taller than a
# chart of two figures needs because it is now ruled at round altitudes as well:
# eight lines across 22 mm put their numbers 2.75 mm apart, which is barely more
# than the 6.5 pt type they are set in.
_PLOT_H = 30.0
_HEAD_H = 5.0
_AXIS_H = 4.0

# The scale gutter to the left of the band, holding those round altitudes
# right-aligned. Outside the plot, not inside it: the curve reaches the left edge
# at the trailhead, so a number laid over the band there would sit on the line it
# is labelling. Four digits at 6.5 pt measure 5.83 mm, and a `cell` spends 1 mm
# of inner padding at each end, so 9 mm holds a Himalayan altitude with 1.8 mm
# left over between it and the band.
_SCALE_W = 9.0

# The trail map's drawn height is capped here (mm). A day page has an itinerary
# to fit around it, so the map is a figure in the flow, not the page.
_MAP_MAX_H = 68.0

# A distance number this close to either end of the axis (as a fraction of the
# width) is dropped: the row already carries the low elevation on the left and
# the total length on the right, and a km number under either is two figures in
# one place. A *fraction* rather than a measured collision so the viewer's twin
# can apply the identical rule in CSS-land (`HikeTrack.tsx`).
_KM_LABEL_EDGE = 0.07


class HikeMapMixin:
    def _hike_maps_enabled(self) -> bool:
        return bool(getattr(self.itinerary, "include_hike_maps", True))

    def hike_track(self, hike, x: float, w: float) -> None:
        """Draw ``hike``'s trail map and elevation profile, if it has a track.

        A no-op when the hike embeds no ``gpx`` or the trip switched hike maps
        off. Each half degrades on its own: a tile failure loses the map but
        keeps the profile, and a GPX without elevations draws the map alone.

        The hike's own ``show_map`` drops the **map** and nothing else — the
        profile still draws, and the viewer still offers the GPX for download.
        The field says *map*, and a profile is a chart of the numbers the hike
        already states; ``defaults.include_hike_maps`` remains the switch for the
        whole figure (it also keeps the geometry out of the resolved document,
        which this can't: the profile needs it).
        """
        track = getattr(hike, "track", None)
        if track is None or not self._hike_maps_enabled():
            return
        # The map is centred and usually narrower than the column (its aspect is
        # fixed, the column's isn't), so the profile takes the map's box rather
        # than the column's: the two then read as one stacked figure instead of
        # two charts of unrelated widths.
        box = (self._hike_map(hike, track, x, w)
               if getattr(hike, "show_map", True) else None)
        self._hike_profile(track, *(box or (x, w)))

    # -- the trail map ---------------------------------------------------
    def _hike_map(self, hike, track, x: float, w: float) -> tuple[float, float] | None:
        """The GPX line over basemap tiles, captioned with the hike's name.
        Returns the ``(x, width)`` it drew at, or ``None`` when it drew nothing.

        The trail's decoration — direction arrowheads, the start/finish markers,
        the points the file names — arrives *inside* the image
        (``maps.build.render_hike_map`` → ``maps.render.Trail``), which is why
        nothing here draws it and why the viewer's interactive twin has to build
        it itself (``DayMapGL.tsx``).

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
        a gutter of round altitudes ruling the band, the high mark inside it, and
        the low mark and the length sharing the axis row beneath.

        The y range is padded by a tenth of the climb so a flat walk reads as a
        flat line across the middle rather than a curve pinned to the floor and
        ceiling of its own noise.

        The gutter is taken out of the left of ``(x, w)`` — which is the map's
        box, so the band is inset from the image above it by that much and the
        two still read as one stacked figure (the gutter is whitespace and a
        column of small numbers).
        """
        profile = track.profile
        if len(profile) < 2:
            return  # no elevations in the file — the map stands alone
        total_h = _HEAD_H + _PLOT_H + _AXIS_H
        if self.get_y() + total_h + 4 > self.page_break_trigger:
            self.add_page()

        low = min(p[1] for p in profile)
        high = max(p[1] for p in profile)
        pad = max((high - low) * 0.1, 5.0)
        lo, hi = low - pad, high + pad
        km = profile[-1][0]
        # The band's own scale: round altitudes between the walk's low and high
        # marks. The padding above and below them is left clear — a line there
        # would be ruling air the walk never reached.
        grid = elevation_grid(low, high)
        # the plot box, with the gutter taken off the left
        x, w = x + _SCALE_W, w - _SCALE_W

        # header: "Elevation profile   ↑ 780 m · ↓ 760 m"
        self.set_x(x)
        self.set_font(FONT, "B", 7.5)
        self.set_text_color(*self.accent)
        head = self.t("Elevation profile")
        self.cell(self.get_string_width(head) + 1, _HEAD_H, head)
        # A non-empty profile means the file carried elevations, so the climb
        # figures are always there to show alongside it — rounded for display
        # like every other climb in the book (models/parsers.py), since they are
        # accumulated off an altimeter.
        climb = "  ·  ".join((
            self.t("↑ {m} m").format(m=round_elevation(track.ascent_m or 0)),
            self.t("↓ {m} m").format(m=round_elevation(track.descent_m or 0)),
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

        # The altitude scale, ruled across the band and numbered in the gutter.
        # Lighter than the kilometre hairlines below: those pair the figure with
        # the trail map, so they stay the marks that read first.
        if grid:
            self.set_draw_color(*_tint(self.accent, 0.74))
            self.set_line_width(0.12)
            for m in grid:
                self.line(x, py(m), x + w, py(m))
            self.set_font(FONT, "", 6.5)
            self.set_text_color(*FAINT)
            for m in grid:
                # centred on its line: a 6.5 pt line of type is ~2.3 mm tall
                self.set_xy(x - _SCALE_W, py(m) - 1.5)
                self.cell(_SCALE_W - 0.8, 3, str(m), align="R")

        # The distance marks, as hairlines up through the band — drawn over the
        # fill and under the curve, so the profile still reads as one shape. Same
        # kilometres, same numbers, as the trail map's ticks: that pairing is the
        # whole point, and it holds because `models/gpx.py` decides the step once
        # for both figures.
        marks = [m.km for m in getattr(track, "km_marks", []) if 0 < m.km < km]
        if marks:
            self.set_draw_color(*_tint(self.accent, 0.62))
            self.set_line_width(0.15)
            for k in marks:
                self.line(px(k), top, px(k), bottom)

        self.set_draw_color(*self.accent)
        self.set_line_width(0.35)
        self.polyline(curve, style="D")

        # The high mark rides inside the band's top-left corner, where the curve
        # can't reach it (the padding above ``hi`` is what keeps that clear). The
        # low mark would collide with the curve at every trailhead, so it goes
        # *under* the baseline, sharing the axis row with the total distance.
        # These two are the walk's own altitudes and keep their ``m``; the
        # gutter's are the scale it is drawn against, and stay bare numbers — so
        # a figure standing in the gutter's column is never a measured one.
        self.set_font(FONT, "", 6.5)
        self.set_text_color(*FAINT)
        self.set_xy(x + 0.6, top + 0.2)
        self.cell(w, 3, f"{round(high)} m")
        self.set_xy(x + 0.6, bottom + 0.2)
        self.cell(w / 2, _AXIS_H, f"{round(low)} m")
        # each mark's kilometre, centred under its hairline — the numbers the
        # trail map wears too, so the reader can carry one figure onto the other
        for k in marks:
            if not _KM_LABEL_EDGE < k / km < 1 - _KM_LABEL_EDGE:
                continue
            self.set_xy(px(k) - 4, bottom + 0.2)
            self.cell(8, _AXIS_H, str(k), align="C")
        self.set_xy(x + w / 2, bottom + 0.2)
        self.cell(w / 2 - 0.6, _AXIS_H, format_km(km), align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)
