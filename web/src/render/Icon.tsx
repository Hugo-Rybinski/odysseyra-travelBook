// The viewer's line icons, drawn on the blog's grammar (DESIGN.md → Shapes):
// 24-unit line drawings, 1.75 stroke, round caps and joins, in currentColor, so
// an icon takes the ink of whatever it sits in. They replace the emoji and the
// ▸/▾/☰ glyphs the chrome used to borrow from the font, which rendered in a
// different weight on every platform.
import type { ReactNode } from "react";

export type IconName =
  | "menu"
  | "chevron"
  | "plane"
  | "train"
  | "bus"
  | "taxi"
  | "ferry"
  | "transit"
  | "car"
  | "hotel"
  | "tent"
  | "house"
  | "bed"
  | "sun"
  | "partly"
  | "cloud"
  | "fog"
  | "rain"
  | "snow"
  | "storm"
  | "thermo"
  | "error"
  | "warning"
  | "info"
  | "compass"
  | "map"
  | "search"
  | "pencil"
  | "book"
  | "prompt"
  | "gear"
  | "refresh"
  | "plus"
  | "folder"
  | "play";

const SUN_RAYS = "M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4";
const CLOUD = "M7 18h10a4 4 0 0 0 .6-7.95A5.5 5.5 0 0 0 7.1 9.1 4.5 4.5 0 0 0 7 18z";

const PATHS: Record<IconName, ReactNode> = {
  menu: (
    <>
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </>
  ),
  // Points right; `.icon-chevron.open` turns it down.
  chevron: <path d="M9 5l7 7-7 7" />,
  plane: (
    <path d="M10.5 3.5c.5-1 2.5-1 3 0l.5 6.5 7 4v2l-7-2-.5 4.5 2.5 2v1.5l-4-1-4 1V20.5l2.5-2L10 14l-7 2v-2l7-4z" />
  ),
  train: (
    <>
      <rect x="6" y="3" width="12" height="14" />
      <path d="M6 11h12" />
      <path d="M9 14h.01" />
      <path d="M15 14h.01" />
      <path d="M8.5 17L6 21" />
      <path d="M15.5 17L18 21" />
    </>
  ),
  bus: (
    <>
      <rect x="4" y="4" width="16" height="13" />
      <path d="M4 11h16" />
      <path d="M7.5 14h.01" />
      <path d="M16.5 14h.01" />
      <path d="M6.5 17v3" />
      <path d="M17.5 17v3" />
    </>
  ),
  taxi: (
    <>
      <path d="M3 16v-4l2.5-5h13l2.5 5v4z" />
      <path d="M3 12h18" />
      <path d="M10 4h4v3" />
      <circle cx="7.5" cy="17.5" r="1.5" />
      <circle cx="16.5" cy="17.5" r="1.5" />
    </>
  ),
  ferry: (
    <>
      <path d="M3 14l2.5 5h13L21 14z" />
      <path d="M6 14v-4h12v4" />
      <path d="M10 10V6h4v4" />
      <path d="M2 21.5c2 0 2-1 4-1s2 1 4 1 2-1 4-1 2 1 4 1 2-1 4-1" />
    </>
  ),
  transit: (
    <>
      <path d="M4 8h13" />
      <path d="M14 5l3 3-3 3" />
      <path d="M20 16H7" />
      <path d="M10 13l-3 3 3 3" />
    </>
  ),
  car: (
    <>
      <path d="M3 16v-4l2.5-5h13l2.5 5v4z" />
      <path d="M3 12h18" />
      <circle cx="7.5" cy="17.5" r="1.5" />
      <circle cx="16.5" cy="17.5" r="1.5" />
    </>
  ),
  hotel: (
    <>
      <path d="M5 21V3h14v18" />
      <path d="M3 21h18" />
      <path d="M9 7h.01M15 7h.01M9 11h.01M15 11h.01M9 15h.01M15 15h.01" />
      <path d="M10.5 21v-3h3v3" />
    </>
  ),
  tent: (
    <>
      <path d="M12 4L3 20h18z" />
      <path d="M12 12l-3 8" />
      <path d="M12 12l3 8" />
      <path d="M10 4l2 0" />
    </>
  ),
  house: (
    <>
      <path d="M3 11l9-7 9 7" />
      <path d="M5 9.5V20h14V9.5" />
      <path d="M10 20v-5h4v5" />
    </>
  ),
  bed: (
    <>
      <path d="M3 19V6" />
      <path d="M3 15h18v4" />
      <path d="M3 11h18v4" />
      <path d="M7 11V8.5h4V11" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d={SUN_RAYS} />
    </>
  ),
  partly: (
    <>
      <path d="M8 3.5v1.5M3.5 8H5M4.8 4.8l1 1M11.2 4.8l-1 1" />
      <path d="M5.6 10.4A3 3 0 0 1 10.6 6.7" />
      <path d="M9 20h8a3.5 3.5 0 0 0 .5-6.96A4.8 4.8 0 0 0 8.4 12.3 3.9 3.9 0 0 0 9 20z" />
    </>
  ),
  cloud: <path d={CLOUD} />,
  fog: (
    <>
      <path d="M7 13h10a4 4 0 0 0 .6-7.95A5.5 5.5 0 0 0 7.1 4.1 4.5 4.5 0 0 0 7 13z" />
      <path d="M4 17h16M6 21h12" />
    </>
  ),
  rain: (
    <>
      <path d="M7 14h10a4 4 0 0 0 .6-7.95A5.5 5.5 0 0 0 7.1 5.1 4.5 4.5 0 0 0 7 14z" />
      <path d="M8 17l-1 3M12 17l-1 3M16 17l-1 3" />
    </>
  ),
  snow: (
    <>
      <path d="M7 14h10a4 4 0 0 0 .6-7.95A5.5 5.5 0 0 0 7.1 5.1 4.5 4.5 0 0 0 7 14z" />
      <path d="M8 18h.01M12 20h.01M16 18h.01M10 21.5h.01M14 21.5h.01" />
    </>
  ),
  storm: (
    <>
      <path d="M7 14h10a4 4 0 0 0 .6-7.95A5.5 5.5 0 0 0 7.1 5.1 4.5 4.5 0 0 0 7 14z" />
      <path d="M12.5 14l-2 4h3l-2 4" />
    </>
  ),
  thermo: (
    <>
      <path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a3.5 3.5 0 1 1-4 0z" />
      <path d="M12 9v7" />
    </>
  ),
  error: (
    <>
      <rect x="3.5" y="3.5" width="17" height="17" />
      <path d="M9 9l6 6M15 9l-6 6" />
    </>
  ),
  warning: (
    <>
      <path d="M12 3.5l9.5 16.5h-19z" />
      <path d="M12 10v4.5M12 17.5h.01" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5.5M12 7.8h.01" />
    </>
  ),
  compass: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M15.5 8.5l-2 5-5 2 2-5z" />
    </>
  ),
  map: (
    <>
      <path d="M3 6l6-2.5 6 2.5 6-2.5v14.5l-6 2.5-6-2.5-6 2.5z" />
      <path d="M9 3.5V18M15 6v14.5" />
    </>
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="M15 15l5.5 5.5" />
    </>
  ),
  pencil: (
    <>
      <path d="M4 20l1-4.5L15.5 5a2.1 2.1 0 0 1 3 3L8 18.5z" />
      <path d="M13.5 7l3 3" />
    </>
  ),
  book: (
    <>
      <path d="M4 5.5C6.5 4 9.5 4 12 5.5 14.5 4 17.5 4 20 5.5V19c-2.5-1.5-5.5-1.5-8 0-2.5-1.5-5.5-1.5-8 0z" />
      <path d="M12 5.5V19" />
    </>
  ),
  prompt: (
    <>
      <path d="M4 5h16v11H10l-4.5 3.5V16H4z" />
      <path d="M8 9.5h8M8 12.5h5" />
    </>
  ),
  gear: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8" />
      <circle cx="12" cy="12" r="6.5" />
    </>
  ),
  refresh: (
    <>
      <path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3" />
      <path d="M19.5 4v4h-4" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  folder: <path d="M3 6.5h6l2 2h10V19H3z" />,
  play: <path d="M7 4.5v15l12-7.5z" />,
};

/** A label's leading emoji (and the space after it), for the strings whose
 * translations carry one (`"🧭 Travel"`): the chrome draws a line icon in its
 * place, and the string itself stays the i18n key it always was. */
export function stripEmoji(label: string): string {
  return label
    .replace(/^(?:[\p{Extended_Pictographic}\u2190-\u21FF\u25A0-\u25FF\u2795\u{1F1E6}-\u{1F1FF}]\uFE0F?\u200D?)+\s*/u, "")
    .replace(/\s*\p{Extended_Pictographic}\uFE0F?$/u, "");
}

// The eight phases `models/moon.py` names, as the lit fraction and which side
// is lit — enough to draw the disc instead of borrowing an emoji.
const MOON_PHASE: Record<string, { k: number; waxing: boolean }> = {
  moonNew: { k: 0, waxing: true },
  moonWaxingCrescent: { k: 0.25, waxing: true },
  moonFirstQuarter: { k: 0.5, waxing: true },
  moonWaxingGibbous: { k: 0.75, waxing: true },
  moonFull: { k: 1, waxing: true },
  moonWaningGibbous: { k: 0.75, waxing: false },
  moonLastQuarter: { k: 0.5, waxing: false },
  moonWaningCrescent: { k: 0.25, waxing: false },
};

/** The night's moon as a drawn disc: an ink ring with its lit part filled in
 * ink, the terminator an ellipse. `phaseKey` is the resolved `day.moon.key`. */
export function MoonIcon({ phaseKey, size = 16, label }: { phaseKey: string; size?: number; label?: string }) {
  const phase = MOON_PHASE[phaseKey] ?? MOON_PHASE.moonFull;
  const r = 8;
  const rx = Math.abs(1 - 2 * phase.k) * r;
  // right half from top to bottom, then back along the terminator: through the
  // right side for a crescent (sweep 0), the left for a gibbous (sweep 1)
  const sweep = phase.k > 0.5 ? 1 : 0;
  const lit =
    phase.k <= 0
      ? null
      : phase.k >= 1
        ? <circle cx="12" cy="12" r={r} fill="currentColor" stroke="none" />
        : (
            <path
              d={`M12 ${12 - r}A${r} ${r} 0 0 1 12 ${12 + r}A${rx} ${r} 0 0 ${sweep} 12 ${12 - r}Z`}
              fill="currentColor"
              stroke="none"
              transform={phase.waxing ? undefined : "matrix(-1 0 0 1 24 0)"}
            />
          );
  return (
    <svg
      className="icon icon-moon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      {lit}
      <circle cx="12" cy="12" r={r} />
    </svg>
  );
}

export function Icon({
  name,
  size = 18,
  className,
  label,
}: {
  name: IconName;
  size?: number;
  className?: string;
  // An accessible name when the icon stands alone; decorative otherwise.
  label?: string;
}) {
  return (
    <svg
      className={["icon", `icon-${name}`, className].filter(Boolean).join(" ")}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}

/** The disclosure caret every collapsible row uses (day strips, cards, the
 * past-days fold): one chevron, turned down when its row is open. */
export function Caret({ open, className }: { open: boolean; className?: string }) {
  return <Icon name="chevron" size={16} className={[open ? "open" : "", className].filter(Boolean).join(" ")} />;
}

// The night's stay pin, drawn: the ★ glyph sits off-centre in its disc
// (wherever the platform's fallback font puts it), so the star is a polygon,
// its bounding box centred on the disc. Five points, the top one up.
const STAR_POINTS = "12.00,3.85 14.17,9.86 20.56,10.07 15.52,13.99 17.29,20.13 12.00,16.55 6.71,20.13 8.48,13.99 3.44,10.07 9.83,9.86";
const STAY_PIN = "★";

/** A map pin's label as drawn inside its disc — a number or letter trimmed to
 * its cap height (so it sits on the disc's centre rather than on the font's
 * line box), or the stay's star. Shared by the itinerary's discs and the map's
 * markers so the two always agree. */
export function PinLabel({ label }: { label: string }) {
  if (label === STAY_PIN)
    return (
      <svg className="pin-star" viewBox="0 0 24 24" aria-hidden focusable="false">
        <polygon points={STAR_POINTS} fill="currentColor" />
      </svg>
    );
  return <span className="pin-n">{label}</span>;
}

/** The same, for the DOM markers MapLibre places (no React there). */
export function fillPinLabel(el: HTMLElement, label: string): void {
  if (label === STAY_PIN) {
    el.innerHTML = `<svg class="pin-star" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><polygon points="${STAR_POINTS}" fill="currentColor"/></svg>`;
    el.setAttribute("aria-label", label);
    return;
  }
  const n = document.createElement("span");
  n.className = "pin-n";
  n.textContent = label;
  el.replaceChildren(n);
}
