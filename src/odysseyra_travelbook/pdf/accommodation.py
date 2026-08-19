"""The accommodation summary page and its booking cards."""

from __future__ import annotations

from .base import FONT, INK, LIGHT, MUTED


class AccommodationMixin:
    def accommodations(self) -> None:
        self.add_page()
        link = getattr(self, "accommodation_link", None)
        if link is not None:
            self.set_link(link, page=self.page_no())
        self._band_header(self.t("WHERE YOU'LL STAY"), self.t("Accommodation"))
        for acc in self.itinerary.accommodations:
            self._accommodation_card(acc)

    def _booked_text(self, acc) -> str:
        bits = []
        if acc.booking_source:
            bits.append(self.t("Booked via {source}").format(source=acc.booking_source))
        return "  ·  ".join(bits)

    def _acc_date_line(self, acc) -> str:
        bits = []
        if acc.arrival and acc.departure:
            bits.append(f"{self.d(acc.arrival, 'md')} → {self.d(acc.departure, 'md')}")
        elif acc.arrival:
            bits.append(self.d(acc.arrival, "md"))
        if acc.nights is not None:
            key = "{nights} night" if acc.nights == 1 else "{nights} nights"
            bits.append(self.t(key).format(nights=acc.nights))
        if acc.type:
            bits.append(self.t(acc.type).capitalize())
        return "  ·  ".join(bits)

    def _accommodation_card(self, acc) -> None:
        pad = 5
        inner_w = self.content_width - 2 * pad
        # The Navigate link rides inline on the address line (its own line when
        # there's no address); ``addr_h`` covers both.
        where = ", ".join(p for p in (acc.name, acc.city) if p)
        addr_h = self._nav_block_h(acc.address, acc.coordinate, acc.address, where,
                                   w=inner_w, size=10, h=5)
        contact_lines = self._measure_lines(acc.contact, inner_w)
        booked = self._booked_text(acc)
        date_line = self._acc_date_line(acc)
        links = [(self.t("Website"), acc.website),
                 (self.t("Reservation"), acc.booking_link)]
        has_links = any(url for _, url in links)

        h = pad * 2 + 7
        if date_line:
            h += 5.5
        h += addr_h + contact_lines * 5
        if booked:
            h += 5
        if acc.price is not None:
            h += 5
        if acc.breakfast_included:
            h += 6
        if has_links:
            h += 5

        y = self.get_y()
        if y + h > self.h - self.b_margin:
            self.add_page()
            y = self.get_y()

        self._card_bg(y, h)

        cx = self.l_margin + pad
        yy = y + pad
        self._acc_badges(acc, yy)  # right-aligned, on the name row
        self.set_xy(cx, yy)
        self.set_font(FONT, "B", 13)
        self.set_text_color(*INK)
        self.cell(inner_w - 46, 7, acc.name)
        yy += 7

        if date_line:
            self.set_xy(cx, yy)
            self.set_font(FONT, "B", 9)
            self.set_text_color(*self.accent)
            self.cell(inner_w, 5, date_line)
            yy += 5.5

        self.set_text_color(*MUTED)
        self.set_xy(cx, yy)
        self._line_with_nav(cx, inner_w, acc.address, acc.coordinate,
                            acc.address, where, size=10, h=5, color=MUTED)
        yy += addr_h
        if acc.contact:
            self.set_xy(cx, yy)
            self.set_font(FONT, "", 10)
            self.multi_cell(inner_w, 5, acc.contact)
            yy += contact_lines * 5
        if booked:
            self.set_xy(cx, yy)
            self.set_font(FONT, "", 10)
            self.cell(inner_w, 5, booked)
            yy += 5
        if acc.price is not None:
            self._draw_price(cx, yy, inner_w, acc.price, acc.currency)
            yy += 5
        if acc.breakfast_included:
            self.set_xy(cx, yy + 1)
            self.set_font(FONT, "B", 9)
            self.set_text_color(*self.accent)
            self.cell(inner_w, 5, self.t("✓  Breakfast included"))
            yy += 6
        if has_links:
            self._link_row(cx, yy, links)

        self.set_y(y + h + 4)

    def _acc_badges(self, acc, y: float) -> None:
        """Right-aligned payment + reservation-status pills on the name row."""
        rx = self.w - self.r_margin - 5
        if acc.paid is not None:
            label = self.t("PAID") if acc.paid else self.t("TO PAY")
            rx -= self._pill_w(label)
            self._pill(label, rx, y, filled=acc.paid)
            rx -= 3
        if acc.status:
            label = self.t(acc.status.upper())
            rx -= self._pill_w(label)
            self._pill(label, rx, y, filled=(acc.status == "confirmed"))

