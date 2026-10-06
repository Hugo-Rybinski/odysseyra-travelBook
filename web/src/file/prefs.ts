// The viewer's Options choices (language, display, maps, PDF ink-saver), kept
// across launches.
//
// In `localStorage` rather than IndexedDB because the first render needs them:
// it is synchronous, so the app opens in the chosen language instead of
// painting English and switching a frame later (and the launch render cache's
// `painted.lang === lang` check would otherwise fail on every French launch).
//
// The record is dropped — every option back to its default — when:
//  - it was written by another build (`RENDER_BUILD`: commit + `SCHEMA_VERSION`),
//    the same rule as the launch render cache, so a deploy that renames or
//    reshapes an option can't be fed a stale value;
//  - it was last changed more than `PREFS_TTL_MS` (30 days) ago.
// Values are also checked one by one on read, so a malformed entry falls back
// to its default rather than reaching the UI.
//
// Per-file choices are deliberately not here: the PDF's *Include maps* toggle
// follows the opened file's `include_maps_in_render`.

import type { Lang } from "../render/format";
import type { CollapseView as DayView } from "../render/collapse";
import type { MapProvider } from "../render/nav";
import { MAP_PROVIDERS } from "../render/nav";
import { RENDER_BUILD } from "./renderCache";

export interface Prefs {
  lang: Lang;
  interactiveMaps: boolean;
  clampDescriptions: boolean;
  showForecast: boolean;
  daysView: DayView;
  transportView: DayView;
  accommodationView: DayView;
  mapProvider: MapProvider;
  inkSaver: boolean;
}

export const DEFAULT_PREFS: Prefs = {
  lang: "en",
  interactiveMaps: true,
  clampDescriptions: true,
  showForecast: true,
  daysView: "collapse-past",
  transportView: "collapse-past",
  accommodationView: "collapse-past",
  mapProvider: "google",
  inkSaver: false,
};

export const PREFS_TTL_MS = 30 * 24 * 60 * 60 * 1000;

const KEY = "odysseyra-prefs";
const VIEWS: readonly string[] = ["collapse-past", "collapse-all", "current-only", "expand-all"];

interface PrefsRecord {
  build: string;
  at: number; // epoch ms of the last change
  prefs: Partial<Prefs>;
}

function clean(raw: Partial<Prefs>): Prefs {
  const out = { ...DEFAULT_PREFS };
  const bool = (k: "interactiveMaps" | "clampDescriptions" | "showForecast" | "inkSaver") => {
    if (typeof raw[k] === "boolean") out[k] = raw[k] as boolean;
  };
  bool("interactiveMaps");
  bool("clampDescriptions");
  bool("showForecast");
  bool("inkSaver");
  if (raw.lang === "en" || raw.lang === "fr") out.lang = raw.lang;
  for (const k of ["daysView", "transportView", "accommodationView"] as const) {
    if (typeof raw[k] === "string" && VIEWS.includes(raw[k] as string)) out[k] = raw[k] as DayView;
  }
  if (MAP_PROVIDERS.some((p) => p.id === raw.mapProvider)) out.mapProvider = raw.mapProvider as MapProvider;
  return out;
}

/** The stored options, or the defaults when there are none, they're stale, or
 *  storage is unavailable (a private window, blocked site data). */
export function loadPrefs(now = Date.now()): Prefs {
  try {
    const text = localStorage.getItem(KEY);
    if (!text) return { ...DEFAULT_PREFS };
    const rec = JSON.parse(text) as PrefsRecord;
    if (
      !rec ||
      rec.build !== RENDER_BUILD ||
      typeof rec.at !== "number" ||
      now - rec.at > PREFS_TTL_MS ||
      typeof rec.prefs !== "object"
    ) {
      localStorage.removeItem(KEY);
      return { ...DEFAULT_PREFS };
    }
    return clean(rec.prefs ?? {});
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

/** Store the options (best-effort: losing them costs a reset to defaults). */
export function savePrefs(prefs: Prefs, now = Date.now()): void {
  try {
    const rec: PrefsRecord = { build: RENDER_BUILD, at: now, prefs };
    localStorage.setItem(KEY, JSON.stringify(rec));
  } catch {
    /* best-effort */
  }
}
