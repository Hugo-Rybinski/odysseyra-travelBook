import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import type { Activity, Itinerary } from "../types/resolved";
import type { Forecast } from "../weather";
import { tr, type Lang } from "./format";
import {
  allItemsPast,
  collapsedForItems,
  foldedForItems,
  type CollapseView,
  type DateSpan,
} from "./collapse";
import { AccentContext, paletteVars } from "./palette";
import { MapProviderContext, type MapProvider } from "./nav";
import { ClampProvider } from "./Clamp";
import { Cover } from "./Cover";
import { DayCard } from "./DayCard";
import { EmergencyContacts } from "./EmergencyContacts";
import { ForecastProvider } from "./forecast";
import { PastFold, usePastFold } from "./Parts";
import { TransportList } from "./TransportList";
import { TripMap } from "./TripMap";
import { AccommodationSummary } from "./AccommodationSummary";

// How days/sections open on load: all collapsed, only past collapsed (default),
// only the current one open, or all expanded. Shared with transport/accommodation.
export type DayView = CollapseView;

const NO_FORECASTS = new Map<Activity, Forecast>();

// A day as a date span, so the day list answers to the same three rules as the
// transport / accommodation card lists (`collapse.ts`). A day is one date, so
// its span opens and closes on it — which makes `current-only`'s
// "span covers today" the day-dated-today it always was.
function daySpans(itinerary: Itinerary): DateSpan[] {
  return itinerary.days.map((d) => ({ start: d.date, end: d.date }));
}

// Indices → day numbers: everything outside this module addresses a day by its
// `day_number` (the cover's rows jump by it, `#day-N` is its element), while the
// shared collapse rules work on list positions.
function dayNumbers(itinerary: Itinerary, idx: Set<number>): Set<number> {
  return new Set([...idx].map((i) => itinerary.days[i].day_number));
}

function collapsedFor(view: DayView, itinerary: Itinerary): Set<number> {
  return dayNumbers(itinerary, collapsedForItems(view, daySpans(itinerary)));
}

// The past days this view folds away entirely (see `usePastFold` below), rather
// than opening on a stack of collapsed bands for days already travelled. The
// rule — and the reason it is `past ∩ collapsed` rather than the past days
// outright — lives in `collapse.ts`'s `foldedForItems`, shared with the three
// card lists.
function foldedDayNumbers(view: DayView, itinerary: Itinerary): Set<number> {
  return dayNumbers(itinerary, foldedForItems(view, daySpans(itinerary)));
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
  forecasts = NO_FORECASTS,
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
  // The per-activity weather forecasts to show on the day timeline (travel view
  // only). Fetched by App's `useActivityForecasts`, not here, so the hourly
  // refresh keeps running while another tab is on screen.
  forecasts?: Map<Activity, Forecast>;
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

  // Which days are folded away, and whether they're on screen at all. A past
  // day used to stay as a header band you could expand — so a trip halfway
  // through opened on a stack of rows for days already travelled, and the day
  // you actually want was below them. They are now folded away entirely, behind
  // one line that shows or hides the lot. This applies to **every view that
  // collapses that day** (`collapse-past`, `collapse-all`, `current-only`), not
  // only `collapse-past`: a row you have to scroll past to reach today costs
  // the same wherever the preset that drew it came from. `expand-all` is the
  // one that keeps them, having been asked for everything.
  //
  // The state — including the trip whose *every* day is past, which opens with
  // the run revealed — is `usePastFold`, shared with the three card lists.
  const past = useMemo(() => foldedDayNumbers(daysView, itinerary), [daysView, itinerary]);
  const allPast = useMemo(() => allItemsPast(daySpans(itinerary)), [itinerary]);
  const fold = usePastFold(past, allPast);

  // Re-apply the day-view preset when it changes or a different itinerary loads.
  // Manual per-day toggles (below) live in `collapsed` and persist until then
  // (as does a manual reveal of the past days — `usePastFold` re-folds on the
  // same two signals).
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
    // A folded-away past day has no element to scroll to, so reveal the run
    // first — the cover's overview and the Overview tab both jump by day
    // number and neither knows what's on screen.
    if (past.has(n)) fold.reveal();
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
  }, [past]);

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
            {/* The trip's emergency contacts close the overview — the same list
                the PDF puts on its last page. A no-op when none are given. */}
            <EmergencyContacts itinerary={itinerary} lang={lang} />
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
        {/* The past days' one line, in place of their bands. It sits at the top
            of the list, where those days are — they're the start of the trip. */}
        <PastFold
          n={past.size}
          shown={fold.shown}
          onToggle={fold.toggle}
          lang={lang}
          showKey="showPastDays"
          hideKey="hidePastDays"
        />
        {itinerary.days.map((day) =>
          fold.hidden(day.day_number) ? null : (
            <DayCard
              key={day.day_number}
              day={day}
              lang={lang}
              collapsed={collapsed.has(day.day_number)}
              onToggle={toggle}
              mapExpected={itinerary.maps.include_in_render && showMapLoaders}
              interactive={interactiveMaps}
            />
          ),
        )}
      </div>
    </div>
    </ForecastProvider>
    </ClampProvider>
    </MapProviderContext.Provider>
    </AccentContext.Provider>
  );
}
