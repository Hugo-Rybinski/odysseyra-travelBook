"""The emergency-contacts page — the last page of the book.

Deliberately the plainest page in the document: a directory, not a card deck.
Every other section renders bookings, which have a dozen fields each and earn
their card backgrounds; a contact is a name and a number, and someone reading
this page is in a hurry, so the numbers are set large, accent-colored and
right-aligned in a single column you can run a finger down.

Kept in step with the viewer's ``web/src/render/EmergencyContacts.tsx``, which
draws the same list in the 🗺️ Overview tab — with one deliberate addition paper
can't have: there, a contact that looks dialable is a tap-to-call link.
"""

from __future__ import annotations

from .base import FONT, INK, LIGHT


class MiscMixin:
    # A row's text height, and the padding above/below it.
    _ROW_LINE_H = 6.0
    _ROW_PAD = 3.0
    # Space between a contact's name and its number, and the widest share of the
    # page the number may claim before it drops to a line of its own.
    _CONTACT_GAP = 8.0
    _CONTACT_MAX_SHARE = 0.45

    def emergency_contacts(self) -> None:
        self.add_page()
        link = getattr(self, "emergency_link", None)
        if link is not None:
            self.set_link(link, page=self.page_no())
        self._band_header(self.t("IN CASE OF EMERGENCY"),
                          self.t("Emergency contacts"))
        contacts = self.itinerary.emergency_contacts
        for i, contact in enumerate(contacts):
            self._emergency_row(contact, last=(i == len(contacts) - 1))

    def _contact_width(self, contact: str) -> float:
        self.set_font(FONT, "B", 12)
        return self.get_string_width(contact)

    def _emergency_row(self, contact, last: bool = False) -> None:
        """One contact: its name on the left, the number on the right in accent.

        Three shapes, because both halves are optional and either may be long:

        * both, and the number fits — name left, number right-aligned, so the
          numbers form a column however long the names beside them run;
        * both, and the number is too wide to share the line (an address, an
          international number with an extension) — it takes a line of its own
          underneath rather than squeezing the name into a two-word column;
        * one half only — it simply takes the whole row, left-aligned. A lone
          number right-aligned against nothing reads as a layout bug.
        """
        cw = self.content_width
        contact_w = self._contact_width(contact.contact) if contact.contact else 0
        # No name to sit beside: the number owns the row and starts at the margin.
        alone = not contact.name or not contact.contact
        stacked = not alone and contact_w > cw * self._CONTACT_MAX_SHARE
        name_w = cw if (stacked or alone) else cw - contact_w - self._CONTACT_GAP

        name_lines = self._measure_lines(contact.name, name_w, 11, "B")
        contact_lines = (self._measure_lines(contact.contact, cw, 12, "B")
                         if (stacked or (alone and contact.contact)) else 0)
        rows = max(1, name_lines + contact_lines)
        h = rows * self._ROW_LINE_H + 2 * self._ROW_PAD

        y = self.get_y()
        if y + h > self.h - self.b_margin:
            self.add_page()
            y = self.get_y()

        if contact.name:
            self.set_xy(self.l_margin, y + self._ROW_PAD)
            self.set_font(FONT, "B", 11)
            self.set_text_color(*INK)
            self.multi_cell(name_w, self._ROW_LINE_H, contact.name)

        if contact.contact:
            self.set_font(FONT, "B", 12)
            self.set_text_color(*self.accent)
            if contact_lines:
                self.set_xy(self.l_margin,
                            y + self._ROW_PAD + name_lines * self._ROW_LINE_H)
                self.multi_cell(cw, self._ROW_LINE_H, contact.contact)
            else:
                self.set_xy(self.l_margin + name_w + self._CONTACT_GAP,
                            y + self._ROW_PAD)
                self.cell(contact_w, self._ROW_LINE_H, contact.contact, align="R")

        # A hairline between rows — never accent (that is for emphasis, and the
        # numbers already have it), and never after the last one.
        bottom = y + h
        if not last:
            self.set_draw_color(*LIGHT)
            self.set_line_width(0.3)
            self.line(self.l_margin, bottom, self.w - self.r_margin, bottom)

        self.set_xy(self.l_margin, bottom)
        self.set_text_color(*INK)
