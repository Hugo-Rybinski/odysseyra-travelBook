"""Shared PDF scaffolding: fonts, colors, and the low-level drawing helpers
(:class:`_PDFBase`) that every section mixin builds on."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from ..lang import DEFAULT_LANGUAGE, fmt_date, tr
from ..models import Itinerary, _format_tz, format_money, maps_url

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
FONT = "DejaVu"  # bundled Unicode font: handles accents, CJK-latin, arrows, …

INK = (33, 37, 41)
MUTED = (108, 117, 125)
FAINT = (152, 160, 168)  # lighter than MUTED — for de-emphasized secondary text
LIGHT = (233, 236, 239)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (31, 78, 95)


def _tint(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Blend ``rgb`` toward white by ``amount`` in [0, 1]."""
    return tuple(round(c + (255 - c) * amount) for c in rgb)  # type: ignore[return-value]


class _PDFBase(FPDF):
    def __init__(self, itinerary: Itinerary, lang: str = DEFAULT_LANGUAGE,
                 ink_saver: bool = False):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.add_font(FONT, "", FONT_DIR / "DejaVuSans.ttf")
        self.add_font(FONT, "B", FONT_DIR / "DejaVuSans-Bold.ttf")
        self.add_font(FONT, "I", FONT_DIR / "DejaVuSans-Oblique.ttf")
        self.itinerary = itinerary
        self.lang = lang
        # Ink-saving mode: skip large solid accent fills (cover banner, page
        # header bands, card backgrounds) and draw outlines / thin rules
        # instead, keeping the accent color only for text and hairlines.
        self.ink_saver = ink_saver
        self.accent = _hex_to_rgb(itinerary.cover_color)
        self.default_tz = itinerary.default_timezone

    def t(self, text: str) -> str:
        return tr(text, self.lang)

    def d(self, day, style: str) -> str:
        return fmt_date(day, style, self.lang)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=18, top=18, right=18)
        self.set_title(itinerary.title)

    # -- page furniture -------------------------------------------------
    def footer(self) -> None:
        if self.page_no() == 1:  # no footer on the cover
            return
        self.set_y(-15)
        self.set_font(FONT, size=8)
        self.set_text_color(*MUTED)
        self.cell(0, 10, self.itinerary.title, align="L")
        self.cell(0, 10, f"{self.page_no() - 1}", align="R")

    @property
    def content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def _tz_label(self, offset: int | None) -> str:
        """Parenthesized UTC-offset label, shown only when it differs from the
        trip default (empty string otherwise)."""
        if offset is None or offset == self.default_tz:
            return ""
        return f"({_format_tz(offset)})"

    def _band_header(self, kicker: str, title: str, right_text: str = "") -> None:
        """A full-width accent band with a small kicker, a big title, and an
        optional right-aligned note. Used to open day and section pages.

        In ink-saving mode the solid band is replaced by accent-colored text
        over a thin accent rule."""
        band_h = 30
        if self.ink_saver:
            kicker_col = self.accent
            title_col = INK
            right_col = MUTED
        else:
            self.set_fill_color(*self.accent)
            self.rect(0, 0, self.w, band_h, style="F")
            kicker_col = title_col = right_col = (255, 255, 255)

        self.set_xy(self.l_margin, 11)
        self.set_font(FONT, "B", 9)
        self.set_text_color(*kicker_col)
        self.cell(0, 5, kicker)
        if right_text:
            self.set_xy(self.l_margin, 11)
            self.set_font(FONT, "", 10)
            self.set_text_color(*right_col)
            self.cell(self.content_width, 5, right_text, align="R")

        self.set_xy(self.l_margin, 17)
        self.set_font(FONT, "B", 18)
        self.set_text_color(*title_col)
        self.cell(0, 9, title)

        if self.ink_saver:  # a hairline stands in for the band's bottom edge
            self.set_draw_color(*self.accent)
            self.set_line_width(0.6)
            self.line(self.l_margin, band_h, self.w - self.r_margin, band_h)

        self.set_y(band_h + 6)
        self.set_text_color(*INK)

    def _card_bg(self, y: float, h: float) -> None:
        """Card background + 2 mm accent spine. In ink-saving mode the light
        tint fill becomes a thin outline; the slim spine is kept either way."""
        if self.ink_saver:
            self.set_draw_color(*_tint(self.accent, 0.5))
            self.set_line_width(0.3)
            self.rect(self.l_margin, y, self.content_width, h, style="D")
        else:
            self.set_fill_color(*_tint(self.accent, 0.93))
            self.rect(self.l_margin, y, self.content_width, h, style="F")
        self.set_fill_color(*self.accent)
        self.rect(self.l_margin, y, 2, h, style="F")

    def _measure_lines(self, text: str, w: float, size: float = 10,
                       style: str = "") -> int:
        if not text:
            return 0
        self.set_font(FONT, style, size)
        return len(self.multi_cell(w, 5, text, dry_run=True, output="LINES"))

    def _pill_w(self, label: str) -> float:
        self.set_font(FONT, "B", 7)
        return self.get_string_width(label) + 5

    def _pill(self, label: str, x: float, y: float, filled: bool = True) -> float:
        w = self._pill_w(label)
        if self.ink_saver:
            # Outline always; an emphasized ("filled") pill keeps a faint tint
            # so the emphasized/de-emphasized distinction survives on paper.
            self.set_draw_color(*self.accent)
            self.set_line_width(0.4)
            if filled:
                self.set_fill_color(*_tint(self.accent, 0.82))
                self.rect(x, y, w, 5.5, style="DF")
            else:
                self.rect(x, y, w, 5.5, style="D")
            self.set_text_color(*self.accent)
        elif filled:
            self.set_fill_color(*self.accent)
            self.rect(x, y, w, 5.5, style="F")
            self.set_text_color(255, 255, 255)
        else:
            self.set_draw_color(*self.accent)
            self.set_line_width(0.4)
            self.rect(x, y, w, 5.5, style="D")
            self.set_text_color(*self.accent)
        self.set_xy(x, y + 0.7)
        self.cell(w, 4.3, label, align="C")
        return w

    def _section_title(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font(FONT, "B", 12)
        self.set_text_color(*self.accent)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        y = self.get_y()
        self.set_draw_color(*LIGHT)
        self.set_line_width(0.4)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(2)

    def _badge(self, x: float, y: float, w: float, label: str) -> None:
        h = 5.6
        if self.ink_saver:
            self.set_draw_color(*self.accent)
            self.set_line_width(0.3)
            self.rect(x, y + 0.3, w, h, style="D")
            text_col = self.accent
        else:
            self.set_fill_color(*self.accent)
            self.rect(x, y + 0.3, w, h, style="F")
            text_col = (255, 255, 255)
        self.set_xy(x, y + 0.7)
        self.set_font(FONT, "B", 7)
        self.set_text_color(*text_col)
        self.cell(w, 4.8, label, align="C")

    def _meta_line(self, x: float, w: float, parts) -> None:
        parts = [p for p in parts if p]
        if not parts:
            return
        self.set_x(x)
        self.set_font(FONT, "", 9)
        self.set_text_color(*MUTED)
        self.multi_cell(w, 5, "  ·  ".join(parts))

    def _para(self, x: float, w: float, text: str) -> None:
        self.set_x(x)
        self.set_font(FONT, "", 10)
        self.set_text_color(*MUTED)
        self.multi_cell(w, 5, text)

    def _nav_geom(self, text: str, w: float, size: float, style: str) -> tuple:
        """Shared geometry for the ``text`` + inline "(Navigate)" block: the
        wrapped text lines, the width of the last one (in the text font), the
        "(Navigate)" label and its width, and whether the label fits after the
        last line. Leaves the font set to the text face."""
        label = self.t("(Navigate)")
        self.set_font(FONT, style, size)
        lines = self.multi_cell(w, 5, text, dry_run=True, output="LINES") or [text]
        last_w = self.get_string_width(lines[-1])
        self.set_font(FONT, "", size)
        label_w = self.get_string_width(label)
        gap = self.get_string_width("  ")
        self.set_font(FONT, style, size)
        return lines, last_w, label, label_w, last_w + gap + label_w <= w

    def _nav_block_h(self, text: str, coordinate, *query_parts, w: float,
                     size: float = 9, h: float = 5, style: str = "") -> float:
        """The height :meth:`_line_with_nav` will consume for these arguments
        (so cards can reserve exactly the right space)."""
        url = maps_url(coordinate, *query_parts)
        if not text:
            return h if url else 0
        lines, _, _, _, fits = self._nav_geom(text, w, size, style)
        if not url:
            return len(lines) * h
        return len(lines) * h if fits else (len(lines) + 1) * h

    def _line_with_nav(self, x: float, w: float, text: str, coordinate,
                       *query_parts, size: float = 9, h: float = 5,
                       style: str = "", color=MUTED) -> None:
        """Draw ``text`` (wrapped to ``w``, font ``style``/``size``, colour
        ``color``) with a clickable accent "(Navigate)" link right after its
        last line — the link points at ``coordinate``, else the first non-empty
        ``query_parts`` address / place name. The link drops to its own line
        only when it would not fit. With no text, just the link is drawn; with
        no locatable target, just the text. Advances the cursor below."""
        url = maps_url(coordinate, *query_parts)
        y = self.get_y()
        if not text and not url:
            return
        if not text:
            self.set_xy(x, y)
            self.set_font(FONT, "", size)
            self.set_text_color(*self.accent)
            self.cell(self.get_string_width(self.t("(Navigate)")), h,
                      self.t("(Navigate)"), link=url)
            self.set_y(y + h)
            return
        lines, last_w, label, label_w, fits = self._nav_geom(text, w, size, style)
        n = len(lines)
        self.set_xy(x, y)
        self.set_text_color(*color)
        self.multi_cell(w, h, text)
        if not url:
            return
        self.set_font(FONT, "", size)
        self.set_text_color(*self.accent)
        gap = self.get_string_width("  ")
        if fits:
            self.set_xy(x + last_w + gap, y + (n - 1) * h)
            self.cell(label_w, h, label, link=url)
            self.set_y(y + n * h)
        else:
            self.set_xy(x, y + n * h)
            self.cell(label_w, h, label, link=url)
            self.set_y(y + (n + 1) * h)

    def _link_row(self, x: float, y: float, links, size: float = 9) -> float:
        """Draw a row of clickable hyperlinks in the accent color at ``(x, y)``,
        separated by muted dots. ``links`` is a list of ``(label, url)`` pairs;
        pairs with an empty url are skipped. Returns the row height (0 when
        nothing was drawn)."""
        links = [(label, url) for label, url in links if url]
        if not links:
            return 0
        cx = x
        for i, (label, url) in enumerate(links):
            if i:
                sep = "  ·  "
                self.set_font(FONT, "", size)
                self.set_text_color(*MUTED)
                self.set_xy(cx, y)
                sw = self.get_string_width(sep)
                self.cell(sw, 5, sep)
                cx += sw
            self.set_font(FONT, "", size)
            self.set_text_color(*self.accent)
            self.set_xy(cx, y)
            lw = self.get_string_width(label)
            self.cell(lw, 5, label, link=url)
            cx += lw
        return 5

    # -- prices ---------------------------------------------------------
    def _money(self, amount: float, code: str, converted: bool = False) -> str:
        return format_money(amount, code, self.lang, converted)

    def price_parts(self, amount, currency: str) -> tuple[str, str]:
        """(primary, secondary) strings for a price: the amount in the trip's
        default currency, plus a parenthesized list of the same amount in every
        secondary currency (empty when there are none). An amount whose currency
        has no known rate is shown as-is, with no conversions."""
        it = self.itinerary
        base = it.in_default(amount, currency)
        if base is None:  # unknown currency — nothing to convert against
            return self._money(amount, currency or it.default_currency), ""
        # The primary is a conversion only when the price was given in a
        # non-default currency; a native amount keeps its exact figure.
        converted = bool(currency) and currency.strip().upper() != it.default_currency
        primary = self._money(base, it.default_currency, converted=converted)
        secs = [self._money(s.change_rate * base, s.currency, converted=True)
                for s in it.secondary_currencies]
        return primary, (f"({', '.join(secs)})" if secs else "")

    def _draw_price(self, x: float, y: float, w: float, amount, currency: str) -> None:
        """Draw a price row: the default-currency amount in bold, followed by
        any secondary-currency conversions in a lighter, smaller face."""
        primary, secondary = self.price_parts(amount, currency)
        self.set_xy(x, y)
        self.set_font(FONT, "B", 10)
        self.set_text_color(*MUTED)
        pw = self.get_string_width(primary)
        self.cell(pw, 5, primary)
        if secondary:
            self.set_font(FONT, "", 9)
            self.set_text_color(*FAINT)
            self.cell(w - pw, 5, "  " + secondary)

    def _chip(self, x: float, label: str) -> None:
        self.ln(0.8)
        self.set_x(x)
        self.set_font(FONT, "B", 7)
        tw = self.get_string_width(label) + 4
        y = self.get_y()
        if self.ink_saver:
            self.set_draw_color(*self.accent)
            self.set_line_width(0.3)
            self.rect(x, y, tw, 4.8, style="D")
            text_col = self.accent
        else:
            self.set_fill_color(*self.accent)
            self.rect(x, y, tw, 4.8, style="F")
            text_col = (255, 255, 255)
        self.set_xy(x, y + 0.4)
        self.set_text_color(*text_col)
        self.cell(tw, 4.0, label, align="C")
        self.ln(5.4)

