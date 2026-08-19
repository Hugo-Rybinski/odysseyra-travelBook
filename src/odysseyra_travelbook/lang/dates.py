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
