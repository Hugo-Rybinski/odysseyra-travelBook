"""A URL, an email address or a phone number written *inside* prose.

The rule the book uses to decide what in a paragraph is worth making clickable.
Three kinds, and nothing else: a **URL**, an **email address**, a **phone
number**.

It is deliberately much stricter than the whole-value rule the ``contact``
fields use (there, a bare ``112`` is exactly the number you want to tap). A loose
rule let into prose claims ``09:30-18:00``, ``12 km``, a guidebook range
``25-30`` or a year span ``1789-1799`` — and a link that goes to the wrong place
is worse than one that isn't there. What that strictness is made of:

* **A leading ``+`` is its own evidence** — nothing else written in a trip file
  opens that way — so an international number needs only 7 digits. Without one
  the floor is a full national number at 9, which clears every date (8 digits),
  price, distance, altitude and page range a description carries.
* **``:`` and ``,`` are not separators.** They are what a time and a page list
  are made of.
* **A candidate with exactly one separator reads as a decimal**, since a real
  number is either grouped (``01 42 60 30 30``) or solid (``0142603030``). That
  is what keeps ``1234.56789`` from dialling.
* **A URL must name itself** — ``https://…`` or a ``www.`` host. A bare
  ``example.com`` is not enough: ``trip.json``, ``p.m.`` and a sentence that runs
  ``…the abbey.Or the château`` all look the same to that pattern, and the cost
  of guessing wrong is a link to nowhere.
* **A candidate glued to something larger is dropped**, which is what lets a
  query string survive: ``?id=1234567890`` is not a phone number.

The viewer implements the same rule in ``web/src/render/contact.tsx``
(``linkifyProse``) — **keep the two in step**; there is no JS test runner, so
``tests/test_prose_links.py`` is the contract both sides answer to.
"""

from __future__ import annotations

import re

__all__ = ["find_links", "markdown_prose", "MIN_DIGITS_INTL", "MIN_DIGITS_LOCAL"]

# Candidates only — classified (and trimmed) below. Ordered: a URL is tried
# first at each position so `https://x.com/1234567890` is consumed whole rather
# than leaving its digits behind.
_CANDIDATE = re.compile(
    r"""(?:https?://|www\.)[^\s<>"'\[\]]+"""     # a URL
    r"""|[A-Za-z0-9._%+-]+@[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]"""  # an email
    r"""|\+?\d[\d .()-]*\d"""                    # a phone number
)

_MAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")

# A character that, sitting against a candidate, says it is part of something
# larger: a word, an address, a time, a date, a decimal, a fraction, a URL.
_GLUED = re.compile(r"[\w@:/=?&#%~]")

_SEPARATORS = re.compile(r"[ .()-]")

MIN_DIGITS_INTL = 7
MIN_DIGITS_LOCAL = 9

# Sentence punctuation a URL may collect but never own.
_URL_TRAIL = ".,;:!?'\"“”’«»"


def _dialable(token: str) -> bool:
    digits = sum(c.isdigit() for c in token)
    if token.startswith("+"):
        return digits >= MIN_DIGITS_INTL
    if digits < MIN_DIGITS_LOCAL:
        return False
    seps = len(_SEPARATORS.findall(token))
    return seps == 0 or seps >= 2


def _trim_url(token: str) -> str:
    """Drop the sentence punctuation a URL swept up, and a closing bracket that
    was opened outside it — while keeping the one in
    ``…/wiki/Foo_(bar)``, which is part of the address."""
    while token and token[-1] in _URL_TRAIL:
        token = token[:-1]
    while token.endswith(")") and token.count(")") > token.count("("):
        token = token[:-1]
        while token and token[-1] in _URL_TRAIL:
            token = token[:-1]
    return token


def _classify(token: str) -> tuple[str, str] | None:
    """``(token, url)`` for a candidate worth linking, else None."""
    low = token.lower()
    if low.startswith(("http://", "https://", "www.")):
        token = _trim_url(token)
        if len(token) < 8:  # "www.a.bc" is the shortest thing worth pointing at
            return None
        url = token if low.startswith("http") else f"https://{token}"
        return token, url
    if _MAIL.match(token):
        return token, f"mailto:{token}"
    token = token.rstrip(" .()-")
    if token and _dialable(token):
        return token, "tel:" + re.sub(r"[^\d+]", "", token)
    return None


def find_links(text: str) -> list[tuple[int, int, str]]:
    """Every linkable span in ``text`` as ``(start, end, url)``, in order."""
    out: list[tuple[int, int, str]] = []
    for m in _CANDIDATE.finditer(text):
        found = _classify(m.group(0))
        if not found:
            continue
        token, url = found
        start = m.start()
        end = start + len(token)
        before = text[start - 1] if start else ""
        after = text[end] if end < len(text) else ""
        if before and (_GLUED.match(before) or before in ".+-"):
            continue
        if after and _GLUED.match(after):
            continue
        out.append((start, end, url))
    return out


# --- rendering it through fpdf2's markdown ----------------------------------
#
# fpdf2 draws a link inside flowing text as `[label](url)` with
# ``multi_cell(markdown=True)``, which is the only route that keeps the
# justification and the line breaking we already have — computing each token's
# position ourselves would mean re-deriving how a justified line stretches its
# spaces, for a paragraph fpdf2 has already laid out.
#
# The cost is that the *rest* of the paragraph is then markup too, so the
# emphasis markers have to be escaped. All four are, plus the escape character
# itself, in one pass.

_MD_MARKERS = ("**", "__", "~~", "--")


def _escape_markdown(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\":
            out.append("\\\\")
            i += 1
            continue
        if text[i:i + 2] in _MD_MARKERS:
            out.append("\\" + text[i:i + 2])
            i += 2
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def markdown_prose(text: str) -> str | None:
    """``text`` rewritten with fpdf2 markdown links over its URLs, emails and
    phone numbers — or **None** when there is nothing to link or the paragraph
    can't safely be drawn as markdown.

    The one unsafe case is prose that already contains ``](``: fpdf2 has no
    escape for a bracket, so that text would grow a link of its own. Nothing is
    lost by declining — the paragraph is drawn as plain text, exactly as before.
    """
    spans = find_links(text)
    if not spans:
        return None
    if "](" in text:
        return None
    # A url with a paren can't be written as `(url)` — fpdf2's link pattern
    # stops at the first one — so those spans are dropped rather than mangled.
    spans = [s for s in spans if "(" not in s[2] and ")" not in s[2]]
    if not spans:
        return None
    out: list[str] = []
    pos = 0
    for start, end, url in spans:
        out.append(_escape_markdown(text[pos:start]))
        out.append(f"[{text[start:end]}]({url})")
        pos = end
    out.append(_escape_markdown(text[pos:]))
    return "".join(out)
