// The viewer's colour theme (Options → Display → Theme). Viewer-only: the PDF is
// paper and stays light whatever the screen does.
//
// `auto` (the default) is light by day and dark by night. "Day" is today's
// sunrise → sunset when the open trip has a day dated today with sun times —
// i.e. where you actually are — and 07:00 → 19:00 otherwise (no file, a trip
// that isn't under way, or `show_sun_times` off). The sun times are the day's
// local wall clock, compared against the device's: a phone abroad is normally
// on local time, which is the case this is for.
//
// The theme is a `data-theme` attribute on <html>; index.css carries the dark
// overrides under `:root[data-theme="dark"]`, and `paletteVars` derives the
// trip's accent tints for the dark surfaces.

import { createContext, useContext, useEffect, useState } from "react";
import type { Day } from "./types/resolved";
import { todayISO } from "./render/collapse";

export type ThemePref = "auto" | "light" | "dark";
export type Theme = "light" | "dark";

export const THEME_PREFS: readonly ThemePref[] = ["auto", "light", "dark"];

// The fallback day, in minutes after midnight.
const DAY_START_MIN = 7 * 60;
const DAY_END_MIN = 19 * 60;
// How often `auto` re-checks the clock while the page is open.
const RECHECK_MS = 60 * 1000;

export interface SunWindow {
  sunrise: string; // "HH:MM"
  sunset: string;
}

function toMin(s: string): number | null {
  const m = /^(\d{1,2}):(\d{2})/.exec(s);
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}

/** Today's sunrise/sunset from the trip, if a day is dated today and has them. */
export function sunForToday(days: readonly Day[] | undefined, today = todayISO()): SunWindow | null {
  const day = days?.find((d) => d.date === today);
  return day?.sun ?? null;
}

/** Is `now` between sunrise and sunset (or 07:00 and 19:00 without them)? */
export function isDaytime(now: Date, sun: SunWindow | null): boolean {
  let start = DAY_START_MIN;
  let end = DAY_END_MIN;
  const rise = sun && toMin(sun.sunrise);
  const set = sun && toMin(sun.sunset);
  // Only a sane window replaces the fallback (polar days come back as null).
  if (rise != null && set != null && rise < set) {
    start = rise;
    end = set;
  }
  const min = now.getHours() * 60 + now.getMinutes();
  return min >= start && min < end;
}

export function resolveTheme(pref: ThemePref, now: Date, sun: SunWindow | null): Theme {
  if (pref === "light" || pref === "dark") return pref;
  return isDaytime(now, sun) ? "light" : "dark";
}

/** Put the theme on <html> (also called before the first paint, from main.tsx). */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}

/**
 * The theme in force for `pref`, applied to the document and kept current: an
 * `auto` theme re-checks the clock every minute and whenever the page comes
 * back into view (a sleeping phone suspends timers), so it flips at sunset
 * without a reload.
 */
export function useTheme(pref: ThemePref, sun: SunWindow | null): Theme {
  const [theme, setTheme] = useState<Theme>(() => resolveTheme(pref, new Date(), sun));
  // Primitive deps, so a fresh `sun` object with the same times re-runs nothing.
  const rise = sun?.sunrise ?? null;
  const set = sun?.sunset ?? null;

  useEffect(() => {
    const window_ = rise && set ? { sunrise: rise, sunset: set } : null;
    const update = () => setTheme(resolveTheme(pref, new Date(), window_));
    update();
    if (pref !== "auto") return;
    const id = setInterval(update, RECHECK_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") update();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [pref, rise, set]);

  useEffect(() => applyTheme(theme), [theme]);
  return theme;
}

// The resolved theme, for the components that compute colours in code (the
// book's palette).
export const ThemeContext = createContext<Theme>("light");
export const useThemeValue = (): Theme => useContext(ThemeContext);
