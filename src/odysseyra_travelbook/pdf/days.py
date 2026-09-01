"""Per-day pages: header band, the merged itinerary (activities + transport),
and the bottom stay bar."""

from __future__ import annotations

from datetime import time

from ..lang import fmt_weekday_runs
from ..models import Day, _format_duration, maps_url, moon_phase
from .base import FAINT, FONT, INK, LIGHT, MUTED, _tint


def road_display_legs(start, waypoints):
    """Collapse a road's waypoints into display legs. Unnamed (route-shaping)
    waypoints carry no leg of their own — they merge forward into the next named
    waypoint, their ``duration`` / ``distance_km`` summed into that leg and their
    ``off_road`` OR-ed into it. Returns
    ``[(src, dest, duration_min | None, distance_km | None, dest_wp,
    off_road)]``; ``dest`` is ``None`` for a trailing run of unnamed waypoints (an
    unnamed arrival), and ``dest_wp`` is the waypoint the leg ends at — the named
    one, or the last shaping point for an unnamed arrival — which is what carries
    that leg's coordinate, its map pin and its ``gpx``."""
    legs = []
    acc = {"prev": start, "dur": 0, "dist": 0.0, "has_dur": False,
           "has_dist": False, "pending": False, "wp": None, "off": False}

    def flush(dest):
        legs.append((acc["prev"], dest,
                     acc["dur"] if acc["has_dur"] else None,
                     acc["dist"] if acc["has_dist"] else None,
                     acc["wp"], acc["off"]))
        acc.update(prev=dest, dur=0, dist=0.0, has_dur=False,
                   has_dist=False, pending=False, wp=None, off=False)

    for wp in waypoints:
        acc["pending"] = True
        acc["wp"] = wp  # the waypoint the leg being built ends at
        if wp.duration_min is not None:
            acc["dur"] += wp.duration_min
            acc["has_dur"] = True
        if wp.distance_km is not None:
            acc["dist"] += wp.distance_km
            acc["has_dist"] = True
        if wp.off_road:
            acc["off"] = True
        if wp.location:
            flush(wp.location)
    if acc["pending"]:  # trailing unnamed waypoints → the arrival
        flush(None)
    return legs


class DayMixin:
    def day(self, index: int, day: Day) -> None:
        self.add_page()
        # point the cover's day-by-day row for this day at the top of its page
        link = getattr(self, "day_links", {}).get(index)
        if link is not None:
            self.set_link(link, page=self.page_no())
        # The band carries the city and the date; the day's sky goes in the body
        # (see `_sun_moon_line`), where the viewer puts it too.
        sun = self.itinerary.sun_for(day)
        moon = moon_phase(day.date) if self.itinerary.show_moon_phase and day.date else None
        kicker = self.t("DAY {index}").format(index=index)
        head = [b for b in (day.city, self.d(day.date, "wd_full_md")) if b]
        self._band_header(kicker, day.title, "   ".join(head))

        # A public holiday opens the day, ahead of the sky line, the intro and
        # the map: it changes what you'll find open, so it should be the first
        # thing read. The ⚠️ is U+26A0 + U+FE0F, both in DejaVu (like the sun
        # line's ☀️), so it needs no emoji fallback font and is kept out of the
        # translated key.
        if day.bank_holiday:
            self._notice(f"⚠️ {self.t('BANK HOLIDAY')}",
                         self.t("Expect closures and reduced opening hours."))

        # With both switches on, the night's phase closes the sun line — one
        # "today's sky" reading instead of two. It then leaves the stay bar,
        # rather than being printed twice on one page.
        sun_text, line_moon = self._sun_moon_line(sun, moon)
        if sun_text:
            self.set_x(self.l_margin)
            self.set_font(FONT, "B", 9.5)
            self.set_text_color(*self.accent)
            self.multi_cell(self.content_width, 5.5, sun_text)
            self.ln(1.5)

        if day.description:
            self.set_font(FONT, "", 11)
            self.set_text_color(*MUTED)
            self.multi_cell(self.content_width, 6, day.description)
            self.ln(3)

        day_maps = self.day_maps(day)
        self._day_maps = day_maps   # read by title renderers to show pin numbers
        if day_maps:
            self.day_main_map(day_maps, index)

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
                    if item.kind == "place":
                        self.day_area_map(day_maps, item.title)

        self._day_stay(day, moon=None if line_moon else moon)

    def _sun_moon_line(self, sun, moon):
        """The day's sun times, closed by the night's moon phase when both
        switches are on. Returns ``(text, moon_shown)`` — the caller then leaves
        the moon out of the stay bar, so the page never prints it twice.

        It is drawn in the day's body, above the intro, over the full content
        width — so unlike the header band (where it used to sit beside the
        kicker, sharing one row) there is nothing to degrade for: the phase is
        always named, and the longest French name fits."""
        if sun is None:
            return "", None
        sunrise, sunset = sun.hhmm
        if moon is None:
            return self.t("☀️ Sunrise: {sunrise}, Sunset: {sunset}").format(
                sunrise=sunrise, sunset=sunset), None
        return self.t(
            "☀️ Sunrise: {sunrise}, Sunset: {sunset}, {emoji} {moon}"
        ).format(sunrise=sunrise, sunset=sunset, emoji=moon.emoji,
                 moon=self.t(moon.name)), moon

    def _day_items(self, day):
        """Activities, same-day transports and car pick-up/drop-off events,
        merged and sorted by start time."""
        items = (list(day.activities)
                 + self.itinerary.transports_on(day.date)
                 + self.itinerary.car_events_on(day.date))
        items.sort(key=lambda x: (x.start_time is None, x.start_time or time(0, 0)))
        return items

    def _day_stay(self, day, moon=None) -> None:
        """A compact bar at the bottom of the day's page for that night — an
        accommodation, or an overnight transport leg if you sleep aboard one.

        ``moon`` is the night's phase when the header band didn't already show
        it beside the sun times (`day` decides, so the two never both print it)."""
        acc = self.itinerary.stay_for(day.date)
        if acc is not None:
            total, night = acc.nights, acc.night_of(day.date)
            right = (self.t("Night {night}/{total} here").format(night=night, total=total)
                     if total and total > 1 and night else "")
            sub = "  ·  ".join(p for p in (acc.address, self._booked_text(acc)) if p)
            where = ", ".join(p for p in (acc.name, acc.city) if p)
            links = [(self.t("Website"), acc.website),
                     (self.t("Reservation"), acc.booking_link)]
            self._bottom_bar(acc.name, sub, right, pin=self.pin_label(acc),
                             links=links, moon=moon, note=acc.description,
                             nav=maps_url(acc.coordinate, acc.address, where,
                                          provider=self.map_provider),
                             addr_url=self._addr_url(acc.coordinate, acc.address))
            return
        leg = self.itinerary.night_transport(day.date)
        if leg is not None:
            times = self._transport_times(leg)
            sub = "  ·  ".join(p for p in (leg.title, times) if p)
            links = [(self.t("Website"), leg.website),
                     (self.t("Reservation"), leg.booking_link)]
            # The leg is normally also a row in the day's itinerary above (both
            # `night_transport` and `transports_on` select on the departure
            # date), and that row already prints its note — so the bar doesn't
            # repeat it. Checked rather than assumed, so the note still shows if
            # the two ever stop coinciding.
            note = "" if leg in self._day_items(day) else leg.description
            self._bottom_bar(self._overnight_name(leg), sub, self.t("on board"),
                             links=links, moon=moon, note=note)

    _BAR_NOTE_LINES = 2  # the bar is a glance, not a page

    def _bar_note(self, note: str, w: float) -> list[str]:
        """The stay's ``description`` wrapped for the bottom bar, capped at
        ``_BAR_NOTE_LINES`` lines with an ellipsis when it runs longer — the bar
        is pinned near the page foot, so it can't grow without bound. The full
        text is always on the accommodation page."""
        if not note:
            return []
        self.set_font(FONT, "", 8.5)
        lines = list(self.multi_cell(w, 4, note, dry_run=True, output="LINES"))
        if len(lines) > self._BAR_NOTE_LINES:
            lines = lines[:self._BAR_NOTE_LINES]
            lines[-1] = lines[-1].rstrip() + " …"
        return lines

    def _bottom_bar(self, name: str, sub: str, right: str = "", pin=None,
                    links=None, nav: str = "", addr_url: str = "", moon=None,
                    note: str = "") -> None:
        # bar_h leaves ~3 mm below the sub line to match the padding above the
        # kicker (the sub cell ends at offset pad+9+4 = 17; 17 + 3 = 20). A row
        # of clickable links, when present, sits below the sub line and grows
        # the bar by 6 mm; the note (when there is one) grows it by its own
        # wrapped height, between the two.
        if self.ink_saver:  # ink-saver drops every hyperlink
            links, nav, addr_url = None, "", ""
        links = [(label, url) for label, url in (links or []) if url]
        pad = 4
        note_lines = self._bar_note(note, self.content_width - 2 * pad - 2)
        bar_h = (26 if links else 20) + len(note_lines) * 4
        # The bar must sit whole on one page: if the day's content already
        # runs to the bottom, start a fresh page so the bar's name/sub cells
        # don't auto-break away onto stray pages of their own.
        self._ensure_room(bar_h + 6)
        # Pin to the lower part of the page, but never over the day's content.
        y = max(self.get_y() + 6, self.h - 24 - bar_h)
        cx = self.l_margin + pad + 2

        self._card_bg(y, bar_h)

        self.set_xy(cx, y + pad - 1)
        self.set_font(FONT, "B", 7)
        self.set_text_color(*self.accent)
        kicker = self.t("TONIGHT'S STAY")
        self.cell(self.get_string_width(kicker) + 1, 4, kicker)
        if moon is not None:
            # Moon phase inline after the kicker: the emoji (fallback font) a
            # touch larger than the muted phase name beside it.
            self.set_font(FONT, "", 9)
            self.set_text_color(*MUTED)
            self.cell(self.get_string_width("  " + moon.emoji) + 1, 4, "  " + moon.emoji)
            self.set_font(FONT, "", 7)
            self.cell(0, 4, " " + self.t(moon.name))
        if right:
            self.set_xy(self.l_margin, y + pad - 1)
            self.set_font(FONT, "B", 8)
            self.set_text_color(*self.accent)
            self.cell(self.content_width - pad, 4, right, align="R")

        nx = cx
        if pin:
            nx = cx + self._pin_disc(cx, y + pad + 3.2, pin)
        self.set_xy(nx, y + pad + 3.5)
        self.set_font(FONT, "B", 11)
        self.set_text_color(*INK)
        self.cell(0, 5, name)

        # The Navigate link sits inline right after the sub (address) line; it
        # reserves its own width so the sub is truncated to leave room for it.
        nav_label = "  " + self.t("(Navigate)") if nav else ""
        self.set_font(FONT, "", 8.5)
        nav_w = self.get_string_width(nav_label)
        maxw = self.content_width - 2 * pad - 2
        while sub and "  ·  " in sub and self.get_string_width(sub) + nav_w > maxw:
            sub = sub.rsplit("  ·  ", 1)[0]
        self.set_xy(cx, y + pad + 9)
        self.set_text_color(*MUTED)
        sub_w = self.get_string_width(sub)
        self.cell(sub_w, 4, sub, link=addr_url)
        if nav:
            self.set_text_color(*self.accent)
            self.cell(nav_w, 4, nav_label, link=nav)

        ny = y + pad + 13.5
        for line in note_lines:
            self.set_xy(cx, ny)
            self.set_font(FONT, "", 8.5)
            self.set_text_color(*MUTED)
            self.cell(0, 4, line)
            ny += 4

        if links:
            self._link_row(cx, y + pad + 14 + len(note_lines) * 4, links)

        self.set_y(y + bar_h)

    GUTTER = 28  # left column reserved for the type badge

    def _ensure_room(self, min_h: float) -> None:
        """Start a fresh page unless at least ``min_h`` mm remain on this one.

        Each row lays out its badge / time / pin-disc at absolute coordinates
        captured in ``top`` before any auto page-break. If a row starts too
        close to the bottom, fpdf2 breaks partway through and those fixed
        pieces scatter one-per-page — this keeps a row's header block together
        by breaking cleanly first."""
        if self.get_y() + min_h > self.page_break_trigger:
            self.add_page()

    def _activity(self, act) -> None:
        self._ensure_room(24)
        top = self.get_y()
        start_page = self.page_no()
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

        num = self.pin_label(act)
        if not self._road_title(act, x, detail_w, top, num):
            tx, tw = x, detail_w
            if num:
                wd = self._pin_disc(x, top + 0.6, num)
                tx, tw = x + wd, detail_w - wd
            self.set_xy(tx, top)
            self.set_font(FONT, "B", 11)
            self.set_text_color(*INK)
            self.multi_cell(tw, 6, act.title)

        # Type-specific details.
        getattr(self, f"_details_{act.kind}")(act, x, detail_w)

        # Keep the row at least as tall as the gutter time block — but only if
        # the row stayed on one page; if its content overflowed, ``top`` is a
        # coordinate on the previous page and the floor would jump the cursor
        # far down the new page (stranding whatever follows).
        if self.page_no() == start_page:
            self.set_y(max(self.get_y(), top + 15))
        y = self.get_y()
        self.set_draw_color(*LIGHT)
        self.set_line_width(0.2)
        self.line(x, y, self.w - self.r_margin, y)
        self.ln(2)

    def _buffer(self, buf) -> None:
        self._ensure_room(10)
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
        self._ensure_room(16)
        top = self.get_y()
        x = self.l_margin + self.GUTTER
        gw = self.GUTTER - 5
        if meal.start_time is not None:
            self.set_xy(self.l_margin, top)
            self.set_font(FONT, "B", 8)
            self.set_text_color(*self.accent)
            self.cell(gw, 5, f"{meal.start_time:%H:%M}", align="C")

        label = self.t(meal.category).capitalize()
        if meal.restaurant:
            head = self.t("{meal} at {restaurant}").format(
                meal=label, restaurant=meal.restaurant)
        elif meal.area:
            head = self.t("{meal} near {area}").format(meal=label, area=meal.area)
        else:
            head = label
        num = self.pin_label(meal)
        tx = x
        if num:
            tx = x + self._pin_disc(x, top + 0.4, num)
        self.set_xy(tx, top)
        self.set_font(FONT, "B", 9.5)
        self.set_text_color(*self.accent)
        self.cell(0, 5, head, new_x="LMARGIN", new_y="NEXT")

        meta = "  ·  ".join(p for p in (meal.duration_display, meal.address) if p)
        w = self.content_width - self.GUTTER
        self.set_xy(x, self.get_y())
        self._line_with_nav(x, w, meta, meal.coordinate, meal.address,
                            meal.restaurant, meal.area, size=8.5, h=4.5,
                            text_url=self._addr_url(meal.coordinate, meal.address))
        self.ln(1.5)

    def _transport_row(self, t) -> None:
        """A transport leg shown inline in a day's itinerary."""
        self._ensure_room(24)
        top = self.get_y()
        start_page = self.page_no()
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

        self.set_y(top)
        self._line_with_nav(x, detail_w, t.title, t.start_coordinate or t.coordinate,
                            t.start, size=11, h=6, style="B", color=INK)

        meta = "  ·  ".join(
            p for p in (t.duration_display, self._transport_booking(t)) if p
        )
        if meta:
            self.set_x(x)
            self.set_font(FONT, "", 9)
            self.set_text_color(*MUTED)
            self.multi_cell(detail_w, 5, meta)
        if t.description:
            self._para(x, detail_w, t.description)
        if t.overnight:
            self._chip(x, self.t("OVERNIGHT"))

        if self.page_no() == start_page:
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
        self._ensure_room(24)
        top = self.get_y()
        start_page = self.page_no()
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
        coord = (cr.pickup_coordinate if ev.kind == "car_pickup"
                 else cr.dropoff_coordinate) or cr.coordinate
        if meta or maps_url(coord, ev.location, provider=self.map_provider):
            self.set_xy(x, self.get_y())
            self._line_with_nav(x, detail_w, meta, coord, ev.location)
        if cr.description:
            self._para(x, detail_w, cr.description)

        if self.page_no() == start_page:
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
        if act.kind == "meal":
            return self.t("MEAL")
        return self.t("ROAD") if act.kind == "road" else self.t("HIKE")

    def _road_title(self, act, x: float, w: float, top: float, dep_pin) -> bool:
        """A drive's title with a disc beside **each** end it pins —
        ``(1) Amboise → (4) Sarlat-la-Canéda``.

        Every other activity is one place, so one disc leads its title; a drive
        is two, and the arrival's number has to sit next to the arrival or it
        reads as a second label on the departure. Returns ``False`` — leaving the
        plain single-disc ``multi_cell`` to the caller — for anything that isn't
        a drive with a pinned, named arrival, and for a route too long to fit
        one line (a disc can't be drawn mid-wrap). The viewer's `ActivityTitle`
        is the same rule; keep the two in step."""
        if getattr(act, "kind", "") != "road":
            return False
        legs = road_display_legs(act.start, act.waypoints)
        arr_wp = legs[-1][4] if legs else None
        # Only named waypoints are ever pinned, so an unnamed arrival (a
        # trailing run of shaping points) falls through here on its own.
        arr_pin = self.pin_label(arr_wp) if arr_wp is not None else None
        dest = legs[-1][1] if legs else ""
        if not arr_pin or not act.start or not dest:
            return False
        ends = ((dep_pin, act.start), (arr_pin, dest))
        opts = dict(sep="  →  ", size=11, style="B")
        if self._route_width(ends, **opts) > w:
            return False
        self._route_with_pins(x, top, ends, h=6, color=INK, **opts)
        # match the `multi_cell` this stands in for: one line consumed, cursor
        # back at the left margin (`_meta_line` and friends re-set x, not y).
        self.set_xy(self.l_margin, top + 6)
        return True

    def _details_road(self, act, x: float, w: float) -> None:
        parts = [act.duration_display]
        if act.distance_km is not None:
            parts.append(f"{act.distance_km:g} km")
        meta = "  ·  ".join(p for p in parts if p)
        legs = road_display_legs(act.start, act.waypoints)
        multi = len(legs) > 1
        if multi:
            # multi-leg drives get a Navigate link per leg (in the VIA list).
            self._meta_line(x, w, parts)
        else:
            dest_wp = legs[0][4] if legs else None
            dest_coord = dest_wp.coordinate if dest_wp is not None else None
            self._line_with_nav(x, w, meta, dest_coord, act.destination)
        # The road-level chip covers the whole drive. A single-leg drive has no
        # VIA list to hang a per-leg flag on, so its leg's flag shows here too —
        # otherwise the only off-road marking on that road would be invisible.
        if act.off_road or (not multi and legs and legs[0][5]):
            self._chip(x, self.t("OFF-ROAD SECTIONS"))
        self._para_with_pill(x, w, act.description, act.guidebook_pages)
        self._road_waypoints(x, w, act)
        self._render_nested(x, w, act.activities)

    def _road_waypoints(self, x: float, w: float, road) -> None:
        """The drive's legs, listed under a small 'VIA' header in a lower
        (lightened) accent — each row reads 'previous → this waypoint', with each
        end's map pin beside the name it labels, that leg's duration / distance
        in muted text, and a Navigate link to the leg's destination.

        A junction is one place written twice — it ends one leg and starts the
        next — so its disc appears on both rows: read down the list, the numbers
        chain ``(1)→(2)``, ``(2)→(3)``, ``(3)→(4)`` and every one of them sits
        against its own town. The first row's departure pin comes from the road
        itself, which is where the day map's numbering puts it.

        Hidden for a road with a single leg (a plain departure→arrival): the
        drive *is* that hop, so the title already carries every part of the row
        — the route, the duration, the distance, the Navigate link, and (since
        `_road_title` draws its discs mid-line) the arrival's map pin beside the
        name it labels. A pinned arrival used to earn a row here, back when the
        title bunched its discs at the front and the number sat against the
        wrong town; the mid-line discs retired that reason."""
        legs = road_display_legs(road.start, road.waypoints)
        if len(legs) <= 1:
            return
        pins = [self.pin_label(wp) if wp is not None else None
                for _s, _d, _dur, _dist, wp, _off in legs]
        # A leg's departure is the previous leg's arrival; the first one's is the
        # road's own pin (the label `pin_label(road)` carries).
        src_pins = [self.pin_label(road), *pins[:-1]]
        low_accent = _tint(self.accent, 0.4)
        self.ln(1)
        self.set_x(x)
        self.set_font(FONT, "B", 8)
        self.set_text_color(*low_accent)
        self.cell(0, 5, self.t("VIA"), new_x="LMARGIN", new_y="NEXT")
        for (src, dest, dur_min, dist_km, dest_wp, off_road), pin, src_pin in zip(
                legs, pins, src_pins):
            self._ensure_room(6)
            row_y = self.get_y()
            ends = ((src_pin, src or "?"), (pin, dest or self.t("arrival")))
            tx = self._route_with_pins(x + 3, row_y, ends, sep="  →  ", h=5,
                                       size=9, style="", color=low_accent,
                                       lead="•  ")
            self.set_xy(tx, row_y)  # the discs moved the cursor; put it back
            meta = []
            if dur_min is not None:
                meta.append(_format_duration(dur_min))
            if dist_km is not None:
                meta.append(f"{dist_km:g} km")
            if meta:
                self.set_font(FONT, "", 8.5)
                self.set_text_color(*FAINT)
                mtext = "   " + "  ·  ".join(meta)
                self.cell(self.get_string_width(mtext) + 1, 5, mtext)
            if off_road:
                # a small pill on this leg's row — the road-level chip stays for
                # a drive that is off-road as a whole
                self.cell(2, 5, "")
                self._inline_chip(self.t("OFF-ROAD"))
            dest_coord = dest_wp.coordinate if dest_wp is not None else None
            url = "" if self.ink_saver else maps_url(dest_coord, dest or "",
                                                     provider=self.map_provider)
            if url:
                label2 = self.t("(Navigate)")
                self.set_font(FONT, "", 8.5)
                self.set_text_color(*self.accent)
                self.cell(self.get_string_width("  " + label2), 5,
                          "  " + label2, link=url)
            self.ln(5)

    def _opening_line(self, act, x: float, w: float, size: float = 9,
                      h: float = 5) -> None:
        """A point of interest's opening days and hours as one row led by a bold
        accent label — ``Open   Tue–Sun  ·  09:30–12:30, 14:00–18:00``. Draws
        nothing when the visit states neither (the common case).

        Either half may be missing: no days means every day, no hours means all
        day, so only what is known is printed. The viewer's `.act-opening` line
        is the same row from the same fields — keep the two in step. Neither
        renderer flags a visit that falls *outside* the hours; that is the
        validator's warning, since the fix belongs in the JSON."""
        opening = getattr(act, "opening", None)
        if opening is None:
            return
        parts = []
        if opening.day_runs:
            parts.append(fmt_weekday_runs(opening.day_runs, self.lang))
        if opening.hours:
            parts.append(opening.hours_display)
        label = self.t("Open") + "  "
        self.set_x(x)
        self.set_font(FONT, "B", size)
        self.set_text_color(*self.accent)
        lw = self.get_string_width(label)
        self.cell(lw, h, label)
        # multi_cell takes the cursor x as its left edge, so a wrapped second
        # line hangs under the text rather than under the label.
        self.set_font(FONT, "", size)
        self.set_text_color(*MUTED)
        self.multi_cell(w - lw, h, "  ·  ".join(parts))

    def _details_point_of_interest(self, act, x: float, w: float) -> None:
        parts = [act.duration_display]
        if act.address:
            parts.append(act.address)
        meta = "  ·  ".join(p for p in parts if p)
        self._line_with_nav(x, w, meta, act.coordinate, act.address, act.name,
                            text_url=self._addr_url(act.coordinate, act.address))
        self._opening_line(act, x, w)
        self._para_with_pill(x, w, act.description, act.guidebook_pages)
        if act.website and not self.ink_saver:
            y = self.get_y()
            self._link_row(x, y, [(self.t("Website"), act.website)])
            self.set_y(y + 5)
        self._render_nested(x, w, act.activities)

    def _details_place(self, act, x: float, w: float) -> None:
        self._line_with_nav(x, w, act.duration_display, act.coordinate, act.name)
        self._para_with_pill(x, w, act.description, act.guidebook_pages)
        self._render_nested(x, w, act.activities)

    def _render_nested(self, x: float, w: float, activities) -> None:
        """The nested activities grouped under a container, drawn as an indented
        list under a small header — each row led by a compact type badge."""
        if not activities:
            return
        self._ensure_room(20)  # keep the "INCLUDES" header with its first item
        self.ln(1)
        self.set_x(x)
        self.set_font(FONT, "B", 8)
        self.set_text_color(*self.accent)
        self.cell(0, 5, self.t("INCLUDES"), new_x="LMARGIN", new_y="NEXT")
        # A single badge width across the group so every title lines up.
        badge_w = max(self._nested_badge_width(self._badge_label(s)) for s in activities)
        for sub in activities:
            if sub.kind == "hike":
                self._nested_hike(x + 5, w - 5, sub, badge_w)
            elif sub.kind == "meal":
                self._nested_meal(x + 5, w - 5, sub, badge_w)
            else:
                self._nested_poi(x + 5, w - 5, sub, badge_w)

    def _details_hike(self, act, x: float, w: float) -> None:
        parts = [act.duration_display]
        if act.distance_km is not None:
            parts.append(f"{act.distance_km:g} km")
        if act.elevation_m is not None:
            parts.append(f"+{act.elevation_m:g} m")
        parts.append(self.t(act.route_label))
        meta = "  ·  ".join(p for p in parts if p)
        self._line_with_nav(x, w, meta, act.coordinate, act.start, act.name)
        if act.name and act.start and act.end:
            self._para(x, w, f"{act.start} → {act.end}")
        self._para_with_pill(x, w, act.description, act.guidebook_pages)
        self.hike_track(act, x, w)  # no-op without an embedded `gpx`
        self._render_nested(x, w, act.activities)

    def _nested_badge_width(self, label: str) -> float:
        """The natural width of a nested type badge for ``label``."""
        self.set_font(FONT, "B", 6)
        return self.get_string_width(label) + 3

    def _nested_badge(self, x: float, y: float, label: str, w: float) -> None:
        """A compact type badge drawn inline before a nested item's title — a
        smaller sibling of the gutter :meth:`_badge`, drawn at the fixed width
        ``w`` so sibling badges align."""
        bh = 4.4
        if self.ink_saver:
            self.set_draw_color(*self.accent)
            self.set_line_width(0.3)
            self.rect(x, y, w, bh, style="D")
            text_col = self.accent
        else:
            self.set_fill_color(*self.accent)
            self.rect(x, y, w, bh, style="F")
            text_col = (255, 255, 255)
        self.set_xy(x, y + 0.5)
        self.set_font(FONT, "B", 6)
        self.set_text_color(*text_col)
        self.cell(w, 3.4, label, align="C")

    def _nested_poi(self, x: float, w: float, poi, badge_w: float) -> None:
        self._ensure_room(14)
        top = self.get_y()
        self._nested_badge(x, top + 0.4, self._badge_label(poi), badge_w)
        tx = x + badge_w + 2
        tw = w - badge_w - 2
        num = self.pin_label(poi)
        if num:
            wd = self._pin_disc(tx, top + 0.2, num)
            tx += wd
            tw -= wd
        self.set_xy(tx, top)
        self.set_font(FONT, "B", 10)
        self.set_text_color(*INK)
        self.multi_cell(tw, 5, poi.title)

        meta = "  ·  ".join(p for p in (poi.duration_display, poi.address) if p)
        if meta or maps_url(poi.coordinate, poi.address, poi.name,
                            provider=self.map_provider):
            self._line_with_nav(tx, tw, meta, poi.coordinate, poi.address,
                                poi.name, size=8.5, h=4.5,
                                text_url=self._addr_url(poi.coordinate, poi.address))
        self._opening_line(poi, tx, tw, size=8.5, h=4.5)
        self._para_with_pill(tx, tw, poi.description, poi.guidebook_pages,
                             size=9, h=4.5)
        if poi.website and not self.ink_saver:
            y = self.get_y()
            self._link_row(tx, y, [(self.t("Website"), poi.website)], size=8.5)
            self.set_y(y + 4.5)
        self.ln(1)

    def _nested_hike(self, x: float, w: float, hike, badge_w: float) -> None:
        self._ensure_room(14)
        top = self.get_y()
        self._nested_badge(x, top + 0.4, self._badge_label(hike), badge_w)
        tx = x + badge_w + 2
        tw = w - badge_w - 2
        num = self.pin_label(hike)
        if num:
            wd = self._pin_disc(tx, top + 0.2, num)
            tx += wd
            tw -= wd
        self.set_xy(tx, top)
        self.set_font(FONT, "B", 10)
        self.set_text_color(*INK)
        self.multi_cell(tw, 5, hike.title)

        # The "HIKE" badge marks the type; then distance / elevation / route.
        parts = []
        if hike.distance_km is not None:
            parts.append(f"{hike.distance_km:g} km")
        if hike.elevation_m is not None:
            parts.append(f"+{hike.elevation_m:g} m")
        parts.append(self.t(hike.route_label))
        if hike.duration_display:
            parts.append(hike.duration_display)
        meta = "  ·  ".join(p for p in parts if p)
        self._line_with_nav(tx, tw, meta, hike.coordinate, hike.start, hike.name,
                            size=8.5, h=4.5)
        if hike.name and hike.start and hike.end:
            self.set_x(tx)
            self.set_font(FONT, "", 9)
            self.set_text_color(*MUTED)
            self.multi_cell(tw, 4.5, f"{hike.start} → {hike.end}")
        self._para_with_pill(tx, tw, hike.description, hike.guidebook_pages,
                             size=9, h=4.5)
        self.hike_track(hike, tx, tw)  # no-op without an embedded `gpx`
        self.ln(1)

    def _nested_meal(self, x: float, w: float, meal, badge_w: float) -> None:
        self._ensure_room(14)
        top = self.get_y()
        self._nested_badge(x, top + 0.4, self._badge_label(meal), badge_w)
        tx = x + badge_w + 2
        tw = w - badge_w - 2
        label = self.t(meal.category).capitalize()
        if meal.restaurant:
            head = self.t("{meal} at {restaurant}").format(
                meal=label, restaurant=meal.restaurant)
        elif meal.area:
            head = self.t("{meal} near {area}").format(meal=label, area=meal.area)
        else:
            head = label
        num = self.pin_label(meal)
        if num:
            wd = self._pin_disc(tx, top + 0.2, num)
            tx += wd
            tw -= wd
        # Accent-colored, bold head — echoing the non-nested meal row (see
        # ``_meal``) rather than the INK title used for nested POIs / hikes.
        self.set_xy(tx, top)
        self.set_font(FONT, "B", 9.5)
        self.set_text_color(*self.accent)
        self.multi_cell(tw, 5, head)

        parts = [p for p in (meal.duration_display, meal.address) if p]
        meta = "  ·  ".join(parts)
        if meta or maps_url(meal.coordinate, meal.address, meal.restaurant,
                            meal.area, provider=self.map_provider):
            self._line_with_nav(tx, tw, meta, meal.coordinate, meal.address,
                                meal.restaurant, meal.area, size=8.5, h=4.5,
                                text_url=self._addr_url(meal.coordinate, meal.address))
        self.ln(1)


