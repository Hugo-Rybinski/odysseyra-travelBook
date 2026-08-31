// Derive a small display palette from the trip's single `cover_color`, mirroring
// the idea behind the PDF's palette (one accent drives everything). Display-only.

export interface Palette {
  accent: string; // the cover color itself
  accentDark: string; // for hovers / deep bands
  accentLight: string; // de-emphasized accent *text* (mirrors the PDF's _tint(accent, 0.4))
  accentSoft: string; // pale tint for card/band backgrounds
  onAccent: string; // readable text on the accent (white or near-black)
}

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

export function palette(coverColor: string): Palette {
  const [r, g, b] = parseHex(coverColor);
  const accent = toHex(r, g, b);
  const accentDark = toHex(mix(r, 0, 0.2), mix(g, 0, 0.2), mix(b, 0, 0.2));
  // 40% toward white — the same blend pdf/base.py's `_tint(accent, 0.4)` uses for
  // the VIA header and the guidebook line, so both renderers lighten alike.
  const accentLight = toHex(mix(r, 255, 0.4), mix(g, 255, 0.4), mix(b, 255, 0.4));
  const accentSoft = toHex(mix(r, 255, 0.9), mix(g, 255, 0.9), mix(b, 255, 0.9));
  const onAccent = luminance([r, g, b]) > 150 ? "#1a1a1a" : "#ffffff";
  return { accent, accentDark, accentLight, accentSoft, onAccent };
}

/** The palette as CSS custom properties, to spread onto a wrapper's style. */
export function paletteVars(coverColor: string): Record<string, string> {
  const p = palette(coverColor);
  return {
    "--accent": p.accent,
    "--accent-dark": p.accentDark,
    "--accent-light": p.accentLight,
    "--accent-soft": p.accentSoft,
    "--on-accent": p.onAccent,
  };
}
