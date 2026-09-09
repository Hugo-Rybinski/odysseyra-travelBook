"""The in-prose link rule — the contract both renderers implement.

``prose_links.find_links`` is mirrored by the viewer's
``web/src/render/contact.tsx`` (``linkifyProse``). There is no JS test runner, so
this file is where the rule is pinned; when a case changes here, change it there
too.
"""

import pytest

from odysseyra_travelbook.prose_links import find_links, markdown_prose

# --- what must link --------------------------------------------------------

LINKS = [
    # (prose, [(token, url), …])
    ("Book ahead on +996 312 44 55 66.", [("+996 312 44 55 66", "tel:+996312445566")]),
    ("Call +33 1 42 60 30 30 for a table", [("+33 1 42 60 30 30", "tel:+33142603030")]),
    ("Reception: +1 (212) 555-1234", [("+1 (212) 555-1234", "tel:+12125551234")]),
    ("Ring 01 42 60 30 30 the day before", [("01 42 60 30 30", "tel:0142603030")]),
    ("Guardian: 01.42.60.30.30", [("01.42.60.30.30", "tel:0142603030")]),
    ("Phone 0142603030 to open the chapel", [("0142603030", "tel:0142603030")]),
    ("Write to gardien@abbaye.example.fr first",
     [("gardien@abbaye.example.fr", "mailto:gardien@abbaye.example.fr")]),
    ("Ask camping@example.co.uk.", [("camping@example.co.uk", "mailto:camping@example.co.uk")]),
    ("Tickets at https://lascaux.example/en/book now",
     [("https://lascaux.example/en/book", "https://lascaux.example/en/book")]),
    ("See https://example.com/page.", [("https://example.com/page", "https://example.com/page")]),
    ("Details on www.example.com/tickets",
     [("www.example.com/tickets", "https://www.example.com/tickets")]),
    ("Read (https://en.wikipedia.org/wiki/Foo_(bar)) for context",
     [("https://en.wikipedia.org/wiki/Foo_(bar)",
       "https://en.wikipedia.org/wiki/Foo_(bar)")]),
    ("Call +996 312 44 55 66 or mail a@b.com",
     [("+996 312 44 55 66", "tel:+996312445566"), ("a@b.com", "mailto:a@b.com")]),
    ("Book on https://x.example/r?id=7 or ring 0142603030",
     [("https://x.example/r?id=7", "https://x.example/r?id=7"),
      ("0142603030", "tel:0142603030")]),
]


@pytest.mark.parametrize("text,want", LINKS)
def test_links(text, want):
    got = [(text[a:b], url) for a, b, url in find_links(text)]
    assert got == want


# --- what must NOT link ----------------------------------------------------

SKIP = [
    "Open 09:30-12:30, 14:00-18:00 every day",
    "09:30-18:00",
    "See pages 25-30 and 16, 23",
    "A 345 km drive, 12 km of it off-road",
    "1 250 m of ascent over 18 km",
    "Built 1789-1799 by the abbey",
    "Closed on 2026-09-09 for the holiday",
    "Entry costs 22 EUR, children 11.50",
    "The whole trip came to 1 250 000 KGS",
    "Meet at 42.12345, 0.54321 on the col",
    "The ratio is 1234.56789 exactly",
    "4h30 · 345 km · leave by 08:00",
    "Reference AF77-QWLM1234567890",
    "Take exit 1234567 890",
    # a bare domain names nothing: trip.json and p.m. look identical to it
    "Saved as trip.json in the folder",
    "Arrive by 6 p.m. at the latest",
    "The village of Sainte-Marie.Or the col",
]


# Digits inside a URL belong to the URL, not to a phone number — the one case
# the alternation order exists for.
@pytest.mark.parametrize("text,url", [
    ("See https://ex.example/1234567890 for details", "https://ex.example/1234567890"),
    ("Book at https://ex.example/r?id=1234567890&x=2 now",
     "https://ex.example/r?id=1234567890&x=2"),
])
def test_digits_in_a_url_stay_in_the_url(text, url):
    assert [(text[a:b], u) for a, b, u in find_links(text)] == [(url, url)]


@pytest.mark.parametrize("text", SKIP)
def test_skipped(text):
    assert find_links(text) == []


# --- the fpdf2 markdown rendering ------------------------------------------

def test_markdown_wraps_the_token_only():
    md = markdown_prose("Ring 01 42 60 30 30 the day before")
    assert md == "Ring [01 42 60 30 30](tel:0142603030) the day before"


def test_markdown_is_none_without_a_link():
    assert markdown_prose("A quiet day in the valley.") is None


def test_markdown_escapes_the_emphasis_markers():
    # `--` would otherwise underline the rest of the paragraph, and `**` embolden
    # it: the prose around a link is markup too, so all four markers are escaped.
    md = markdown_prose("Ring 0142603030 -- ask for the **guardian** __first__")
    assert md == ("Ring [0142603030](tel:0142603030) \\-- ask for the "
                  "\\**guardian\\** \\__first\\__")


def test_markdown_declines_prose_that_is_already_a_link():
    # fpdf2 has no escape for a bracket, so this text would grow a link of its
    # own. Declining costs the link and keeps the sentence intact.
    assert markdown_prose("See [the site](https://x.example) or ring 0142603030") is None


def test_markdown_drops_a_url_with_a_paren():
    # fpdf2's link pattern stops at the first paren, so `(url)` can't hold one.
    # The other links in the paragraph survive.
    md = markdown_prose("See https://en.wikipedia.org/wiki/Foo_(bar) or ring 0142603030")
    assert md == "See https://en.wikipedia.org/wiki/Foo_(bar) or ring [0142603030](tel:0142603030)"


def test_markdown_leaves_the_text_readable():
    """Whatever is injected, stripping the markup must give the prose back."""
    import re
    for text, _ in LINKS:
        md = markdown_prose(text)
        if md is None:  # every link in it was dropped (a url with a paren)
            continue
        plain = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md).replace("\\", "")
        assert plain == text
