"""Shared PDF scaffolding: fonts, colors, and the low-level drawing helpers
(:class:`_PDFBase`) that every section mixin builds on."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from ..lang import DEFAULT_LANGUAGE, fmt_date, tr
from ..models import (
    DEFAULT_MAP_PROVIDER,
    Itinerary,
    _format_tz,
    format_money,
    maps_url,
)

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
FONT = "DejaVu"  # bundled Unicode font: handles accents, CJK-latin, arrows, …
# A tiny bundled subset of Noto Emoji (monochrome) holding only the eight
# moon-phase glyphs (U+1F311..U+1F318), which DejaVu lacks — registered as a
# fallback so the "tonight" moon-phase emoji render instead of tofu.
EMOJI_FONT = "NotoEmojiMoon"

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
                 ink_saver: bool = False, map_provider: str = DEFAULT_MAP_PROVIDER):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.add_font(FONT, "", FONT_DIR / "DejaVuSans.ttf")
        self.add_font(FONT, "B", FONT_DIR / "DejaVuSans-Bold.ttf")
        self.add_font(FONT, "I", FONT_DIR / "DejaVuSans-Oblique.ttf")
        # Emoji fallback for the moon-phase glyphs (see EMOJI_FONT); fpdf2 uses
        # it only for codepoints DejaVu can't draw, so normal text is unaffected.
        # `exact_match=False` because the subset is regular-only: with the
        # default (True), a **bold** run finds no bold emoji font and silently
        # drops the glyph — which is what happened to the moon when the sun/moon
        # line moved into the day's body and became bold. Emoji have no weight
        # of their own, so falling back across styles is exactly right.
        self.add_font(EMOJI_FONT, "", FONT_DIR / "NotoEmojiMoon.ttf")
        self.set_fallback_fonts([EMOJI_FONT], exact_match=False)
        self.itinerary = itinerary
        self.lang = lang
        # Ink-saving mode: skip large solid accent fills (cover banner, page
        # header bands, card backgrounds) and draw outlines / thin rules
        # instead, keeping the accent color only for text and hairlines.
        self.ink_saver = ink_saver
        # Which maps/navigation app the inline "(Navigate)" links open.
        self.map_provider = map_provider
        self.accent = _hex_to_rgb(itinerary.cover_color)
        self.default_tz = itinerary.default_timezone
        self.set_title(itinerary.title)
        # The page box. These two lines spent the file's whole life unreachable
        # — they sat after the `return` in `d()` below — so every book ever
        # printed used fpdf's defaults, and the whole layout (the gutter, the
        # card widths, the map height caps) was measured against those. They are
        # restated here at the values actually in force rather than "restored"
        # to the 18 mm they were written with: narrowing the column by 16 mm
        # reflows every page and changes the page count, which is a design
        # decision and not a bug fix.
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=10, top=10, right=10)

    def t(self, text: str) -> str:
        return tr(text, self.lang)

    def d(self, day, style: str) -> str:
        return fmt_date(day, style, self.lang)

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

    # The call-out strip's height, and the inset its text sits at (clear of the
    # accent spine `_card_bg` also draws).
    _NOTICE_H = 9.0
    _NOTICE_PAD = 6.0

    def _notice(self, label: str, text: str = "") -> None:
        """A full-width call-out strip drawn at the cursor: a bold accent label,
        followed by a muted sentence when there's room for it on the same line
        (there is only one line — the strip is a heads-up, not a paragraph).
        Advances the cursor past it.

        Ink-saving mode swaps the tinted fill for an accent outline, like the
        other large accent areas."""
        y = self.get_y()
        if self.ink_saver:
            self.set_draw_color(*self.accent)
            self.set_line_width(0.4)
            self.rect(self.l_margin, y, self.content_width, self._NOTICE_H, style="D")
        else:
            # Deliberately a shade stronger than `_card_bg`'s 0.93: this is a
            # call-out and has to read as more than another card.
            self.set_fill_color(*_tint(self.accent, 0.82))
            self.rect(self.l_margin, y, self.content_width, self._NOTICE_H, style="F")
        self.set_fill_color(*self.accent)
        self.rect(self.l_margin, y, 2, self._NOTICE_H, style="F")

        self.set_font(FONT, "B", 9)
        label_w = self.get_string_width(label)
        if text:
            self.set_font(FONT, "", 9)
            gap = self.get_string_width("  ")
            room = self.content_width - 2 * self._NOTICE_PAD - label_w - gap
            if self.get_string_width(text) > room:
                text = ""  # a long sentence would spill out of the strip

        self.set_xy(self.l_margin + self._NOTICE_PAD, y + 2.3)
        self.set_font(FONT, "B", 9)
        self.set_text_color(*self.accent)
        self.cell(label_w, 4.4, label)
        if text:
            self.set_font(FONT, "", 9)
            self.set_text_color(*MUTED)
            self.cell(0, 4.4, f"  {text}")

        self.set_y(y + self._NOTICE_H + 4)
        self.set_text_color(*INK)

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

    def _badge(self, x: float, y: float, w: float, label: str,
               muted: bool = False) -> None:
        """The gutter type badge. ``muted`` drops the accent for a grey outline
        — the whole point of the accent is emphasis, so an item the day isn't
        counting on (a detour) shouldn't wear it."""
        h = 5.6
        if muted:
            self.set_draw_color(*FAINT)
            self.set_line_width(0.25)
            self.rect(x, y + 0.3, w, h, style="D")
            text_col = MUTED
        elif self.ink_saver:
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

    def _detour_min_width(self, size: float = 6) -> float:
        """The narrowest column :meth:`_detour_tag` can set its label in — its
        widest single word, padded.

        A caller that *owns* its column (a nested item's badge column, sized to
        its siblings' labels) has to widen it to at least this before drawing,
        or the pill's longest word would run past its own box."""
        self.set_font(FONT, "B", size)
        return max(self.get_string_width(w)
                   for w in self.t("DETOUR").split()) + 5

    def _detour_tag(self, x: float, y: float, w: float,
                    size: float = 6) -> float:
        """DETOUR as a grey outline pill filling ``w`` at ``(x, y)``, returning
        its height.

        Drawn **under the type badge, in the badge's own column** — the gutter
        for a top-level row, the nested badge column for a nested one — rather
        than ahead of the title, which buried the name of the place. The slot
        is free because a detour has **no clock time**: the model clears both
        (``resolve_detours``), so the lines the start/end times would occupy
        are exactly what this fills, and the mark lands beside the item instead
        of inside its heading. It is also what the viewer has always done
        (``.t-detour``, in the gutter where the absent start time would be), so
        the two renderers agree on placement as well as meaning.

        Grey rather than accent on purpose: this marks a stop the day is *not*
        counting on, and the accent is what the book uses for emphasis.

        One word, so it sets on one line in both languages. It is still
        **wrapped greedily on spaces** rather than drawn as a single `cell`,
        because a badge column is narrow (the gutter is 23 mm, a nested one
        ~16) and this label is the kind that grows in translation — the pill
        then takes another line instead of running off the column, which is
        also why the height is returned rather than assumed. It was two lines
        itself until the label was shortened from 'OPTIONAL DETOUR' (27.6 mm at
        6.5 pt; French 'DÉTOUR OPTIONNEL' 29.3)."""
        self.set_font(FONT, "B", size)
        lines, cur = [], ""
        for word in self.t("DETOUR").split():
            trial = f"{cur} {word}".strip()
            if cur and self.get_string_width(trial) > w - 2:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            lines.append(cur)

        lh = 2.9
        h = 1.8 + lh * len(lines)
        self.set_draw_color(*FAINT)
        self.set_line_width(0.25)
        self.rect(x, y, w, h, style="D")
        self.set_text_color(*MUTED)
        for i, line in enumerate(lines):
            self.set_xy(x, y + 0.7 + lh * i)
            self.cell(w, lh, line, align="C")
        return h

    def _fit_text(self, text: str, w: float) -> str:
        """``text`` cut back with an ellipsis until it fits ``w`` at the current
        font, or unchanged when it already does.

        fpdf's one-line ``cell`` neither wraps nor clips — it simply draws past
        its own width — so any single-line row carrying a value the user can make
        arbitrarily long (a hotel called "Yurt Camp Ali-Nur, Lake Song-Kul,
        Kyrgyzstan, Юрточный лагерь…") has to be measured first, or it runs off
        the page. Ellipsizing is the right answer only where the full text is
        readable elsewhere in the book — a stay's name is also on the
        accommodation page, an address is also its Navigate link — so a caller
        that would be *losing* information should wrap or drop a part instead.
        The font must already be set."""
        if self.get_string_width(text) <= w:
            return text
        cut = len(text)
        while cut and self.get_string_width(text[:cut].rstrip() + " …") > w:
            cut -= 1
        return text[:cut].rstrip() + " …" if cut else ""

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

    def _guidebook_pill(self, x: float, y: float, pages: str,
                        size: float = 7.5) -> float:
        """The activity's guidebook page reference ("Guidebook p. 15-18") as a
        **rounded pill** drawn at ``(x, y)``; returns its width. A soft accent
        fill with accent text at normal weight — lighter than the solid
        ``_chip``/``_inline_chip`` flags, so it reads as a pointer appended to the
        prose rather than as a marker. Ink-saver drops the fill for an outline.

        Leaves the cursor **on the pill's own line** (like ``_chip``, unlike
        ``_para``); callers that drew text above it must restore y themselves."""
        label = self.t("Guidebook p. {pages}").format(pages=pages)
        self.set_font(FONT, "", size)
        tw = self.get_string_width(label) + 4
        ph = size * 0.56
        self.set_line_width(0.2)
        if self.ink_saver:
            self.set_draw_color(*_tint(self.accent, 0.4))
            style = "D"
        else:
            self.set_fill_color(*_tint(self.accent, 0.86))
            self.set_draw_color(*_tint(self.accent, 0.6))
            style = "DF"
        self.rect(x, y, tw, ph, style=style, round_corners=True,
                  corner_radius=ph / 2)
        self.set_xy(x, y + 0.15)
        self.set_text_color(*self.accent)
        self.cell(tw, ph - 0.3, label, align="C")
        return tw

    def _para_with_pill(self, x: float, w: float, text: str, pages: str,
                        size: float = 10, h: float = 5) -> None:
        """A description paragraph with the guidebook pill appended **after its
        last line**, dropping to a line of its own only when it wouldn't fit.
        Either part may be empty: no pages draws a plain paragraph, no text draws
        the pill alone, and neither draws nothing. Advances the cursor below."""
        if not text and not pages:
            return
        pill_size = max(6.5, size - 2.5)
        # vertically centre the pill on the text line it trails
        dy = (h - pill_size * 0.56) / 2

        def pill_alone() -> None:
            """The pill on a line of its own, breaking the page first if needed."""
            if self.get_y() + h > self.page_break_trigger:
                self.add_page()
            y = self.get_y()
            self._guidebook_pill(x, y + dy, pages, pill_size)
            self.set_y(y + h)

        if not text:
            pill_alone()
            return

        self.set_font(FONT, "", size)
        lines = self.multi_cell(w, h, text, dry_run=True, output="LINES") or [text]
        last_w = self.get_string_width(lines[-1])
        gap = self.get_string_width("  ")
        self.set_x(x)
        self.set_text_color(*MUTED)
        self.multi_cell(w, h, text)
        if not pages:
            return
        # where the paragraph left the cursor — restored below, since drawing the
        # pill moves it back up onto the last text line
        end_y = self.get_y()
        # measure the pill in its own (smaller) face before placing it
        self.set_font(FONT, "", pill_size)
        pill_w = self.get_string_width(
            self.t("Guidebook p. {pages}").format(pages=pages)) + 4
        if last_w + gap + pill_w > w:
            pill_alone()
            return
        # Derive the last line's y from the *live* cursor rather than from
        # y + (n-1)*h: the paragraph above may have triggered an auto page
        # break, which would leave that arithmetic pointing at the previous
        # page — drawing the pill's box off-sheet while its text broke onto the
        # next one (exactly what a nested activity near a page end did).
        self._guidebook_pill(x + last_w + gap, end_y - h + dy, pages, pill_size)
        self.set_y(end_y)

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
        # Mirror _line_with_nav: ink-saver draws no "(Navigate)", so no link
        # width to reserve and never a dropped extra line.
        url = "" if self.ink_saver else maps_url(coordinate, *query_parts,
                                                 provider=self.map_provider)
        if not text:
            return h if url else 0
        lines, _, _, _, fits = self._nav_geom(text, w, size, style)
        if not url:
            return len(lines) * h
        return len(lines) * h if fits else (len(lines) + 1) * h

    def _addr_url(self, coordinate, address: str) -> str:
        """An address-based maps URL that *complements* the coordinate Navigate
        link: returned only when BOTH a coordinate and an address exist (so the
        two differ). The displayed address then stays clickable as a search by
        name while "(Navigate)" goes to the exact point. "" otherwise."""
        if coordinate is None or not address:
            return ""
        return maps_url(None, address, provider=self.map_provider)

    def _line_with_nav(self, x: float, w: float, text: str, coordinate,
                       *query_parts, size: float = 9, h: float = 5,
                       style: str = "", color=MUTED, text_url: str = "") -> None:
        """Draw ``text`` (wrapped to ``w``, font ``style``/``size``, colour
        ``color``) with a clickable accent "(Navigate)" link right after its
        last line — the link points at ``coordinate``, else the first non-empty
        ``query_parts`` address / place name. The link drops to its own line
        only when it would not fit. With no text, just the link is drawn; with
        no locatable target, just the text. ``text_url`` (see :meth:`_addr_url`)
        makes the drawn ``text`` itself clickable — an address-based search that
        complements the coordinate Navigate link. Advances the cursor below."""
        url = maps_url(coordinate, *query_parts, provider=self.map_provider)
        if self.ink_saver:
            # Ink-saver drops every hyperlink: no "(Navigate)" and no clickable
            # address — just the plain text (or nothing when there's no text).
            url = text_url = ""
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
        self.multi_cell(w, h, text, link=text_url)
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
        if self.ink_saver:  # ink-saver drops all hyperlinks
            return 0
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

    def price_inline(self, amount, currency: str) -> str:
        """An activity's price as one string for a meta line — ``€12  (1200 KGS)``
        — or ``""`` when there is none.

        Zero is *not* nothing: a guidebook stating that entry is free is telling
        you something, so it prints as ``Free`` rather than as ``€0``. Unlike a
        booking's price this is inline rather than its own bold row: a stop's fee
        is one figure among the duration and the address, not a reservation's
        headline. The viewer's `priceInline` is the same rule — keep them in
        step."""
        if amount is None:
            return ""
        if amount == 0:
            return self.t("Free")
        primary, secondary = self.price_parts(amount, currency)
        return f"{primary}  {secondary}" if secondary else primary

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

    def _inline_chip_width(self, label: str) -> float:
        """The width :meth:`_inline_chip` would draw ``label`` in — so a row that
        ends in one can tell whether it still fits its column."""
        self.set_font(FONT, "B", 6)
        return self.get_string_width(label) + 3

    def _inline_chip(self, label: str) -> None:
        """A small filled pill drawn *inline*, at the cursor, inside a text row —
        used for a VIA leg's off-road marker. Unlike ``_chip`` (which owns its
        line) this advances x past the pill and leaves y where it was, so the row
        can carry on with a link afterwards. Follows ``ink_saver`` like the rest:
        outline + accent text instead of a solid fill."""
        self.set_font(FONT, "B", 6)
        tw = self.get_string_width(label) + 3
        x, y = self.get_x(), self.get_y()
        if self.ink_saver:
            self.set_draw_color(*self.accent)
            self.set_line_width(0.25)
            self.rect(x, y + 0.9, tw, 3.4, style="D")
            text_col = self.accent
        else:
            self.set_fill_color(*self.accent)
            self.rect(x, y + 0.9, tw, 3.4, style="F")
            text_col = (255, 255, 255)
        self.set_xy(x, y + 0.7)
        self.set_text_color(*text_col)
        self.cell(tw, 3.8, label, align="C")
        self.set_xy(x + tw, y)  # back on the row's baseline for what follows

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

