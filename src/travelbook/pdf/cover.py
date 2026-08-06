"""The cover page and the day-by-day overview table."""

from __future__ import annotations

from .base import FONT, INK, LIGHT, MUTED, _tint


class CoverMixin:
    def cover(self) -> None:
        self.add_page()
        it = self.itinerary
        # Full-width accent band across the top third.
        band_h = self.h * 0.42
        if self.ink_saver:
            title_col = self.accent
            subtitle_col = MUTED
        else:
            self.set_fill_color(*self.accent)
            self.rect(0, 0, self.w, band_h, style="F")
            title_col = (255, 255, 255)
            subtitle_col = _tint(self.accent, 0.75)

        self.set_y(band_h * 0.42)
        self.set_x(self.l_margin)
        self.set_text_color(*title_col)
        self.set_font(FONT, "B", 34)
        self.multi_cell(self.content_width, 13, it.title, align="L")

        if it.subtitle:
            self.set_x(self.l_margin)
            self.set_font(FONT, "", 15)
            self.set_text_color(*subtitle_col)
            self.multi_cell(self.content_width, 8, it.subtitle, align="L")

        if self.ink_saver:  # a hairline marks the base of the header zone
            self.set_draw_color(*self.accent)
            self.set_line_width(0.6)
            self.line(self.l_margin, band_h, self.w - self.r_margin, band_h)

        # Meta block below the band.
        if it.start_date and it.end_date:
            date_range = f"{self.d(it.start_date, 'long')} – {self.d(it.end_date, 'long')}"
        elif it.start_date:
            date_range = self.d(it.start_date, "long")
        else:
            date_range = ""
        self.set_y(band_h + 16)
        self.set_text_color(*INK)
        for label, value in (
            ("Dates", date_range),
            ("Days", str(len(it.days))),
        ):
            if not value:
                continue
            self.set_x(self.l_margin)
            self.set_font(FONT, "B", 10)
            self.set_text_color(*self.accent)
            self.cell(28, 8, self.t(label).upper())
            self.set_font(FONT, "", 12)
            self.set_text_color(*INK)
            self.cell(0, 8, value, new_x="LMARGIN", new_y="NEXT")

        if it.summary:
            self.ln(6)
            self.set_x(self.l_margin)
            self.set_font(FONT, "", 11)
            self.set_text_color(*MUTED)
            self.multi_cell(self.content_width, 6, it.summary)

        self._overview()

    def _day_highlights(self, day) -> str:
        """A short, comma-joined summary of a day's notable items (in time
        order), including transport legs."""
        titles = []
        for item in self._day_items(day):
            if item.kind in ("point_of_interest", "place", "hike"):
                titles.append(item.title)
            elif item.kind == "road" and (item.duration_min or 0) > 60:
                titles.append(f"{self.t('Road')} {item.title}".strip())
            elif item.kind == "transport":
                ty = self.t(item.type).title() if item.type else ""
                titles.append(f"{ty} {item.title}".strip())
        if not titles:  # a pure transit/driving day — fall back to the drives
            titles = [f"{self.t('Road')} {a.title}".strip()
                      for a in day.activities if a.kind == "road"]
        return ", ".join(titles) if titles else "—"

    def _sleep_label(self, day) -> str:
        """Where you sleep that night: an accommodation, or an overnight leg."""
        stay = self.itinerary.stay_for(day.date)
        if stay is not None:
            return stay.city or stay.name
        night = self.itinerary.night_transport(day.date)
        if night is not None:
            return self._overnight_name(night)
        return "—"

    def _overnight_name(self, t) -> str:
        ty = (t.type or "").strip()
        if not ty:
            return self.t("Overnight travel")
        if any(w in ty.lower() for w in ("night", "overnight", "nuit")):
            return ty.capitalize()
        return self.t("Overnight {type}").format(type=self.t(ty))

    def _overview(self) -> None:
        """Day-by-day summary table shown on the cover page."""
        it = self.itinerary
        self.ln(8)
        self.set_x(self.l_margin)
        self.set_font(FONT, "B", 11)
        self.set_text_color(*self.accent)
        self.cell(0, 7, self.t("Day by day"), new_x="LMARGIN", new_y="NEXT")

        day_w, date_w, sleep_w = 12, 27, 36
        act_w = self.content_width - day_w - date_w - sleep_w
        x0 = self.l_margin
        offsets = (x0, x0 + day_w, x0 + day_w + date_w, x0 + day_w + date_w + act_w)

        # Header row.
        y = self.get_y()
        self.set_font(FONT, "B", 7.5)
        self.set_text_color(*MUTED)
        for (label, w), x in zip(
            (("DAY", day_w), ("DATE", date_w), ("HIGHLIGHTS", act_w), ("SLEEP", sleep_w)),
            offsets,
        ):
            self.set_xy(x, y)
            self.cell(w, 5, self.t(label))
        y += 6
        self.set_draw_color(*self.accent)
        self.set_line_width(0.4)
        self.line(x0, y, x0 + self.content_width, y)
        y += 2

        for i, day in enumerate(it.days, start=1):
            acts = self._day_highlights(day)
            sleep = self._sleep_label(day)
            date_s = self.d(day.date, "wd_md") if day.date else ""

            self.set_font(FONT, "", 9)
            lines = self.multi_cell(act_w - 2, 4.6, acts, dry_run=True, output="LINES")
            row_h = max(len(lines) * 4.6, 5) + 3
            if y + row_h > self.h - self.b_margin:
                self.add_page()
                y = self.get_y()

            self.set_xy(offsets[0], y)
            self.set_font(FONT, "B", 10)
            self.set_text_color(*self.accent)
            self.cell(day_w, 4.6, str(i))

            self.set_xy(offsets[1], y)
            self.set_font(FONT, "", 9)
            self.set_text_color(*INK)
            self.cell(date_w, 4.6, date_s)

            self.set_xy(offsets[2], y)
            self.set_text_color(*MUTED)
            self.multi_cell(act_w - 2, 4.6, acts)

            self.set_xy(offsets[3], y)
            self.set_text_color(*INK)
            self.multi_cell(sleep_w, 4.6, sleep)

            y += row_h
            self.set_draw_color(*LIGHT)
            self.set_line_width(0.2)
            self.line(x0, y - 1.5, x0 + self.content_width, y - 1.5)

        self.set_y(y)

