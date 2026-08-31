import { useEffect, useMemo, useState } from "react";
import type { CarRental, Itinerary, Stamp, Transport } from "../types/resolved";
import { fill, fmtDate, tr, type Lang } from "./format";
import { collapsedForItems, type CollapseView, type DateSpan } from "./collapse";
import { CardHead, Price, Status } from "./Parts";
import { Clamp } from "./Clamp";
import { AddressLink, Links, NavLink } from "./Links";
import { navUrl, transportTimes, useMapProvider } from "./nav";

const TYPE_ICON: Record<string, string> = {
  plane: "✈️",
  train: "🚆",
  bus: "🚌",
  taxi: "🚕",
  ferry: "⛴️",
  other: "🚊",
};

// The transport section: travel legs plus rental-car bookings. Each card is
// collapsible; `view` decides which start collapsed (same options as days).
export function TransportList({
  itinerary,
  lang,
  view = "collapse-past",
}: {
  itinerary: Itinerary;
  lang: Lang;
  view?: CollapseView;
}) {
  const { transports, car_rentals } = itinerary;

  const tSpans = useMemo<DateSpan[]>(
    () => transports.map((t) => ({ start: t.start_date, end: t.end_date ?? t.start_date })),
    [transports],
  );
  const cSpans = useMemo<DateSpan[]>(
    () =>
      car_rentals.map((c) => ({
        start: c.booking_start?.date ?? null,
        end: c.booking_end?.date ?? c.booking_start?.date ?? null,
      })),
    [car_rentals],
  );

  const [tOpen, setTOpen] = useState(() => collapsedForItems(view, tSpans));
  const [cOpen, setCOpen] = useState(() => collapsedForItems(view, cSpans));
  useEffect(() => setTOpen(collapsedForItems(view, tSpans)), [view, tSpans]);
  useEffect(() => setCOpen(collapsedForItems(view, cSpans)), [view, cSpans]);

  const toggle = (set: (fn: (p: Set<number>) => Set<number>) => void) => (i: number) =>
    set((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  const toggleT = toggle(setTOpen);
  const toggleC = toggle(setCOpen);

  if (!transports.length && !car_rentals.length) return null;

  return (
    <section className="section transport" aria-label={tr(lang, "transport")}>
      <h2>{tr(lang, "transport")}</h2>

      <div className="cards">
        {transports.map((t, i) => (
          <TransportCard
            key={i}
            t={t}
            lang={lang}
            collapsed={tOpen.has(i)}
            onToggle={() => toggleT(i)}
          />
        ))}
      </div>

      {car_rentals.length > 0 && (
        <>
          <h3 className="sub">{tr(lang, "carRentals")}</h3>
          <div className="cards">
            {car_rentals.map((c, i) => (
              <CarRentalCard
                key={i}
                c={c}
                lang={lang}
                collapsed={cOpen.has(i)}
                onToggle={() => toggleC(i)}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function transportBooking(t: Transport, lang: Lang): string {
  const bits: string[] = [];
  if (t.type === "plane" && t.flight_number)
    bits.push(fill(tr(lang, "flight"), { number: t.flight_number }));
  else if (t.type === "train" && t.train_number)
    bits.push(fill(tr(lang, "train"), { number: t.train_number }));
  if (t.booking_number) bits.push(fill(tr(lang, "ref"), { ref: t.booking_number }));
  if (t.booking_source) bits.push(fill(tr(lang, "bookedVia"), { source: t.booking_source }));
  return bits.join("  ·  ");
}

function TransportCard({
  t,
  lang,
  collapsed,
  onToggle,
}: {
  t: Transport;
  lang: Lang;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const dateStr = t.start_date
    ? fmtDate(t.start_date, lang) +
      (t.end_date && t.end_date !== t.start_date ? ` → ${fmtDate(t.end_date, lang)}` : "")
    : "";
  const info = [dateStr, transportTimes(t)].filter(Boolean).join("  ·  ");
  const provider = useMapProvider();
  const booking = transportBooking(t, lang);
  const navHref = navUrl(provider, t.start_coordinate ?? t.coordinate, t.start);
  return (
    <div className={`card ${collapsed ? "collapsed" : ""}`}>
      <CardHead collapsed={collapsed} onToggle={onToggle}>
        <span className="badge" aria-hidden>
          {TYPE_ICON[t.type] ?? TYPE_ICON.other}
        </span>
        <span className="card-title">{t.title}</span>
      </CardHead>
      {!collapsed && (
        <>
          <div className="card-pills">
            {t.overnight && <span className="chip filled">{tr(lang, "overnight")}</span>}
            <Status status={t.status} lang={lang} />
          </div>
          {info && <p className="card-info">{info}</p>}
          {navHref && (
            <p className="card-nav">
              <NavLink lang={lang} href={navHref} />
            </p>
          )}
          {booking && <p className="card-meta">{booking}</p>}
          {t.description && <Clamp className="card-note" text={t.description} />}
          {t.price && (
            <p className="card-price">
              <Price price={t.price} lang={lang} />
            </p>
          )}
          <Links lang={lang} website={t.website} reservation={t.booking_link} />
        </>
      )}
    </div>
  );
}

function stampLine(s: Stamp, lang: Lang): string {
  const time = [s.time, s.tz_label].filter(Boolean).join(" ");
  return [fmtDate(s.date, lang), time].filter(Boolean).join(" · ");
}

function carMeta(c: CarRental, lang: Lang): string {
  const bits: string[] = [];
  if (c.car_model && c.company) bits.push(c.car_model);
  if (c.booking_number) bits.push(fill(tr(lang, "ref"), { ref: c.booking_number }));
  if (c.additional_drivers)
    bits.push(
      fill(tr(lang, c.additional_drivers === 1 ? "driver" : "drivers"), {
        n: c.additional_drivers,
      }),
    );
  if (c.contact) bits.push(c.contact);
  return bits.join("  ·  ");
}

function carWindow(c: CarRental, lang: Lang): string {
  const start = stampLine(c.booking_start, lang);
  const end = stampLine(c.booking_end, lang);
  if (start && end) return fill(tr(lang, "bookedWindow"), { start, end });
  if (start) return fill(tr(lang, "bookedFrom"), { start });
  return "";
}

function CarRentalCard({
  c,
  lang,
  collapsed,
  onToggle,
}: {
  c: CarRental;
  lang: Lang;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const provider = useMapProvider();
  // Trailing bits after the location (stamp + duration), kept as plain text; the
  // location itself is rendered as a clickable AddressLink (navigate-by-address),
  // matching how accommodations and activities present their addresses.
  const pickupRest = [stampLine(c.pickup, lang), c.pickup_duration_display]
    .filter(Boolean)
    .join(" — ");
  const dropoffRest = [stampLine(c.dropoff, lang), c.dropoff_duration_display]
    .filter(Boolean)
    .join(" — ");
  const window = carWindow(c, lang);
  const meta = carMeta(c, lang);
  return (
    <div className={`card ${collapsed ? "collapsed" : ""}`}>
      <CardHead collapsed={collapsed} onToggle={onToggle}>
        <span className="badge" aria-hidden>
          🚙
        </span>
        <span className="card-title">
          {c.title}
          {c.car_type_label ? ` · ${c.car_type_label}` : ""}
        </span>
      </CardHead>
      {!collapsed && (
        <>
          <div className="card-pills">
            <Status status={c.status} lang={lang} />
          </div>
          <p className="card-meta">
            <span>
              {tr(lang, "pickUp")}: <AddressLink address={c.pickup_location} />
              {pickupRest ? ` — ${pickupRest}` : ""}{"  "}
              <NavLink lang={lang} href={navUrl(provider, c.pickup_coordinate ?? c.coordinate, c.pickup_location)} />
            </span>
            <span>
              {tr(lang, "dropOff")}: <AddressLink address={c.dropoff_location} />
              {dropoffRest ? ` — ${dropoffRest}` : ""}{"  "}
              <NavLink lang={lang} href={navUrl(provider, c.dropoff_coordinate ?? c.coordinate, c.dropoff_location)} />
            </span>
            {window && <span>{window}</span>}
            {meta && <span>{meta}</span>}
          </p>
          {c.description && <Clamp className="card-note" text={c.description} />}
          {c.price && (
            <p className="card-price">
              <Price price={c.price} lang={lang} />
            </p>
          )}
          <Links lang={lang} website={c.website} reservation={c.booking_link} />
        </>
      )}
    </div>
  );
}
