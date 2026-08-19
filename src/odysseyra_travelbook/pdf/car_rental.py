"""Car-rental booking cards, rendered under the transport page."""

from __future__ import annotations

from .base import FONT, INK, MUTED


class CarRentalMixin:
    def _cr_when(self, d, t, tz) -> str:
        if d is None:
            return ""
        s = self.d(d, "wd_md")
        if t is not None:
            s += f" {t:%H:%M}"
            label = self._tz_label(tz)
            if label:
                s += f" {label}"
        return s

    def _cr_line(self, label: str, d, t, tz, location: str, dur: str) -> str:
        when = self._cr_when(d, t, tz)
        body = "  ·  ".join(p for p in (when, location) if p)
        if dur:
            body += f"  ({dur})"
        return f"{self.t(label)}: {body}" if body else ""

    def _cr_window(self, cr) -> str:
        start = self._cr_when(cr.booking_start.date, cr.booking_start.time,
                              cr.booking_start.tz)
        end = self._cr_when(cr.booking_end.date, cr.booking_end.time, cr.booking_end.tz)
        if start and end:
            return self.t("Booked {start} → {end}").format(start=start, end=end)
        if start:
            return self.t("Booked from {start}").format(start=start)
        return ""

    def _cr_meta(self, cr) -> str:
        bits = []
        if cr.car_model and cr.company:  # model already stands in as the title otherwise
            bits.append(cr.car_model)
        if cr.booking_number:
            bits.append(self.t("Ref {ref}").format(ref=cr.booking_number))
        if cr.additional_drivers:
            key = ("{n} additional driver" if cr.additional_drivers == 1
                   else "{n} additional drivers")
            bits.append(self.t(key).format(n=cr.additional_drivers))
        if cr.contact:
            bits.append(cr.contact)
        return "  ·  ".join(bits)

    def _cr_badges(self, cr, y: float) -> None:
        """Right-aligned payment + reservation-status pills on the title row."""
        rx = self.w - self.r_margin - 5
        if cr.paid is not None:
            label = self.t("PAID") if cr.paid else self.t("TO PAY")
            rx -= self._pill_w(label)
            self._pill(label, rx, y, filled=cr.paid)
            rx -= 3
        if cr.status:
            label = self.t(cr.status.upper())
            rx -= self._pill_w(label)
            self._pill(label, rx, y, filled=(cr.status == "confirmed"))

    def _car_rental_card(self, cr) -> None:
        pad = 5
        inner_w = self.content_width - 2 * pad
        title = self.t(cr.title) if cr.title == "Car rental" else cr.title
        type_label = self.t(cr.car_type_label)
        type_w = self._pill_w(type_label)
        pickup = self._cr_line("Pick-up", cr.pickup.date, cr.pickup.time,
                               cr.pickup.tz, cr.pickup_location,
                               cr.pickup_duration_display)
        dropoff = self._cr_line("Drop-off", cr.dropoff.date, cr.dropoff.time,
                                cr.dropoff.tz, cr.dropoff_location,
                                cr.dropoff_duration_display)
        window = self._cr_window(cr)
        meta = self._cr_meta(cr)
        links = [(self.t("Website"), cr.website),
                 (self.t("Reservation"), cr.booking_link)]
        has_links = any(url for _, url in links)

        # The pick-up / drop-off lines each carry an inline Navigate link to
        # their location; ``_nav_block_h`` covers the possible extra wrap line.
        pickup_coord = cr.pickup_coordinate or cr.coordinate
        dropoff_coord = cr.dropoff_coordinate or cr.coordinate
        pickup_h = self._nav_block_h(pickup, pickup_coord, cr.pickup_location,
                                     w=inner_w, size=9, h=5, style="B")
        dropoff_h = self._nav_block_h(dropoff, dropoff_coord, cr.dropoff_location,
                                      w=inner_w, size=9, h=5, style="B")
        meta_n = self._measure_lines(meta, inner_w, 10)

        h = pad * 2 + 7
        h += pickup_h + dropoff_h
        if window:
            h += 5.5
        if meta:
            h += meta_n * 5
        if cr.price is not None:
            h += 5
        if has_links:
            h += 5

        y = self.get_y()
        if y + h > self.h - self.b_margin:
            self.add_page()
            y = self.get_y()

        self._card_bg(y, h)

        cx = self.l_margin + pad
        yy = y + pad
        self._pill(type_label, cx, yy, filled=True)
        self._cr_badges(cr, yy)
        self.set_xy(cx + type_w + 4, yy - 0.4)
        self.set_font(FONT, "B", 13)
        self.set_text_color(*INK)
        self.cell(inner_w - type_w - 4 - 32, 7, title)
        yy += 7

        if pickup:
            self.set_xy(cx, yy)
            self._line_with_nav(cx, inner_w, pickup, pickup_coord,
                                cr.pickup_location, size=9, h=5, style="B",
                                color=self.accent)
            yy += pickup_h
        if dropoff:
            self.set_xy(cx, yy)
            self._line_with_nav(cx, inner_w, dropoff, dropoff_coord,
                                cr.dropoff_location, size=9, h=5, style="B",
                                color=self.accent)
            yy += dropoff_h

        if window:
            self.set_xy(cx, yy)
            self.set_font(FONT, "", 9.5)
            self.set_text_color(*MUTED)
            self.cell(inner_w, 5, window)
            yy += 5.5
        if meta:
            self.set_xy(cx, yy)
            self.set_font(FONT, "", 10)
            self.set_text_color(*MUTED)
            self.multi_cell(inner_w, 5, meta)
            yy += meta_n * 5
        if cr.price is not None:
            self._draw_price(cx, yy, inner_w, cr.price, cr.currency)
            yy += 5
        if has_links:
            self._link_row(cx, yy, links)

        self.set_y(y + h + 4)
