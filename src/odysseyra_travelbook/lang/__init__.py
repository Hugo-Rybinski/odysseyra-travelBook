"""Localization: string translation (:func:`tr`) and localized date
formatting (:func:`fmt_date`). Strings live in :mod:`.translations`, date
tables in :mod:`.dates`."""

from __future__ import annotations

from .dates import fmt_date, fmt_weekday_runs, weekday_name
from .translations import TRANSLATIONS

LANGUAGES = ("en", "fr")
DEFAULT_LANGUAGE = "en"


def _lang(lang: str) -> str:
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def tr(text: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Translate ``text`` to ``lang`` (English source is returned unchanged, as
    is any string without an entry)."""
    if not text or _lang(lang) == "en":
        return text
    return TRANSLATIONS.get(_lang(lang), {}).get(text, text)


__all__ = ["LANGUAGES", "DEFAULT_LANGUAGE", "tr", "fmt_date", "fmt_weekday_runs",
           "weekday_name", "TRANSLATIONS"]
