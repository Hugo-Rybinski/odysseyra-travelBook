import type { CSSProperties } from "react";
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
export function Book({ itinerary, lang }: { itinerary: Itinerary; lang: Lang }) {
  const style = paletteVars(itinerary.cover_color) as CSSProperties;
  return (
    <div className="book" style={style}>
      <Cover itinerary={itinerary} lang={lang} />
      <div className="days">
        {itinerary.days.map((day) => (
          <DayCard key={day.day_number} day={day} lang={lang} />
        ))}
      </div>
      <TransportList itinerary={itinerary} lang={lang} />
      <AccommodationSummary itinerary={itinerary} lang={lang} />
    </div>
  );
}
