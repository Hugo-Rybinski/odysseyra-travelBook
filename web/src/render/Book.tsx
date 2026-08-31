import { useCallback, useEffect, useState, type CSSProperties } from "react";
import type { Itinerary } from "../types/resolved";
import { tr, type Lang } from "./format";
import { todayISO, type CollapseView } from "./collapse";
import { AccentContext, paletteVars } from "./palette";
import { MapProviderContext, type MapProvider } from "./nav";
import { ClampProvider } from "./Clamp";
import { Cover } from "./Cover";
import { DayCard } from "./DayCard";
import { ForecastProvider, useActivityForecasts } from "./forecast";
import { TransportList } from "./TransportList";
import { TripMap } from "./TripMap";
import { AccommodationSummary } from "./AccommodationSummary";

// How days/sections open on load: all collapsed, only past collapsed (default),
// only the current one open, or all expanded. Shared with transport/accommodation.
export type DayView = CollapseView;

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
  if (view === "collapse-past") {
    // collapse days dated strictly before today; keep today + future (and any
    // undated day) open
    const today = todayISO();
    return new Set(itinerary.days.filter((d) => d.date && d.date < today).map((d) => d.day_number));
  }
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
  daysView = "collapse-past",
  transportView = "collapse-past",
  accommodationView = "collapse-past",
  mapProvider = "google",
  show = "travel",
  showForecast = true,
  onJumpDay,
  jumpTo = null,
  onJumped,
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
  // Which transport / accommodation cards start open (same options as days).
  transportView?: DayView;
  accommodationView?: DayView;
  // Which mapping app the "Navigate" links open.
  mapProvider?: MapProvider;
  // Which section this render shows: the trip itself (cover + days), the
  // overview (cover + whole-trip map), or one of the transport / accommodation
  // summaries — each its own page in the app.
  show?: "travel" | "overview" | "transport" | "accommodations";
  // Fetch and show a weather forecast per activity (near-term days only). Only
  // meaningful for the travel view; networked and opt-in.
  showForecast?: boolean;
  // Overview mode: where a day-by-day row click goes. The days aren't rendered
  // here, so the app switches to the travel view and hands the day back via
  // `jumpTo` (below) instead of scrolling in place.
  onJumpDay?: (dayNumber: number) => void;
  // Travel mode: a day to expand and scroll to on arrival (from the Overview
  // tab). `onJumped` fires once it's been handled, so the app can clear it.
  jumpTo?: number | null;
  onJumped?: () => void;
}) {
  const style = paletteVars(itinerary.cover_color) as CSSProperties;
  const [collapsed, setCollapsed] = useState<Set<number>>(() => collapsedFor(daysView, itinerary));
  // Called unconditionally (before the early returns below) to keep hook order
  // stable; disabled for the transport/accommodation views so they do no work.
  const forecasts = useActivityForecasts(itinerary.days, showForecast && show === "travel");

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

  // Land on the day the Overview tab asked for, once the days are on screen.
  useEffect(() => {
    if (jumpTo == null || show !== "travel") return;
    jump(jumpTo);
    onJumped?.();
  }, [jumpTo, show, jump, onJumped]);

  if (show === "overview") {
    return (
      <AccentContext.Provider value={itinerary.cover_color}>
      <MapProviderContext.Provider value={mapProvider}>
        <ClampProvider value={clampDescriptions}>
          <div className="book" style={style}>
            <Cover
              itinerary={itinerary}
              lang={lang}
              onJump={onJumpDay ?? jump}
              startOverviewOpen
            />
            <TripMap itinerary={itinerary} lang={lang} />
          </div>
        </ClampProvider>
      </MapProviderContext.Provider>
      </AccentContext.Provider>
    );
  }

  if (show === "transport") {
    const empty = !itinerary.transports.length && !itinerary.car_rentals.length;
    return (
      <AccentContext.Provider value={itinerary.cover_color}>
      <MapProviderContext.Provider value={mapProvider}>
        {/* ClampProvider reaches here too since the cards carry prose of their
            own now (a leg's / rental's `description`) — without it these notes
            would ignore the app's "show full descriptions" option. */}
        <ClampProvider value={clampDescriptions}>
          <div className="book" style={style}>
            {empty ? (
              <p className="section-empty">{tr(lang, "noTransport")}</p>
            ) : (
              <TransportList itinerary={itinerary} lang={lang} view={transportView} />
            )}
          </div>
        </ClampProvider>
      </MapProviderContext.Provider>
      </AccentContext.Provider>
    );
  }

  if (show === "accommodations") {
    return (
      <AccentContext.Provider value={itinerary.cover_color}>
      <MapProviderContext.Provider value={mapProvider}>
        <ClampProvider value={clampDescriptions}>
          <div className="book" style={style}>
            {itinerary.accommodations.length ? (
              <AccommodationSummary itinerary={itinerary} lang={lang} view={accommodationView} />
            ) : (
              <p className="section-empty">{tr(lang, "noAccommodation")}</p>
            )}
          </div>
        </ClampProvider>
      </MapProviderContext.Provider>
      </AccentContext.Provider>
    );
  }

  return (
    <AccentContext.Provider value={itinerary.cover_color}>
    <MapProviderContext.Provider value={mapProvider}>
    <ClampProvider value={clampDescriptions}>
    <ForecastProvider value={forecasts}>
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
    </div>
    </ForecastProvider>
    </ClampProvider>
    </MapProviderContext.Provider>
    </AccentContext.Provider>
  );
}
