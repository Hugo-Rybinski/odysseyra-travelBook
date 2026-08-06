"""Per-day pages: header band, the merged itinerary (activities + transport),
and the bottom stay bar."""

from __future__ import annotations

from datetime import time

from ..models import Day
from .base import FONT, INK, LIGHT, MUTED


class DayMixin:
    def day(self, index: int, day: Day) -> None:
        self.add_page()
        meta_bits = [b for b in (day.city, self.d(day.date, "wd_full_md")) if b]
        kicker = self.t("DAY {index}").format(index=index)
        self._band_header(kicker, day.title, "   ".join(meta_bits))

        if day.description:
            self.set_font(FONT, "", 11)
            self.set_text_color(*MUTED)
            self.multi_cell(self.content_width, 6, day.description)
            self.ln(3)

        items = self._day_items(day)
        if items:
            self._section_title(self.t("Itinerary"))
            for item in items:
                if item.kind == "buffer":
                    self._buffer(item)
                elif item.kind == "meal":
                    self._meal(item)
                elif item.kind == "transport":
                    self._transport_row(item)
                elif item.kind in ("car_pickup", "car_dropoff"):
                    self._car_rental_row(item)
                else:
                    self._activity(item)

        self._day_stay(day)

    def _day_items(self, day):
        """Activities, same-day transports and car pick-up/drop-off events,
        merged and sorted by start time."""
        items = (list(day.activities)
                 + self.itinerary.transports_on(day.date)
                 + self.itinerary.car_events_on(day.date))
        items.sort(key=lambda x: (x.start_time is None, x.start_time or time(0, 0)))
        return items

    def _day_stay(self, day) -> None:
        """A compact bar at the bottom of the day's page for that night — an
        accommodation, or an overnight transport leg if you sleep aboard one."""
        acc = self.itinerary.stay_for(day.date)
        if acc is not None:
            total, night = acc.nights, acc.night_of(day.date)
            right = (self.t("Night {night}/{total} here").format(night=night, total=total)
                     if total and total > 1 and night else "")
            sub = "  ·  ".join(p for p in (acc.address, self._booked_text(acc)) if p)
            self._bottom_bar(acc.name, sub, right)
            return
        leg = self.itinerary.night_transport(day.date)
        if leg is not None:
            times = self._transport_times(leg)
            sub = "  ·  ".join(p for p in (leg.title, times) if p)
            self._bottom_bar(self._overnight_name(leg), sub, self.t("on board"))

    def _bottom_bar(self, name: str, sub: str, right: str = "") -> None:
        # bar_h leaves ~3 mm below the sub line to match the padding above the
        # kicker (the sub cell ends at offset pad+9+4 = 17; 17 + 3 = 20).
        bar_h, pad = 20, 4
        # Pin to the lower part of the page, but never over the day's content.
        y = max(self.get_y() + 6, self.h - 24 - bar_h)
        cx = self.l_margin + pad + 2

        self._card_bg(y, bar_h)

        self.set_xy(cx, y + pad - 1)
        self.set_font(FONT, "B", 7)
        self.set_text_color(*self.accent)
        self.cell(0, 4, self.t("TONIGHT'S STAY"))
        if right:
            self.set_xy(self.l_margin, y + pad - 1)
            self.set_font(FONT, "B", 8)
            self.set_text_color(*self.accent)
            self.cell(self.content_width - pad, 4, right, align="R")

        self.set_xy(cx, y + pad + 3.5)
        self.set_font(FONT, "B", 11)
        self.set_text_color(*INK)
        self.cell(0, 5, name)

        maxw = self.content_width - 2 * pad - 2
        self.set_font(FONT, "", 8.5)
        while sub and "  ·  " in sub and self.get_string_width(sub) > maxw:
            sub = sub.rsplit("  ·  ", 1)[0]
        self.set_xy(cx, y + pad + 9)
        self.set_text_color(*MUTED)
        self.cell(maxw, 4, sub)

        self.set_y(y + bar_h)

    GUTTER = 28  # left column reserved for the type badge

    def _activity(self, act) -> None:
        top = self.get_y()
        x = self.l_margin + self.GUTTER
        detail_w = self.content_width - self.GUTTER

        self._badge(self.l_margin, top, self.GUTTER - 5, self._badge_label(act))
        gw = self.GUTTER - 5
        if act.start_time is not None:
            stz = self._tz_label(act.start_tz)
            slbl = f"{act.start_time:%H:%M}" + (f" {stz}" if stz else "")
            self.set_xy(self.l_margin, top + 6.8)
            self.set_font(FONT, "B", 7 if stz else 8)
            self.set_text_color(*self.accent)
            self.cell(gw, 4, slbl, align="C")
            if act.end_time is not None and act.end_time != act.start_time:
                etz = self._tz_label(act.end_tz)
                elbl = f"{act.end_time:%H:%M}" + (f" {etz}" if etz else "")
                self.set_xy(self.l_margin, top + 10.6)
                self.set_font(FONT, "", 6.5 if etz else 7)
                self.set_text_color(*MUTED)
                self.cell(gw, 3.5, elbl, align="C")

        self.set_xy(x, top)
        self.set_font(FONT, "B", 11)
        self.set_text_color(*INK)
        self.multi_cell(detail_w, 6, act.title)

        # Type-specific details.
        getattr(self, f"_details_{act.kind}")(act, x, detail_w)

        # Keep the row at least as tall as the gutter time block.
        self.set_y(max(self.get_y(), top + 15))
        y = self.get_y()
        self.set_draw_color(*LIGHT)
        self.set_line_width(0.2)
        self.line(x, y, self.w - self.r_margin, y)
        self.ln(2)

    def _buffer(self, buf) -> None:
        x = self.l_margin + self.GUTTER
        self.set_x(x)
        self.set_font(FONT, "I", 8.5)
        self.set_text_color(*MUTED)
        label = buf.duration_display or "—"
        self.cell(0, 5, f"{self.t('buffer')}  ·  {label}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def _meal(self, meal) -> None:
        """A meal — laid out like a buffer (a compact inline row, no card) but
        accented: the accent color, a bold '<meal type> at <restaurant>' head,
        the start time in the gutter, and a muted duration/address line. The
        meal type is explicit or inferred from the start time."""
        top = self.get_y()
        x = self.l_margin + self.GUTTER
        gw = self.GUTTER - 5
        if meal.start_time is not None:
            self.set_xy(self.l_margin, top)
            self.set_font(FONT, "B", 8)
            self.set_text_color(*self.accent)
            self.cell(gw, 5, f"{meal.start_time:%H:%M}", align="C")

        label = self.t(meal.type).capitalize()
        if meal.restaurant:
            head = self.t("{meal} at {restaurant}").format(
                meal=label, restaurant=meal.restaurant)
        elif meal.area:
            head = self.t("{meal} near {area}").format(meal=label, area=meal.area)
        else:
            head = label
        self.set_xy(x, top)
        self.set_font(FONT, "B", 9.5)
        self.set_text_color(*self.accent)
        self.cell(0, 5, head, new_x="LMARGIN", new_y="NEXT")

        meta = "  ·  ".join(p for p in (meal.duration_display, meal.address) if p)
        if meta:
            self.set_x(x)
            self.set_font(FONT, "", 8.5)
            self.set_text_color(*MUTED)
            self.cell(0, 4.5, meta, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def _transport_row(self, t) -> None:
        """A transport leg shown inline in a day's itinerary."""
        top = self.get_y()
        x = self.l_margin + self.GUTTER
        detail_w = self.content_width - self.GUTTER
        gw = self.GUTTER - 5

        self._badge(self.l_margin, top, gw,
                    self.t(t.type).upper() if t.type else self.t("TRANSPORT"))
        if t.start_time is not None:
            stz = self._tz_label(t.start_tz)
            slbl = f"{t.start_time:%H:%M}" + (f" {stz}" if stz else "")
            self.set_xy(self.l_margin, top + 6.8)
            self.set_font(FONT, "B", 7 if stz else 8)
            self.set_text_color(*self.accent)
            self.cell(gw, 4, slbl, align="C")
            if t.end_time is not None and t.end_time != t.start_time:
                etz = self._tz_label(t.end_tz)
                elbl = f"{t.end_time:%H:%M}"
                if etz:
                    elbl += f" {etz}"
                if t.end_day_offset:
                    elbl += f" +{t.end_day_offset}"
                self.set_xy(self.l_margin, top + 10.6)
                self.set_font(FONT, "", 6.5 if (etz or t.end_day_offset) else 7)
                self.set_text_color(*MUTED)
                self.cell(gw, 3.5, elbl, align="C")

        self.set_xy(x, top)
        self.set_font(FONT, "B", 11)
        self.set_text_color(*INK)
        self.multi_cell(detail_w, 6, t.title)

        meta = "  ·  ".join(
            p for p in (t.duration_display, self._transport_booking(t)) if p
        )
        if meta:
            self.set_x(x)
            self.set_font(FONT, "", 9)
            self.set_text_color(*MUTED)
            self.multi_cell(detail_w, 5, meta)
        if t.overnight:
            self._chip(x, self.t("OVERNIGHT"))

        self.set_y(max(self.get_y(), top + 15))
        y = self.get_y()
        self.set_draw_color(*LIGHT)
        self.set_line_width(0.2)
        self.line(x, y, self.w - self.r_margin, y)
        self.ln(2)

    def _car_descriptor(self, cr) -> str:
        name = "  ·  ".join(p for p in (cr.company, cr.car_model) if p)
        label = self.t(cr.car_type_label)
        if label:
            name = f"{name} ({label})" if name else label
        return name

    def _car_rental_row(self, ev) -> None:
        """A car-rental pick-up or drop-off shown inline in a day's itinerary."""
        top = self.get_y()
        x = self.l_margin + self.GUTTER
        detail_w = self.content_width - self.GUTTER
        gw = self.GUTTER - 5

        label = self.t("PICK-UP") if ev.kind == "car_pickup" else self.t("DROP-OFF")
        self._badge(self.l_margin, top, gw, label)
        if ev.start_time is not None:
            stz = self._tz_label(ev.start_tz)
            slbl = f"{ev.start_time:%H:%M}" + (f" {stz}" if stz else "")
            self.set_xy(self.l_margin, top + 6.8)
            self.set_font(FONT, "B", 7 if stz else 8)
            self.set_text_color(*self.accent)
            self.cell(gw, 4, slbl, align="C")
            if ev.end_time is not None and ev.end_time != ev.start_time:
                self.set_xy(self.l_margin, top + 10.6)
                self.set_font(FONT, "", 7)
                self.set_text_color(*MUTED)
                self.cell(gw, 3.5, f"{ev.end_time:%H:%M}", align="C")

        head = self.t("Pick up the rental car") if ev.kind == "car_pickup" \
            else self.t("Drop off the rental car")
        self.set_xy(x, top)
        self.set_font(FONT, "B", 11)
        self.set_text_color(*INK)
        self.multi_cell(detail_w, 6, head)

        cr = ev.rental
        meta = "  ·  ".join(p for p in (
            ev.location,
            ev.duration_display,
            self._car_descriptor(cr),
            self.t("Ref {ref}").format(ref=cr.booking_number) if cr.booking_number else "",
        ) if p)
        if meta:
            self.set_x(x)
            self.set_font(FONT, "", 9)
            self.set_text_color(*MUTED)
            self.multi_cell(detail_w, 5, meta)

        self.set_y(max(self.get_y(), top + 15))
        y = self.get_y()
        self.set_draw_color(*LIGHT)
        self.set_line_width(0.2)
        self.line(x, y, self.w - self.r_margin, y)
        self.ln(2)

    def _badge_label(self, act) -> str:
        if act.kind == "point_of_interest":
            if act.category and act.category != "other":
                return self.t(act.category).upper()[:14]
            return self.t("POINT")
        if act.kind == "place":
            return self.t("PLACE")
        return self.t("ROAD") if act.kind == "road" else self.t("HIKE")

    def _details_road(self, act, x: float, w: float) -> None:
        parts = [act.duration_display]
        if act.distance_km is not None:
            parts.append(f"{act.distance_km:g} km")
        self._meta_line(x, w, parts)
        if act.off_road:
            self._chip(x, self.t("OFF-ROAD SECTIONS"))

    def _details_point_of_interest(self, act, x: float, w: float) -> None:
        parts = [act.duration_display]
        if act.address:
            parts.append(act.address)
        self._meta_line(x, w, parts)
        if act.description:
            self._para(x, w, act.description)

    def _details_place(self, act, x: float, w: float) -> None:
        self._meta_line(x, w, [act.duration_display])
        if act.description:
            self._para(x, w, act.description)
        if act.points_of_interest:
            self.ln(1)
            self.set_x(x)
            self.set_font(FONT, "B", 8)
            self.set_text_color(*self.accent)
            self.cell(0, 5, self.t("POINTS OF INTEREST"), new_x="LMARGIN", new_y="NEXT")
            for poi in act.points_of_interest:
                self._nested_poi(x + 5, w - 5, poi)

    def _details_hike(self, act, x: float, w: float) -> None:
        parts = [act.duration_display]
        if act.distance_km is not None:
            parts.append(f"{act.distance_km:g} km")
        if act.elevation_m is not None:
            parts.append(f"+{act.elevation_m:g} m")
        parts.append(self.t(act.route_label))
        self._meta_line(x, w, parts)
        if act.name and act.start and act.end:
            self._para(x, w, f"{act.start} → {act.end}")
        if act.description:
            self._para(x, w, act.description)

    def _nested_poi(self, x: float, w: float, poi) -> None:
        top = self.get_y()
        # Bullet marker in the accent color.
        self.set_xy(x, top)
        self.set_font(FONT, "B", 10)
        self.set_text_color(*self.accent)
        self.cell(4, 5, "•")

        tx = x + 4
        tw = w - 4
        self.set_xy(tx, top)
        self.set_font(FONT, "B", 10)
        self.set_text_color(*INK)
        self.multi_cell(tw, 5, poi.title)

        category = self.t(poi.category) if poi.category != "other" else ""
        parts = [p for p in (category, poi.duration_display, poi.address) if p]
        if parts:
            self.set_x(tx)
            self.set_font(FONT, "", 8.5)
            self.set_text_color(*MUTED)
            self.multi_cell(tw, 4.5, "  ·  ".join(parts))
        if poi.description:
            self.set_x(tx)
            self.set_font(FONT, "", 9)
            self.set_text_color(*MUTED)
            self.multi_cell(tw, 4.5, poi.description)
        self.ln(1)


