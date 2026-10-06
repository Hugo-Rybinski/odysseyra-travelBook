// React glue for the weather forecast (see ../weather.ts for the pure logic):
// a context carrying the resolved per-activity forecasts, the hook that plans +
// fetches them, and the small chip the day timeline shows. Networked and
// opt-in — it never blocks rendering and shows nothing on error/offline.

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { Activity, Day } from "../types/resolved";
import { fill, tr, type Lang, type LabelKey } from "./format";
import { todayISO } from "./collapse";
import {
  bumpForecastGeneration,
  fetchDayForecast,
  pickHour,
  planForecasts,
  wmo,
  type Forecast,
} from "../weather";

// Keyed by the resolved Activity object itself (stable across renders while the
// itinerary is unchanged), so rows look their forecast up by identity — no index
// threading, and nested sub-activities (never planned) simply find nothing.
const ForecastContext = createContext<Map<Activity, Forecast> | null>(null);
export const ForecastProvider = ForecastContext.Provider;

// How often an open page refetches the forecast on its own.
export const FORECAST_REFRESH_MS = 60 * 60 * 1000;

/** Where the forecast stands, for the Options tab. */
export interface ForecastStatus {
  // When the newest forecast on screen was fetched (epoch ms); null before the
  // first success.
  updatedAt: number | null;
  refreshing: boolean;
  // The latest round had a failed request — whatever is shown is the previous
  // forecast for it (or nothing, if it never succeeded).
  failed: boolean;
  // How many requests the trip needs; 0 = nothing in the window to forecast.
  planned: number;
}

const IDLE: ForecastStatus = { updatedAt: null, refreshing: false, failed: false, planned: 0 };

/**
 * Plan and fetch forecasts for the eligible activities in `days`, returning a
 * map from activity → its forecast, the status, and a `refresh` that refetches
 * everything. Empty (and all work skipped) when disabled.
 *
 * Owned by `App` rather than `Book`, so it keeps running — and keeps its
 * timer — while another tab (Options) is on screen. Reruns when the days
 * change (served from the per-generation cache, so no request), on `refresh`,
 * and every {@link FORECAST_REFRESH_MS}; also when the page comes back into
 * view after missing a scheduled refresh (a sleeping phone suspends timers). A
 * failed refresh keeps the previous forecast (see `fetchDayForecast`). A stale
 * run is ignored on unmount or when the inputs change.
 */
export function useActivityForecasts(
  days: Day[],
  enabled: boolean,
): { forecasts: Map<Activity, Forecast>; status: ForecastStatus; refresh: () => void } {
  const [map, setMap] = useState<Map<Activity, Forecast>>(() => new Map());
  const [status, setStatus] = useState<ForecastStatus>(IDLE);
  const [tick, setTick] = useState(0);
  const lastRefresh = useRef(Date.now());

  const refresh = useCallback(() => {
    bumpForecastGeneration();
    lastRefresh.current = Date.now();
    setTick((n) => n + 1);
  }, []);

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(refresh, FORECAST_REFRESH_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible" && Date.now() - lastRefresh.current >= FORECAST_REFRESH_MS) {
        refresh();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [enabled, refresh]);

  useEffect(() => {
    if (!enabled) {
      setMap(new Map());
      setStatus(IDLE);
      return;
    }
    // "Today" is read per run, so the 7-day window moves with the hourly refresh.
    const plan = planForecasts(days, todayISO());
    if (!plan.fetches.length) {
      setMap(new Map());
      setStatus(IDLE);
      return;
    }
    let cancelled = false;
    setStatus((s) => ({ ...s, refreshing: true, planned: plan.fetches.length }));
    (async () => {
      const out = new Map<Activity, Forecast>();
      let newest: number | null = null;
      let failed = false;
      await Promise.all(
        plan.fetches.map(async (f) => {
          const res = await fetchDayForecast(f.lat, f.long, f.date);
          failed ||= res.failed;
          const fc = res.data && pickHour(res.data, f.hour);
          if (!fc) return;
          out.set(f.act, fc);
          if (res.at != null && (newest == null || res.at > newest)) newest = res.at;
        }),
      );
      // Dependents borrow their leader's forecast.
      for (const [dep, leader] of plan.reuse) {
        const fc = out.get(leader);
        if (fc) out.set(dep, fc);
      }
      if (cancelled) return;
      setMap(out);
      setStatus({ updatedAt: newest, refreshing: false, failed, planned: plan.fetches.length });
    })();
    return () => {
      cancelled = true;
    };
  }, [days, enabled, tick]);

  return { forecasts: map, status, refresh };
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
