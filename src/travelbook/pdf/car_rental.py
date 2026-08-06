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
        start = self._cr_when(cr.booking_start_date, cr.booking_start_time,
                              cr.booking_start_tz)
        end = self._cr_when(cr.booking_end_date, cr.booking_end_time, cr.booking_end_tz)
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

    def _cr_pay_badge(self, cr, y: float) -> None:
        if cr.paid is None:
            return
        label = self.t("PAID") if cr.paid else self.t("TO PAY")
        x = self.w - self.r_margin - 5 - self._pill_w(label)
        self._pill(label, x, y, filled=cr.paid)

    def _car_rental_card(self, cr) -> None:
        pad = 5
        inner_w = self.content_width - 2 * pad
        title = self.t(cr.title) if cr.title == "Car rental" else cr.title
        type_label = self.t(cr.car_type_label)
        type_w = self._pill_w(type_label)
        pickup = self._cr_line("Pick-up", cr.pickup_date, cr.pickup_time,
                               cr.pickup_tz, cr.pickup_location,
                               cr.pickup_duration_display)
        dropoff = self._cr_line("Drop-off", cr.dropoff_date, cr.dropoff_time,
                                cr.dropoff_tz, cr.dropoff_location,
                                cr.dropoff_duration_display)
        window = self._cr_window(cr)
        meta = self._cr_meta(cr)

        pickup_n = self._measure_lines(pickup, inner_w, 9)
        dropoff_n = self._measure_lines(dropoff, inner_w, 9)
        meta_n = self._measure_lines(meta, inner_w, 10)

        h = pad * 2 + 7
        h += pickup_n * 5 + dropoff_n * 5
        if window:
            h += 5.5
        if meta:
            h += meta_n * 5
        if cr.price is not None:
            h += 5

        y = self.get_y()
        if y + h > self.h - self.b_margin:
            self.add_page()
            y = self.get_y()

        self._card_bg(y, h)

        cx = self.l_margin + pad
        yy = y + pad
        self._pill(type_label, cx, yy, filled=True)
        self._cr_pay_badge(cr, yy)
        self.set_xy(cx + type_w + 4, yy - 0.4)
        self.set_font(FONT, "B", 13)
        self.set_text_color(*INK)
        self.cell(inner_w - type_w - 4 - 32, 7, title)
        yy += 7

        self.set_text_color(*self.accent)
        if pickup:
            self.set_xy(cx, yy)
            self.set_font(FONT, "B", 9)
            self.multi_cell(inner_w, 5, pickup)
            yy += pickup_n * 5
        if dropoff:
            self.set_xy(cx, yy)
            self.set_font(FONT, "B", 9)
            self.multi_cell(inner_w, 5, dropoff)
            yy += dropoff_n * 5

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

        self.set_y(y + h + 4)
