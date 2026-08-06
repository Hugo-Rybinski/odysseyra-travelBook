"""Currency handling: the trip's default currency plus optional secondary
currencies, conversion between them, and money formatting.

A price is a bare amount (a ``float``) in some currency. Each priced object may
name its own ``currency`` (an ISO code); when it doesn't, the amount is taken to
be in the trip's ``default_currency``. Secondary currencies carry a
``change_rate`` expressed as *units of that currency per one unit of the default*
(so with a EUR default, a USD ``change_rate`` of ``1.09`` means 1 € = $1.09)."""

from __future__ import annotations

from dataclasses import dataclass


# Currencies we print with their own symbol; anything else prints its ISO code.
CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥"}


@dataclass
class SecondaryCurrency:
    """An extra currency to also show prices in, alongside the default."""

    currency: str  # ISO code, e.g. "USD"
    change_rate: float  # units of this currency per 1 unit of the default


def to_default(amount, code, default_currency, secondaries):
    """Convert ``amount`` (given in currency ``code``, or the default when
    ``code`` is empty) into the trip's default currency. Returns ``None`` when
    ``code`` is neither the default nor a known secondary currency (no rate)."""
    code = (code or default_currency).strip().upper()
    if code == default_currency:
        return amount
    for sec in secondaries:
        if sec.currency == code and sec.change_rate:
            return amount / sec.change_rate
    return None


def _fmt_amount(amount: float) -> str:
    """A whole number when the amount is (near-)integral, else two decimals."""
    if abs(amount - round(amount)) < 0.005:
        return str(int(round(amount)))
    return f"{amount:.2f}"


def _fmt_converted(amount: float) -> str:
    """A converted (approximate) amount: two decimals below 25, whole at/above
    — small sums keep the cents that matter, larger ones round off."""
    if abs(amount) < 25:
        return f"{amount:.2f}"
    return str(int(round(amount)))


def format_money(amount: float, code: str, lang: str = "en",
                 converted: bool = False) -> str:
    """Render ``amount`` in currency ``code``. Major currencies use their own
    symbol (``€612`` in English, ``612 €`` in French); others show the ISO code
    after the amount (``612 CHF``). ``converted`` amounts (the result of an
    exchange-rate conversion) round per :func:`_fmt_converted`."""
    n = _fmt_converted(amount) if converted else _fmt_amount(amount)
    sym = CURRENCY_SYMBOLS.get((code or "").strip().upper())
    if not sym:
        return f"{n} {code}".strip()
    if lang == "fr":  # French convention: the symbol trails the amount
        return f"{n} {sym}"
    return f"{sym}{n}"
