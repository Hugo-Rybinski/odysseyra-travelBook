"""Moon-phase computation for the per-day "tonight" section (opt-in via
``defaults.show_moon_phase``).

Pure and offline: the phase is derived from the date alone, measuring the
moon's age against a known new-moon epoch and rounding to the nearest of the
eight canonical phases. Each phase carries a stable ``key`` (localized by both
the PDF renderer and the web viewer), its emoji (U+1F311..U+1F318) and an
English name (the source string localized in the PDF via ``translations.py``)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Mean synodic month (new moon → new moon) and a reference new moon to count
# from. Rounding to one of eight phases makes this precise enough offline.
_SYNODIC = 29.530588853
_NEW_MOON_EPOCH = date(2000, 1, 6)


@dataclass(frozen=True)
class MoonPhase:
    key: str  # stable label key, shared with the web viewer's format.ts
    emoji: str  # U+1F311..U+1F318
    name: str  # English source name (localized downstream)


# From new (index 0) around to waning crescent (index 7).
_PHASES = (
    MoonPhase("moonNew", "\U0001f311", "New moon"),
    MoonPhase("moonWaxingCrescent", "\U0001f312", "Waxing crescent"),
    MoonPhase("moonFirstQuarter", "\U0001f313", "First quarter"),
    MoonPhase("moonWaxingGibbous", "\U0001f314", "Waxing gibbous"),
    MoonPhase("moonFull", "\U0001f315", "Full moon"),
    MoonPhase("moonWaningGibbous", "\U0001f316", "Waning gibbous"),
    MoonPhase("moonLastQuarter", "\U0001f317", "Last quarter"),
    MoonPhase("moonWaningCrescent", "\U0001f318", "Waning crescent"),
)


def moon_phase(d: date) -> MoonPhase:
    """The moon phase for the night of ``d`` — nearest of the eight phases."""
    age = ((d - _NEW_MOON_EPOCH).days % _SYNODIC) / _SYNODIC  # 0..1 of the cycle
    return _PHASES[round(age * 8) % 8]
