// Weather forecast for the on-screen travel book (viewer-only, opt-in — the PDF
// and the Python model stay deterministic/offline). Forecasts come from
// Open-Meteo (no API key, CORS-friendly); one request covers a whole day's
// hourly series for a coordinate, and we read the hour matching the activity's
// start time. This is the one networked, time-varying thing the viewer renders,
// so every path degrades to "no chip" on error/offline rather than throwing.
//
// Pure logic only (no React) so the planning/dedup pass is easy to reason about
// and test; the React glue lives in render/forecast.tsx.

import type { Activity, ActivityType, Day } from "./types/resolved";

// The single hour we show for an activity: temperature, the WMO weather code
// (mapped to an icon + localized label by `wmo`), and optional precip/wind.
export interface Forecast {
  tempC: number;
  code: number;
  precipProb: number | null; // %
  windKph: number | null;
}

// Only these activity types get a forecast — roads, buffers, transport, car
// rentals and accommodation are excluded (they're movement/logistics, not a
// place you spend time at a known hour).
const FORECAST_TYPES = new Set<ActivityType>([
  "point_of_interest",
  "place",
  "hike",
  "meal",
]);

// A forecast is only shown for days within this many days of today (Open-Meteo's
// forecast horizon is longer, but a near-term window is all that's meaningful).
const WINDOW_DAYS = 7;
// Two activities close in space *and* time share one forecast (no second fetch).
const NEARBY_KM = 50;
const NEARBY_MIN = 120;

// -- geo / time helpers ------------------------------------------------------

function toRad(d: number): number {
  return (d * Math.PI) / 180;
}

/** Great-circle distance in km between two lat/long points. */
export function haversineKm(
  aLat: number,
  aLong: number,
  bLat: number,
  bLong: number,
): number {
  const R = 6371;
  const dLat = toRad(bLat - aLat);
  const dLon = toRad(bLong - aLong);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}

function epochDay(iso: string): number {
  return Math.floor(Date.parse(`${iso}T00:00:00Z`) / 86_400_000);
}

function hhmmToMin(s: string): number | null {
  const m = /^(\d{1,2}):(\d{2})/.exec(s);
  if (!m) return null;
  return Number(m[1]) * 60 + Number(m[2]);
}

// -- WMO weather codes -------------------------------------------------------

// Map an Open-Meteo WMO code to a display glyph + a format.ts label key. Ranges
// per the WMO table Open-Meteo documents (0 clear … 45 fog … 61 rain … 71 snow
// … 95 thunderstorm). `key` is cast to a LabelKey where it's translated.
export function wmo(code: number): { emoji: string; key: string } {
  if (code <= 0) return { emoji: "☀️", key: "wxClear" };
  if (code === 1) return { emoji: "🌤️", key: "wxMainlyClear" };
  if (code === 2) return { emoji: "⛅", key: "wxPartlyCloudy" };
  if (code === 3) return { emoji: "☁️", key: "wxOvercast" };
  if (code === 45 || code === 48) return { emoji: "🌫️", key: "wxFog" };
  if (code >= 51 && code <= 57) return { emoji: "🌦️", key: "wxDrizzle" };
  if (code >= 61 && code <= 67) return { emoji: "🌧️", key: "wxRain" };
  if (code >= 71 && code <= 77) return { emoji: "🌨️", key: "wxSnow" };
  if (code >= 80 && code <= 82) return { emoji: "🌦️", key: "wxRainShowers" };
  if (code === 85 || code === 86) return { emoji: "🌨️", key: "wxSnowShowers" };
  if (code >= 95) return { emoji: "⛈️", key: "wxThunder" };
  return { emoji: "🌡️", key: "wxUnknown" };
}

// -- planning (which activities fetch, which reuse) --------------------------

export interface PlannedFetch {
  act: Activity;
  lat: number;
  long: number;
  date: string;
  hour: number; // 0..23, the activity's start rounded to the nearest hour
}

export interface ForecastPlan {
  // Activities that trigger a network request.
  fetches: PlannedFetch[];
  // Activities that reuse another (already-forecast) activity's result instead
  // of fetching: dependent activity → the leader whose forecast it borrows.
  reuse: Map<Activity, Activity>;
}

/**
 * Decide, for every forecast-eligible activity in the next {@link WINDOW_DAYS}
 * days, whether it fetches its own forecast or reuses a nearby earlier one.
 *
 * An activity reuses an earlier activity's forecast (and skips its own fetch)
 * when that earlier activity already has a forecast, sits within
 * {@link NEARBY_KM} km, and started under {@link NEARBY_MIN} minutes before it.
 * Reuse chains: C can borrow A's forecast by matching B, which itself borrowed
 * A — so a run of clustered stops costs a single request.
 *
 * `today` is injected (ISO "YYYY-MM-DD") so the pass is pure and testable.
 */
export function planForecasts(days: Day[], today: string): ForecastPlan {
  const t0 = epochDay(today);
  const cands: {
    act: Activity;
    lat: number;
    long: number;
    date: string;
    hour: number;
    absMin: number;
  }[] = [];

  for (const day of days) {
    if (!day.date) continue;
    const diff = epochDay(day.date) - t0;
    if (diff < 0 || diff > WINDOW_DAYS) continue;
    for (const act of day.activities) {
      if (!FORECAST_TYPES.has(act.type)) continue;
      const c = act.coordinate;
      if (!c) continue; // no coordinate → nothing to look up
      if (!act.start_time) continue;
      const min = hhmmToMin(act.start_time);
      if (min == null) continue;
      cands.push({
        act,
        lat: c.lat,
        long: c.long,
        date: day.date,
        hour: Math.min(23, Math.max(0, Math.round(min / 60))),
        absMin: epochDay(day.date) * 1440 + min,
      });
    }
  }

  // Chronological order so "started before" is just "earlier in the list".
  cands.sort((a, b) => a.absMin - b.absMin);

  const fetches: PlannedFetch[] = [];
  const reuse = new Map<Activity, Activity>();
  // Every activity we've decided, with the fetched leader that supplies its data.
  const processed: { lat: number; long: number; absMin: number; leader: Activity }[] = [];

  for (const cur of cands) {
    let leader: Activity | null = null;
    for (let i = processed.length - 1; i >= 0; i--) {
      const p = processed[i];
      const dt = cur.absMin - p.absMin; // ≥ 0 (sorted); grows as we go back
      if (dt >= NEARBY_MIN) break; // everything earlier is even further in time
      if (haversineKm(p.lat, p.long, cur.lat, cur.long) < NEARBY_KM) {
        leader = p.leader;
        break;
      }
    }
    if (leader) {
      reuse.set(cur.act, leader);
      processed.push({ lat: cur.lat, long: cur.long, absMin: cur.absMin, leader });
    } else {
      fetches.push({ act: cur.act, lat: cur.lat, long: cur.long, date: cur.date, hour: cur.hour });
      processed.push({ lat: cur.lat, long: cur.long, absMin: cur.absMin, leader: cur.act });
    }
  }

  return { fetches, reuse };
}

// -- network -----------------------------------------------------------------

interface HourlyDay {
  temperature_2m: number[];
  weather_code: number[];
  precipitation_probability?: (number | null)[];
  wind_speed_10m?: number[];
}

// One in-flight/settled request per (coordinate, date), so two activities that
// end up fetching the same day+place hit the network once. Coordinates are
// rounded (~1 km) for the key. A failed request is evicted so it can retry.
const dayCache = new Map<string, Promise<HourlyDay | null>>();

/** Fetch a day's hourly series for a coordinate (memoized). Null on any error. */
export function fetchDayForecast(
  lat: number,
  long: number,
  date: string,
): Promise<HourlyDay | null> {
  const key = `${lat.toFixed(2)},${long.toFixed(2)},${date}`;
  const hit = dayCache.get(key);
  if (hit) return hit;
  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${long}` +
    `&hourly=temperature_2m,weather_code,precipitation_probability,wind_speed_10m` +
    `&start_date=${date}&end_date=${date}&timezone=auto`;
  const p = fetch(url)
    .then(async (r) => {
      if (!r.ok) throw new Error(`weather ${r.status}`);
      const j = await r.json();
      const h = j?.hourly;
      return h?.temperature_2m ? (h as HourlyDay) : null;
    })
    .catch(() => {
      dayCache.delete(key); // let a later view retry
      return null;
    });
  dayCache.set(key, p);
  return p;
}

/** Read the forecast at `hour` (0..23) out of a fetched day, or null. */
export function pickHour(day: HourlyDay, hour: number): Forecast | null {
  const i = Math.min(Math.max(hour, 0), day.temperature_2m.length - 1);
  const temp = day.temperature_2m[i];
  if (temp == null || Number.isNaN(temp)) return null;
  const wind = day.wind_speed_10m?.[i];
  return {
    tempC: Math.round(temp),
    code: day.weather_code[i] ?? 0,
    precipProb: day.precipitation_probability?.[i] ?? null,
    windKph: wind != null ? Math.round(wind) : null,
  };
}
