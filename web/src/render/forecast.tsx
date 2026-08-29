// React glue for the weather forecast (see ../weather.ts for the pure logic):
// a context carrying the resolved per-activity forecasts, the hook that plans +
// fetches them, and the small chip the day timeline shows. Networked and
// opt-in — it never blocks rendering and shows nothing on error/offline.

import { createContext, useContext, useEffect, useState } from "react";
import type { Activity, Day } from "../types/resolved";
import { fill, tr, type Lang, type LabelKey } from "./format";
import { todayISO } from "./collapse";
import { fetchDayForecast, pickHour, planForecasts, wmo, type Forecast } from "../weather";

// Keyed by the resolved Activity object itself (stable across renders while the
// itinerary is unchanged), so rows look their forecast up by identity — no index
// threading, and nested sub-activities (never planned) simply find nothing.
const ForecastContext = createContext<Map<Activity, Forecast> | null>(null);
export const ForecastProvider = ForecastContext.Provider;

/**
 * Plan and fetch forecasts for the eligible activities in `days`, returning a
 * map from activity → its forecast. Empty (and all work skipped) when disabled.
 * Reruns when the itinerary's days change; a stale run is ignored on unmount or
 * when the inputs change.
 */
export function useActivityForecasts(days: Day[], enabled: boolean): Map<Activity, Forecast> {
  const [map, setMap] = useState<Map<Activity, Forecast>>(() => new Map());
  useEffect(() => {
    if (!enabled) {
      setMap(new Map());
      return;
    }
    const plan = planForecasts(days, todayISO());
    if (!plan.fetches.length) {
      setMap(new Map());
      return;
    }
    let cancelled = false;
    (async () => {
      const out = new Map<Activity, Forecast>();
      await Promise.all(
        plan.fetches.map(async (f) => {
          const day = await fetchDayForecast(f.lat, f.long, f.date);
          const fc = day && pickHour(day, f.hour);
          if (fc) out.set(f.act, fc);
        }),
      );
      // Dependents borrow their leader's freshly-fetched forecast.
      for (const [dep, leader] of plan.reuse) {
        const fc = out.get(leader);
        if (fc) out.set(dep, fc);
      }
      if (!cancelled) setMap(out);
    })();
    return () => {
      cancelled = true;
    };
  }, [days, enabled]);
  return map;
}

// A compact chip — icon + temperature — shown inline on an activity's title.
// The condition, precipitation chance and wind sit in the hover/focus bubble.
export function ForecastChip({ act, lang }: { act: Activity; lang: Lang }) {
  const map = useContext(ForecastContext);
  const fc = map?.get(act);
  if (!fc) return null;
  const { emoji, key } = wmo(fc.code);
  const tip = [tr(lang, key as LabelKey), `${fc.tempC}°C`];
  if (fc.precipProb != null) tip.push(fill(tr(lang, "wxPrecip"), { p: fc.precipProb }));
  if (fc.windKph != null) tip.push(fill(tr(lang, "wxWind"), { v: fc.windKph }));
  // Show the rain chance in the badge itself once it's worth noting (>5%).
  const precip = fc.precipProb != null && fc.precipProb > 5 ? fc.precipProb : null;
  return (
    <span className="wx-chip" data-tip={tip.join(" · ")}>
      {emoji} {fc.tempC}°
      {precip != null && (
        <span className="wx-precip">{fill(tr(lang, "wxPrecip"), { p: precip })}</span>
      )}
    </span>
  );
}
