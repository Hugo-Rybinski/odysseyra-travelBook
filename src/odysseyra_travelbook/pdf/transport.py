"""The dedicated transport page: one card per booking, one block per leg."""

from __future__ import annotations

from ..models import format_km
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
        """A leg's full identity line — its own flight/train number plus the
        booking's reference and source, which it reads through. Used where a leg
        stands alone: a day's itinerary row and the stay bar. The transport page
        splits the two halves instead (``_leg_number`` / ``_booking_ref``), so a
        multi-leg card doesn't repeat the reference under every route."""
        bits = [p for p in (self._leg_number(t), self._booking_ref(t)) if p]
        return "  ·  ".join(bits)

    def _leg_number(self, leg) -> str:
        """The number of *this* hop — the one identity a booking can't carry."""
        if leg.type == "plane" and getattr(leg, "flight_number", ""):
            return self.t("Flight {number}").format(number=leg.flight_number)
        if leg.type == "train" and getattr(leg, "train_number", ""):
            return self.t("Train {number}").format(number=leg.train_number)
        return ""

    def _booking_ref(self, t) -> str:
        """What identifies the reservation as a whole. Reads off a booking or a
        leg alike (a leg proxies both fields to its parent)."""
        bits = []
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
        # Through `d()`, like the two-date branch above: a raw strftime here
        # printed an English weekday/month in the French book.
        return self.d(t.start_date, "wd_md")

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

    # A leg block is inset from the booking block, so the page shows at a glance
    # which lines are the reservation's and which are one hop's.
    LEG_INDENT = 7
    # Gap between the "Leg N" badge and the route beside it.
    LEG_BADGE_GAP = 3

    def _leg_label(self, index) -> str:
        """The badge on a leg of a multi-leg booking ("Leg 2"), or "" for a
        one-leg booking, where there is nothing to number."""
        return self.t("Leg {n}").format(n=index) if index else ""

    def _leg_badge_w(self, index) -> float:
        label = self._leg_label(index)
        return self._pill_w(label) + self.LEG_BADGE_GAP if label else 0

    def _leg_block_h(self, leg, inner_w: float, nav_coord, index="") -> float:
        """Height of one leg's block inside a booking card."""
        route_w = inner_w - self._leg_badge_w(index)
        h = max(self._nav_block_h(leg.title, nav_coord, leg.start, w=route_w,
                                  size=11.5, h=6, style="B"), 6) + 1
        if self._leg_info(leg):
            h += 5.5
        if self._leg_number(leg):
            h += 5
        h += self._measure_lines(leg.description, inner_w) * 5
        return h

    def _leg_info(self, leg) -> str:
        """The hop's when-and-how-far line: its date, its times, and its
        ``distance_km`` (rounded for display like every other distance in the
        book). The distance sits here rather than with the flight number
        because it is a figure of the movement, and a leg with no number would
        otherwise have nowhere to show it."""
        return "  ·  ".join(
            p for p in (self._transport_date(leg),
                        self._transport_times(leg, day_marker=False),
                        format_km(getattr(leg, "distance_km", None))) if p
        )

    def _leg_block(self, leg, cx: float, yy: float, inner_w: float,
                   index: int = 0) -> float:
        """Draw one leg — its "Leg N" badge, route (with its Navigate
        link), dates/times, its own flight/train number, its note — and return
        the y below it. Everything the reservation covers is drawn once by the
        caller, above the legs."""
        label = self._leg_label(index)
        if label:
            self._pill(label, cx, yy + 0.2, filled=False)
        route_x = cx + self._leg_badge_w(index)
        route_w = inner_w - self._leg_badge_w(index)
        nav_coord = leg.start_coordinate or leg.coordinate
        title_h = max(self._nav_block_h(leg.title, nav_coord, leg.start, w=route_w,
                                        size=11.5, h=6, style="B"), 6)
        self.set_y(yy - 0.4)
        self._line_with_nav(route_x, route_w, leg.title, nav_coord, leg.start,
                            size=11.5, h=6, style="B", color=INK)
        yy += title_h + 1

        info = self._leg_info(leg)
        if info:
            self.set_xy(cx, yy)
            self.set_font(FONT, "B", 9)
            self.set_text_color(*self.accent)
            self.cell(inner_w, 5, info)
            yy += 5.5
        number = self._leg_number(leg)
        if number:
            self.set_xy(cx, yy)
            self.set_font(FONT, "", 9.5)
            self.set_text_color(*MUTED)
            self.cell(inner_w, 5, number)
            yy += 5
        note_n = self._measure_lines(leg.description, inner_w)
        if note_n:
            self.set_xy(cx, yy)
            self._para(cx, inner_w, leg.description)
            yy += note_n * 5
        return yy

    def _transport_card(self, t) -> None:
        """One booking. Two shapes, because a booking with one leg and a booking
        with several are different things to read:

        * **several legs** — everything the reservation covers first (its name,
          type badge, status/payment pills, reference, note, price and links),
          then, under a rule, one **inset, numbered** block per leg. Shared
          information and per-hop information can't be confused.
        * **one leg** — a single flat block, no rule and no inset: there is
          nothing to tell apart, and the booking *is* that movement. Its route
          line is dropped when it would only repeat the heading (the usual case,
          since an unnamed booking is headed with its route).
        """
        if len(t.legs) == 1:
            self._flat_transport_card(t)
        else:
            self._multi_leg_transport_card(t)

    def _flat_transport_card(self, t) -> None:
        """A one-leg booking: the reservation and its single movement as one
        block (see :meth:`_transport_card`)."""
        leg = t.legs[0]
        pad = 5
        inner_w = self.content_width - 2 * pad
        type_label = self.t(t.type).upper() if t.type else self.t("TRANSPORT")
        type_w = self._pill_w(type_label)
        cx = self.l_margin + pad + 2
        title_x = cx + type_w + 4
        title_w = inner_w - type_w - 4 - 44

        nav_coord = leg.start_coordinate or leg.coordinate
        # The route only earns its own line when the heading isn't already it.
        route = leg.title if leg.title != t.title else ""
        # With no route line, the heading carries the leg's Navigate link.
        title_h = (max(self._nav_block_h(t.title, nav_coord, leg.start, w=title_w,
                                         size=12, h=6, style="B"), 6) if not route
                   else max(self._measure_lines(t.title, title_w, size=12,
                                                style="B"), 1) * 6)
        route_h = (max(self._nav_block_h(route, nav_coord, leg.start, w=inner_w,
                                         size=11.5, h=6, style="B"), 6)
                   if route else 0)
        info = self._leg_info(leg)
        identity = self._transport_booking(leg)  # this leg's number + the ref
        booking_note_n = self._measure_lines(t.description, inner_w)
        leg_note_n = self._measure_lines(leg.description, inner_w)
        links = [(self.t("Website"), t.website),
                 (self.t("Reservation"), t.booking_link)]
        has_links = not self.ink_saver and any(url for _, url in links)

        h = pad * 2 + title_h + 1 + route_h
        if info:
            h += 5.5
        if identity:
            h += 5
        h += (booking_note_n + leg_note_n) * 5
        if t.price is not None:
            h += 5
        if has_links:
            h += 5

        y = self.get_y()
        if y + h > self.h - self.b_margin:
            self.add_page()
            y = self.get_y()
        self._card_bg(y, h)

        yy = y + pad
        self._pill(type_label, cx, yy, filled=True)
        self._status_pills(t, yy, pad)

        if route:
            self.set_xy(title_x, yy - 0.4)
            self.set_font(FONT, "B", 12)
            self.set_text_color(*INK)
            self.multi_cell(title_w, 6, t.title)
        else:
            self.set_y(yy - 0.4)
            self._line_with_nav(title_x, title_w, t.title, nav_coord, leg.start,
                                size=12, h=6, style="B", color=INK)
        yy += title_h + 1

        if route:
            self.set_y(yy - 0.4)
            self._line_with_nav(cx, inner_w, route, nav_coord, leg.start,
                                size=11.5, h=6, style="B", color=INK)
            yy += route_h
        if info:
            self.set_xy(cx, yy)
            self.set_font(FONT, "B", 9)
            self.set_text_color(*self.accent)
            self.cell(inner_w, 5, info)
            yy += 5.5
        if identity:
            self.set_xy(cx, yy)
            self.set_font(FONT, "", 9.5)
            self.set_text_color(*MUTED)
            self.cell(inner_w, 5, identity)
            yy += 5
        # The reservation's note first, then this hop's — the same order the
        # multi-leg card states them in.
        for note, n in ((t.description, booking_note_n),
                        (leg.description, leg_note_n)):
            if n:
                self.set_xy(cx, yy)
                self._para(cx, inner_w, note)
                yy += n * 5
        if t.price is not None:
            self._draw_price(cx, yy, inner_w, t.price, t.currency)
            yy += 5
        if has_links:
            self._link_row(cx, yy, links)

        self.set_y(y + h + 4)

    def _status_pills(self, t, yy: float, pad: float) -> float:
        """The booking's right-aligned payment/status badges. Returns the x the
        next one would start at."""
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
        return rx

    def _multi_leg_transport_card(self, t) -> None:
        """A booking with several legs: what the reservation covers, a rule, then
        one inset numbered block per leg (see :meth:`_transport_card`)."""
        pad = 5
        inner_w = self.content_width - 2 * pad
        type_label = self.t(t.type).upper() if t.type else self.t("TRANSPORT")
        type_w = self._pill_w(type_label)
        cx = self.l_margin + pad + 2
        # The title shares its row with the type pill and the right-side badges.
        title_x = cx + type_w + 4
        title_w = inner_w - type_w - 4 - 44
        title_n = max(self._measure_lines(t.title, title_w, size=12, style="B"), 1)

        ref = self._booking_ref(t)
        note_n = self._measure_lines(t.description, inner_w)
        links = [(self.t("Website"), t.website),
                 (self.t("Reservation"), t.booking_link)]
        has_links = not self.ink_saver and any(url for _, url in links)
        legs = t.legs
        leg_w = inner_w - self.LEG_INDENT

        h = pad * 2 + title_n * 6 + 1
        if ref:
            h += 5
        if note_n:
            h += note_n * 5
        if t.price is not None:
            h += 5
        if has_links:
            h += 5
        h += 4  # the rule between the booking and its legs
        for i, leg in enumerate(legs):
            h += self._leg_block_h(leg, leg_w,
                                   leg.start_coordinate or leg.coordinate,
                                   index=i + 1)
            if i:
                h += 3  # the hairline between two legs

        y = self.get_y()
        if y + h > self.h - self.b_margin:
            self.add_page()
            y = self.get_y()

        self._card_bg(y, h)

        # --- what the reservation covers ---------------------------------
        yy = y + pad
        self._pill(type_label, cx, yy, filled=True)

        self._status_pills(t, yy, pad)

        self.set_xy(title_x, yy - 0.4)
        self.set_font(FONT, "B", 12)
        self.set_text_color(*INK)
        self.multi_cell(title_w, 6, t.title)
        yy += title_n * 6 + 1

        if ref:
            self.set_xy(cx, yy)
            self.set_font(FONT, "", 9.5)
            self.set_text_color(*MUTED)
            self.cell(inner_w, 5, ref)
            yy += 5
        if note_n:
            self.set_xy(cx, yy)
            self._para(cx, inner_w, t.description)
            yy += note_n * 5
        if t.price is not None:
            self._draw_price(cx, yy, inner_w, t.price, t.currency)
            yy += 5
        if has_links:
            self._link_row(cx, yy, links)
            yy += 5

        # --- then the legs, inset under a rule ---------------------------
        # Grey, like the hairlines between the legs — just heavier. The boundary
        # is structural, so it shouldn't compete with the accent colour, which
        # marks emphasis (badges, times, links).
        yy += 1.5
        self.set_draw_color(*LIGHT)
        self.set_line_width(0.5)
        self.line(cx, yy, self.l_margin + pad + inner_w, yy)
        yy += 2.5

        lx = cx + self.LEG_INDENT
        for i, leg in enumerate(legs):
            if i:
                self.set_draw_color(*LIGHT)
                self.set_line_width(0.2)
                self.line(lx, yy + 1, self.l_margin + pad + inner_w, yy + 1)
                yy += 3
            yy = self._leg_block(leg, lx, yy, leg_w, index=i + 1)

        self.set_y(y + h + 4)
