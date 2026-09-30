import { useEffect, useMemo, useState } from "react";
import type { Accommodation, Itinerary } from "../types/resolved";
import { fill, fmtDate, tr, type Lang } from "./format";
import {
  allItemsPast,
  collapsedForItems,
  foldedForItems,
  type CollapseView,
  type DateSpan,
} from "./collapse";
import { CardHead, PastFold, Price, Status, usePastFold } from "./Parts";
import { Clamp } from "./Clamp";
import { AddressLink, Links, NavLink } from "./Links";
import { navUrl, useMapProvider } from "./nav";

const TYPE_ICON: Record<string, string> = {
  hotel: "🏨",
  camping: "⛺",
  "b&b": "🛏",
  other: "🏠",
};

// The accommodation summary: one collapsible card per stay. `view` decides which
// start collapsed (same options as days).
export function AccommodationSummary({
  itinerary,
  lang,
  view = "collapse-past",
}: {
  itinerary: Itinerary;
  lang: Lang;
  view?: CollapseView;
}) {
  const stays = itinerary.accommodations;

  const spans = useMemo<DateSpan[]>(
    () => stays.map((a) => ({ start: a.arrival, end: a.departure ?? a.arrival })),
    [stays],
  );
  const [open, setOpen] = useState(() => collapsedForItems(view, spans));
  useEffect(() => setOpen(collapsedForItems(view, spans)), [view, spans]);

  // Nights already slept are folded away entirely rather than left as a stack
  // of collapsed cards — the day list's treatment of days already travelled,
  // applied to the stays (see `foldedForItems`).
  const fold = useMemo(() => foldedForItems(view, spans), [view, spans]);
  const allPast = useMemo(() => allItemsPast(spans), [spans]);
  const past = usePastFold(fold, allPast);
  const toggle = (i: number) =>
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });

  if (!stays.length) return null;

  return (
    <section className="section accommodation" aria-label={tr(lang, "accommodation")}>
      <h2>{tr(lang, "accommodation")}</h2>
      <div className="cards">
        <PastFold
          n={fold.size}
          shown={past.shown}
          onToggle={past.toggle}
          lang={lang}
          showKey="showPastStays"
          hideKey="hidePastStays"
        />
        {stays.map((a, i) =>
          past.hidden(i) ? null : (
            <StayCard key={i} a={a} lang={lang} collapsed={open.has(i)} onToggle={() => toggle(i)} />
          ),
        )}
      </div>
    </section>
  );
}

function StayCard({
  a,
  lang,
  collapsed,
  onToggle,
}: {
  a: Accommodation;
  lang: Lang;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const range =
    a.arrival && a.departure
      ? `${fmtDate(a.arrival, lang)} → ${fmtDate(a.departure, lang)}`
      : a.arrival
        ? fmtDate(a.arrival, lang)
        : "";
  const nights =
    a.nights != null
      ? `${a.nights} ${a.nights === 1 ? tr(lang, "night") : tr(lang, "nights")}`
      : "";

  const provider = useMapProvider();
  const bookedVia = a.booking_source
    ? fill(tr(lang, "bookedVia"), { source: a.booking_source })
    : "";
  const where = [a.name, a.city].filter(Boolean).join(", ");
  return (
    <div className={`card ${collapsed ? "collapsed" : ""}`}>
      <CardHead collapsed={collapsed} onToggle={onToggle}>
        <span className="badge" aria-hidden>
          {TYPE_ICON[a.type] ?? TYPE_ICON.other}
        </span>
        <span className="card-title">{a.name}</span>
      </CardHead>
      {!collapsed && (
        <>
          <div className="card-pills">
            <Status status={a.status} lang={lang} />
          </div>
          <p className="card-meta">
            {a.city && <span>{a.city}</span>}
            {range && <span>{range}</span>}
            {nights && <span>{nights}</span>}
            {a.breakfast_included && <span>🥐 {tr(lang, "breakfastIncluded")}</span>}
            {bookedVia && <span>{bookedVia}</span>}
          </p>
          {(a.address || a.coordinate) && (
            <p className="card-addr">
              {a.address && <AddressLink address={a.address} />}
              {a.address ? "  " : ""}
              <NavLink lang={lang} href={navUrl(provider, a.coordinate, a.address, where)} />
            </p>
          )}
          {a.contact && <p className="card-addr">{a.contact}</p>}
          {a.description && <Clamp className="card-note" text={a.description} />}
          {a.price && (
            <p className="card-price">
              <Price price={a.price} lang={lang} />
            </p>
          )}
          <Links lang={lang} website={a.website} reservation={a.booking_link} />
        </>
      )}
    </div>
  );
}
