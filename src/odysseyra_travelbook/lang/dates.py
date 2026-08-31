"""Localized date formatting (month / weekday names and ordering)."""

from __future__ import annotations

from datetime import date

_MONTH_ABBR = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
           "Oct", "Nov", "Dec"],
    "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
           "sept.", "oct.", "nov.", "déc."],
}
_WEEKDAY_ABBR = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "fr": ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."],
}
_WEEKDAY_FULL = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
           "Sunday"],
    "fr": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi",
           "dimanche"],
}

# The canonical weekday keys an ``Opening`` speaks in (models/opening.py's
# WEEKDAYS) are exactly these English names lowercased, so the index table is
# derived rather than restated — a test pins the two together.
_WEEKDAY_INDEX = {name.lower(): i for i, name in enumerate(_WEEKDAY_FULL["en"])}


def weekday_name(d: date, lang: str = "en", abbr: bool = False) -> str:
    """A date's weekday on its own — ``Monday`` / ``lundi``. ``fmt_date`` covers
    every case that also wants the day and month; this is for a sentence that
    names only the weekday (the validator's closed-on-that-day warning)."""
    lg = lang if lang in _WEEKDAY_FULL else "en"
    table = _WEEKDAY_ABBR[lg] if abbr else _WEEKDAY_FULL[lg]
    return table[d.weekday()]


def fmt_weekday_runs(runs, lang: str = "en", abbr: bool = True) -> str:
    """A point of interest's opening-day runs, localized: ``(("tuesday",
    "sunday"),)`` → ``Tue–Sun`` / ``mar.–dim.``, and a run of one day → that day
    alone. Takes the canonical name pairs of ``Opening.day_runs`` so the folding
    is done once, in the model, and only the naming happens here.

    ``abbr`` picks the short forms (what the renderers print); the validator asks
    for the full names, since a warning is a sentence."""
    lg = lang if lang in _WEEKDAY_ABBR else "en"
    table = _WEEKDAY_ABBR[lg] if abbr else _WEEKDAY_FULL[lg]

    def name(key: str) -> str:
        return table[_WEEKDAY_INDEX[key]]

    return ", ".join(
        name(first) if first == last else f"{name(first)}–{name(last)}"
        for first, last in runs
    )


def fmt_date(d: date | None, style: str, lang: str = "en") -> str:
    """Localized date formatting.

    Styles: ``long`` (Jun 08, 2026), ``md`` (Jun 08), ``wd_md`` (Mon Jun 08),
    ``wd_full_md`` (Monday, Jun 08).
    """
    if d is None:
        return ""
    lg = lang if lang in _MONTH_ABBR else "en"
    mon = _MONTH_ABBR[lg][d.month - 1]
    wda = _WEEKDAY_ABBR[lg][d.weekday()]
    wdf = _WEEKDAY_FULL[lg][d.weekday()]
    if lg == "fr":
        return {
            "long": f"{d.day:02d} {mon} {d.year}",
            "md": f"{d.day:02d} {mon}",
            "wd_md": f"{wda} {d.day:02d} {mon}",
            "wd_full_md": f"{wdf} {d.day:02d} {mon}",
        }[style]
    return {
        "long": f"{mon} {d.day:02d}, {d.year}",
        "md": f"{mon} {d.day:02d}",
        "wd_md": f"{wda} {mon} {d.day:02d}",
        "wd_full_md": f"{wdf}, {mon} {d.day:02d}",
    }[style]
