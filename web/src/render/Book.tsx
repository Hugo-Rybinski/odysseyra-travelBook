import { useCallback, useState, type CSSProperties } from "react";
import type { Itinerary } from "../types/resolved";
import type { Lang } from "./format";
import { paletteVars } from "./palette";
import { Cover } from "./Cover";
import { DayCard } from "./DayCard";
import { TransportList } from "./TransportList";
import { AccommodationSummary } from "./AccommodationSummary";

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
}: {
  itinerary: Itinerary;
  lang: Lang;
  interactiveMaps?: boolean;
  // When false, days without a rendered map show nothing instead of a loader —
  // used after a plain Apply, whose maps are carried over rather than rebuilt.
  showMapLoaders?: boolean;
}) {
  const style = paletteVars(itinerary.cover_color) as CSSProperties;
  const [collapsed, setCollapsed] = useState<Set<number>>(() => new Set());

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
  );
}
