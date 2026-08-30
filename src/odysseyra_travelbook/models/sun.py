"""Sunrise / sunset computation for each day's header band (on by default,
switched off with ``defaults.show_sun_times``).

Pure and offline: the times come from the NOAA sunrise equation and are
converted to the day's wall clock, so a trip whose ``defaults.timezone`` matches
its region reads correctly. Each end gets its own reference coordinate — the
sunset at that night's accommodation (``Itinerary.sun_reference``), the sunrise
where you woke (``Itinerary.wake_reference``) — assembled by
``Itinerary.sun_for``; this module just answers "sun times here, that day".

The result carries a symbol-only ``display`` (``☀ 06:12 → 21:34``) so the PDF
and the web viewer show the same string with nothing to translate."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

# JD 2451545.0 (the J2000.0 epoch) is 2000-01-01 12:00 UT — the same instant
# expressed as a date to count days from and as a naive-UTC datetime to add to.
_EPOCH_DATE = date(2000, 1, 1)
_EPOCH_DT = datetime(2000, 1, 1, 12, 0)
_OBLIQUITY = 23.4397  # Earth's axial tilt, degrees
# Altitude of the sun's centre at rise/set: half a solar diameter below the
# horizon plus standard atmospheric refraction.
_HORIZON = -0.833


def _sin(deg: float) -> float:
    return math.sin(math.radians(deg))


def _cos(deg: float) -> float:
    return math.cos(math.radians(deg))


@dataclass(frozen=True)
class SunTimes:
    """The day's sunrise and sunset as local wall clock times.

    Deliberately just the two times: the display string
    (``☀️ Sunrise: 06:12, Sunset: 21:34``) spells the labels out, so it is
    language-dependent and belongs to the renderers — `pdf/days.py` via
    ``translations.py`` and the viewer via ``render/format.ts``, both keyed on
    the same English template."""

    sunrise: time
    sunset: time

    @property
    def hhmm(self) -> tuple[str, str]:
        """``(sunrise, sunset)`` as ``HH:MM`` — what the display templates take."""
        return f"{self.sunrise:%H:%M}", f"{self.sunset:%H:%M}"


def sun_times(day: date, lat: float, long: float, tz_minutes: int = 0) -> SunTimes | None:
    """Sunrise/sunset for ``day`` at ``lat``/``long`` (degrees, east-positive),
    returned in the wall clock ``tz_minutes`` east of UTC.

    ``None`` when the sun never crosses the horizon there that day (polar day or
    polar night), so callers simply show nothing."""
    n = (day - _EPOCH_DATE).days
    j_star = n - long / 360.0  # mean solar noon, in days since the epoch
    mean_anomaly = (357.5291 + 0.98560028 * j_star) % 360.0
    centre = (1.9148 * _sin(mean_anomaly)
              + 0.0200 * _sin(2 * mean_anomaly)
              + 0.0003 * _sin(3 * mean_anomaly))
    # Ecliptic longitude: mean anomaly + equation of the centre + the perihelion
    # argument (180 + 102.9372).
    ecliptic = (mean_anomaly + centre + 282.9372) % 360.0
    transit = j_star + 0.0053 * _sin(mean_anomaly) - 0.0069 * _sin(2 * ecliptic)
    declination = math.degrees(math.asin(_sin(ecliptic) * _sin(_OBLIQUITY)))

    denom = _cos(lat) * _cos(declination)
    if abs(denom) < 1e-12:  # exactly at a pole — no meaningful rise/set
        return None
    cos_hour_angle = (_sin(_HORIZON) - _sin(lat) * _sin(declination)) / denom
    if not -1.0 <= cos_hour_angle <= 1.0:
        return None  # polar day / night
    hour_angle = math.degrees(math.acos(cos_hour_angle)) / 360.0  # in days

    return SunTimes(
        _wall_time(transit - hour_angle, tz_minutes),
        _wall_time(transit + hour_angle, tz_minutes),
    )


def _wall_time(days_since_epoch: float, tz_minutes: int) -> time:
    """A time expressed in days since the epoch → a local clock time. Only the
    clock time is kept: near the poles an event can land on the neighbouring
    calendar day, which the ``HH:MM`` display doesn't distinguish."""
    moment = (_EPOCH_DT + timedelta(days=days_since_epoch)
              + timedelta(minutes=tz_minutes))
    # Round to the displayed minute rather than truncating.
    moment += timedelta(seconds=30)
    return time(moment.hour, moment.minute)
