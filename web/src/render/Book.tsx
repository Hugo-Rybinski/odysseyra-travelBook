import { useCallback, useEffect, useState, type CSSProperties } from "react";
import type { Itinerary } from "../types/resolved";
import type { Lang } from "./format";
import { paletteVars } from "./palette";
import { ClampProvider } from "./Clamp";
import { Cover } from "./Cover";
import { DayCard } from "./DayCard";
import { TransportList } from "./TransportList";
import { AccommodationSummary } from "./AccommodationSummary";

// How days open on load (and when the option changes): all collapsed, only the
// current day open (default), or all expanded.
export type DayView = "collapse-all" | "current-only" | "expand-all";

function todayISO(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// The "current" day: the one dated today; failing that (the trip isn't running
// now) the first day, so "current only" always leaves something open.
function currentDayNumber(itinerary: Itinerary): number | null {
  const days = itinerary.days;
  if (!days.length) return null;
  const today = todayISO();
  return (days.find((d) => d.date === today) ?? days[0]).day_number;
}

function collapsedFor(view: DayView, itinerary: Itinerary): Set<number> {
  if (view === "expand-all") return new Set();
  const all = itinerary.days.map((d) => d.day_number);
  if (view === "collapse-all") return new Set(all);
  const current = currentDayNumber(itinerary);
  return new Set(all.filter((n) => n !== current));
}

// The whole travel book, web-native: cover, one card per day, then the
// transport and accommodation sections. The trip's cover_color drives the
// palette via CSS custom properties scoped to this wrapper.
//
// Days are collapsible (click the header band); the cover's overview rows jump
// to — and expand — their day. Collapsed state lives here so the two cooperate.
export function Book({
  itinerary,
  lang,
  interactiveMaps = false,
  showMapLoaders = true,
  clampDescriptions = true,
  daysView = "current-only",
}: {
  itinerary: Itinerary;
  lang: Lang;
  interactiveMaps?: boolean;
  // When false, days without a rendered map show nothing instead of a loader —
  // used after a plain Apply, whose maps are carried over rather than rebuilt.
  showMapLoaders?: boolean;
  // When true (default), long descriptions truncate to a few lines with a
  // "Show more" toggle; when false they're shown in full.
  clampDescriptions?: boolean;
  // Which days start open (see DayView).
  daysView?: DayView;
}) {
  const style = paletteVars(itinerary.cover_color) as CSSProperties;
  const [collapsed, setCollapsed] = useState<Set<number>>(() => collapsedFor(daysView, itinerary));

  // Re-apply the day-view preset when it changes or a different itinerary loads.
  // Manual per-day toggles (below) live in `collapsed` and persist until then.
  useEffect(() => {
    setCollapsed(collapsedFor(daysView, itinerary));
  }, [daysView, itinerary]);

  const toggle = useCallback((n: number) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(n) ? next.delete(n) : next.add(n);
      return next;
    });
  }, []);

  const jump = useCallback((n: number) => {
    setCollapsed((prev) => {
      if (!prev.has(n)) return prev;
      const next = new Set(prev);
      next.delete(n); // expand the target so the jump lands on its content
      return next;
    });
    requestAnimationFrame(() => {
      document
        .getElementById(`day-${n}`)
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, []);

  return (
    <ClampProvider value={clampDescriptions}>
    <div className="book" style={style}>
      <Cover itinerary={itinerary} lang={lang} onJump={jump} />
      <div className="days">
        {itinerary.days.map((day) => (
          <DayCard
            key={day.day_number}
            day={day}
            lang={lang}
            collapsed={collapsed.has(day.day_number)}
            onToggle={toggle}
            mapExpected={itinerary.maps.include_in_render && showMapLoaders}
            interactive={interactiveMaps}
          />
        ))}
      </div>
      <TransportList itinerary={itinerary} lang={lang} />
      <AccommodationSummary itinerary={itinerary} lang={lang} />
    </div>
    </ClampProvider>
  );
}
