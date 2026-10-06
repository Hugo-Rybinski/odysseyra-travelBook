// Derive a small display palette from the trip's single `cover_color`, mirroring
// the idea behind the PDF's palette (one accent drives everything). Display-only.

import { createContext, useContext } from "react";

export interface Palette {
  accent: string; // the cover color itself
  accentDark: string; // for hovers / deep bands
  accentLight: string; // de-emphasized accent *text* (mirrors the PDF's _tint(accent, 0.4))
  accentSoft: string; // pale tint for card/band backgrounds
  onAccent: string; // readable text on the accent (white or near-black)
  accentText: string; // the accent as *text* on the page (the accent itself in light mode)
}

// The dark theme's card colour (index.css `--card` under data-theme="dark"):
// what the soft tint mixes toward instead of white.
const DARK_CARD: [number, number, number] = [0x1c, 0x1f, 0x24];

function parseHex(hex: string): [number, number, number] {
  const m = hex.trim().replace(/^#/, "");
  const full = m.length === 3 ? m.split("").map((c) => c + c).join("") : m;
  const n = parseInt(full.slice(0, 6) || "1f4e5f", 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const toHex = (r: number, g: number, b: number) =>
  "#" + [r, g, b].map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join("");

const mix = (a: number, b: number, t: number) => a + (b - a) * t;

/** Perceived luminance (0–255) to decide black/white text on the accent. */
function luminance([r, g, b]: [number, number, number]): number {
  return 0.299 * r + 0.587 * g + 0.114 * b;
}

export function palette(coverColor: string, dark = false): Palette {
  const [r, g, b] = parseHex(coverColor);
  const accent = toHex(r, g, b);
  const onAccent = luminance([r, g, b]) > 150 ? "#1a1a1a" : "#ffffff";
  if (dark) {
    // A cover colour is picked to read on white — usually deep — so on a dark
    // page its text and tints are lifted toward white, and the soft wash mixes
    // toward the dark card rather than toward white. Fills (bands, badges) keep
    // the accent itself, with `onAccent` text as in light mode.
    const [cr, cg, cb] = DARK_CARD;
    return {
      accent,
      accentDark: toHex(mix(r, 0, 0.2), mix(g, 0, 0.2), mix(b, 0, 0.2)),
      accentLight: toHex(mix(r, 255, 0.35), mix(g, 255, 0.35), mix(b, 255, 0.35)),
      accentSoft: toHex(mix(r, cr, 0.7), mix(g, cg, 0.7), mix(b, cb, 0.7)),
      onAccent,
      accentText: toHex(mix(r, 255, 0.6), mix(g, 255, 0.6), mix(b, 255, 0.6)),
    };
  }
  const accentDark = toHex(mix(r, 0, 0.2), mix(g, 0, 0.2), mix(b, 0, 0.2));
  // 40% toward white — the same blend pdf/base.py's `_tint(accent, 0.4)` uses for
  // the VIA header and the guidebook line, so both renderers lighten alike.
  const accentLight = toHex(mix(r, 255, 0.4), mix(g, 255, 0.4), mix(b, 255, 0.4));
  const accentSoft = toHex(mix(r, 255, 0.9), mix(g, 255, 0.9), mix(b, 255, 0.9));
  return { accent, accentDark, accentLight, accentSoft, onAccent, accentText: accent };
}

/** The palette as CSS custom properties, to spread onto a wrapper's style. */
export function paletteVars(coverColor: string, dark = false): Record<string, string> {
  const p = palette(coverColor, dark);
  return {
    "--accent": p.accent,
    "--accent-dark": p.accentDark,
    "--accent-light": p.accentLight,
    "--accent-soft": p.accentSoft,
    "--on-accent": p.onAccent,
    "--accent-text": p.accentText,
  };
}

// The trip's raw `cover_color`, for the few places that need the accent as a
// *value* rather than as a CSS variable — MapLibre paints its layers from a
// colour string, and a hike's trail map builds its geo client-side (unlike a day
// map, whose geo arrives from Python with the accent already in it).
export const AccentContext = createContext<string>("#1f4e5f");
export const useAccent = (): string => useContext(AccentContext);
