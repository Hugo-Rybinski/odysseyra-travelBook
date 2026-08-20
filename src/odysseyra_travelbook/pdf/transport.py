"""The dedicated transport page and its leg cards."""

from __future__ import annotations

from .base import FONT, INK, LIGHT, MUTED


class TransportMixin:
    def transports(self) -> None:
        self.add_page()
        link = getattr(self, "transport_link", None)
        if link is not None:
            self.set_link(link, page=self.page_no())
        self._band_header(self.t("GETTING AROUND"), self.t("Transport"))
        for t in self.itinerary.transports:
            self._transport_card(t)
        if self.itinerary.car_rentals:
            if self.itinerary.transports:
                self.ln(4)
            if self.get_y() > self.h - self.b_margin - 34:
                self.add_page()
            self._section_title(self.t("Car rentals"))
            for cr in self.itinerary.car_rentals:
                self._car_rental_card(cr)

    def _transport_booking(self, t) -> str:
        bits = []
        if t.type == "plane" and t.flight_number:
            bits.append(self.t("Flight {number}").format(number=t.flight_number))
        elif t.type == "train" and t.train_number:
            bits.append(self.t("Train {number}").format(number=t.train_number))
        if t.booking_number:
            bits.append(self.t("Ref {ref}").format(ref=t.booking_number))
        if t.booking_source:
            bits.append(self.t("Booked via {source}").format(source=t.booking_source))
        return "  ·  ".join(bits)

    def _transport_date(self, t) -> str:
        if t.start_date is None:
            return ""
        if t.end_date and t.end_date != t.start_date:
            return f"{self.d(t.start_date, 'wd_md')} → {self.d(t.end_date, 'md')}"
        return f"{t.start_date:%a %b %d}"

    def _transport_times(self, t, day_marker: bool = True) -> str:
        if t.start_time is None and t.end_time is None:
            return t.duration_display
        off = t.end_day_offset if day_marker else 0

        def fmt(tm, tz, day_off=0):
            s = f"{tm:%H:%M}"
            label = self._tz_label(tz)
            if label:
                s += f" {label}"
            if day_off:
                s += f" +{day_off}"
            return s

        if t.start_time and t.end_time:
            line = f"{fmt(t.start_time, t.start_tz)} → {fmt(t.end_time, t.end_tz, off)}"
        elif t.start_time:
            line = fmt(t.start_time, t.start_tz)
        else:
            line = fmt(t.end_time, t.end_tz, off)
        if t.duration_display:
            line += f"  ·  {t.duration_display}"
        return line

    def _transport_card(self, t) -> None:
        pad = 5
        inner_w = self.content_width - 2 * pad
        type_label = self.t(t.type).upper() if t.type else self.t("TRANSPORT")
        type_w = self._pill_w(type_label)
        route_w = inner_w - type_w - 4 - 44  # leave room for right-side badges
        # The route title carries an inline Navigate link to the departure.
        nav_coord = t.start_coordinate or t.coordinate
        title_h = max(self._nav_block_h(t.title, nav_coord, t.start, w=route_w,
                                        size=12, h=6, style="B"), 6)
        info = "  ·  ".join(
            p for p in (self._transport_date(t), self._transport_times(t, day_marker=False)) if p
        )
        booking = self._transport_booking(t)
        links = [(self.t("Website"), t.website),
                 (self.t("Reservation"), t.booking_link)]
        has_links = not self.ink_saver and any(url for _, url in links)

        h = pad * 2 + title_h
        if info:
            h += 5.5
        if booking:
            h += 5
        if t.price is not None:
            h += 5
        if has_links:
            h += 5

        y = self.get_y()
        if y + h > self.h - self.b_margin:
            self.add_page()
            y = self.get_y()

        self._card_bg(y, h)

        cx = self.l_margin + pad + 2
        yy = y + pad
        self._pill(type_label, cx, yy, filled=True)

        # Right-aligned status / payment badges.
        rx = self.w - self.r_margin - pad
        if t.paid is not None:
            label = self.t("PAID") if t.paid else self.t("TO PAY")
            rx -= self._pill_w(label)
            self._pill(label, rx, yy, filled=t.paid)
            rx -= 3
        if t.status:
            label = self.t(t.status.upper())
            rx -= self._pill_w(label)
            self._pill(label, rx, yy, filled=(t.status == "confirmed"))

        self.set_y(yy - 0.4)
        self._line_with_nav(cx + type_w + 4, route_w, t.title, nav_coord, t.start,
                            size=12, h=6, style="B", color=INK)
        yy += title_h + 1

        if info:
            self.set_xy(cx, yy)
            self.set_font(FONT, "B", 9)
            self.set_text_color(*self.accent)
            self.cell(inner_w, 5, info)
            yy += 5.5
        if booking:
            self.set_xy(cx, yy)
            self.set_font(FONT, "", 9.5)
            self.set_text_color(*MUTED)
            self.cell(inner_w, 5, booking)
            yy += 5
        if t.price is not None:
            self._draw_price(cx, yy, inner_w, t.price, t.currency)
            yy += 5
        if has_links:
            self._link_row(cx, yy, links)

        self.set_y(y + h + 4)
