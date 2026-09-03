import { useEffect, useMemo, useState } from "react";
import type {
  CarRental,
  Itinerary,
  Stamp,
  Transport,
  TransportLeg,
} from "../types/resolved";
import { fill, fmtDate, fmtKm, tr, type Lang } from "./format";
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

// The booking's reference line: what identifies the reservation as a whole. The
// flight/train number is *not* here — that belongs to a single leg (see LegBlock).
function bookingRef(t: Transport, lang: Lang): string {
  const bits: string[] = [];
  if (t.booking_number) bits.push(fill(tr(lang, "ref"), { ref: t.booking_number }));
  if (t.booking_source) bits.push(fill(tr(lang, "bookedVia"), { source: t.booking_source }));
  return bits.join("  ·  ");
}

function legNumber(leg: TransportLeg, lang: Lang): string {
  if (leg.type === "plane" && leg.flight_number)
    return fill(tr(lang, "flight"), { number: leg.flight_number });
  if (leg.type === "train" && leg.train_number)
    return fill(tr(lang, "train"), { number: leg.train_number });
  return "";
}

// The hop's when-and-how-far line: its date, its times, and its distance
// (rounded for display like every other distance in the book). Mirrors
// `_leg_info` in pdf/transport.py — the distance sits here rather than with the
// flight number because a leg with no number would otherwise have nowhere to
// show it.
function legDates(leg: TransportLeg, lang: Lang): string {
  const dateStr = leg.start_date
    ? fmtDate(leg.start_date, lang) +
      (leg.end_date && leg.end_date !== leg.start_date
        ? ` → ${fmtDate(leg.end_date, lang)}`
        : "")
    : "";
  const dist = leg.distance_km != null ? fmtKm(leg.distance_km) : "";
  return [dateStr, transportTimes(leg), dist].filter(Boolean).join("  ·  ");
}

// One hop of a *multi-leg* booking: its position, where it goes, when, its own
// number and note — inset under everything the reservation covers. A one-leg
// booking has nothing to tell apart, so TransportCard lays it out flat instead.
function LegBlock({ leg, lang, index }: { leg: TransportLeg; lang: Lang; index: number }) {
  const provider = useMapProvider();
  const info = legDates(leg, lang);
  const navHref = navUrl(provider, leg.start_coordinate ?? leg.coordinate, leg.start);
  const number = legNumber(leg, lang);
  return (
    <div className="card-leg">
      <p className="card-leg-title">
        <span className="card-leg-badge">{fill(tr(lang, "leg"), { n: index + 1 })}</span>
        <strong>{leg.title}</strong>
        {leg.overnight && <span className="chip">{tr(lang, "overnight")}</span>}
      </p>
      {info && <p className="card-info">{info}</p>}
      {navHref && (
        <p className="card-nav">
          <NavLink lang={lang} href={navHref} />
        </p>
      )}
      {number && <p className="card-meta">{number}</p>}
      {leg.description && <Clamp className="card-note" text={leg.description} />}
    </div>
  );
}

// A one-leg booking, flat: no rule, no inset, no leg number — the booking *is*
// that movement. Its route line is dropped when it would only repeat the card's
// heading (the usual case: an unnamed booking is headed with its route, so the
// heading carries the Navigate link instead). Mirrors pdf/transport.py's
// `_flat_transport_card`.
function FlatBooking({ t, lang }: { t: Transport; lang: Lang }) {
  const provider = useMapProvider();
  const leg = t.legs[0];
  const info = legDates(leg, lang);
  const navHref = navUrl(provider, leg.start_coordinate ?? leg.coordinate, leg.start);
  const route = leg.title === t.title ? "" : leg.title;
  // This leg's own number joined with the booking's reference: with one leg
  // there's no reason to split them over two lines.
  const identity = [legNumber(leg, lang), bookingRef(t, lang)]
    .filter(Boolean)
    .join("  ·  ");
  return (
    <>
      <div className="card-pills">
        {leg.overnight && <span className="chip filled">{tr(lang, "overnight")}</span>}
        <Status status={t.status} lang={lang} />
      </div>
      {route && (
        <p className="card-leg-title">
          <strong>{route}</strong>
        </p>
      )}
      {info && <p className="card-info">{info}</p>}
      {navHref && (
        <p className="card-nav">
          <NavLink lang={lang} href={navHref} />
        </p>
      )}
      {identity && <p className="card-meta">{identity}</p>}
      {/* the reservation's note, then this hop's — the multi-leg card's order */}
      {t.description && <Clamp className="card-note" text={t.description} />}
      {leg.description && <Clamp className="card-note" text={leg.description} />}
      {t.price && (
        <p className="card-price">
          <Price price={t.price} lang={lang} />
        </p>
      )}
      <Links lang={lang} website={t.website} reservation={t.booking_link} />
    </>
  );
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
  const ref = bookingRef(t, lang);
  return (
    <div className={`card ${collapsed ? "collapsed" : ""}`}>
      <CardHead collapsed={collapsed} onToggle={onToggle}>
        <span className="badge" aria-hidden>
          {TYPE_ICON[t.type] ?? TYPE_ICON.other}
        </span>
        <span className="card-title">{t.title}</span>
      </CardHead>
      {!collapsed &&
        (t.legs.length === 1 ? (
          <FlatBooking t={t} lang={lang} />
        ) : (
          <>
            {/* Everything the reservation covers, stated once, first… */}
            <div className="card-pills">
              <Status status={t.status} lang={lang} />
            </div>
            {ref && <p className="card-meta">{ref}</p>}
            {t.description && <Clamp className="card-note" text={t.description} />}
            {/* One price for the whole booking, every leg included. */}
            {t.price && (
              <p className="card-price">
                <Price price={t.price} lang={lang} />
              </p>
            )}
            <Links lang={lang} website={t.website} reservation={t.booking_link} />
            {/* …then the legs, inset under a rule so they read as subordinate to
                the booking above (mirrors pdf/transport.py's card). */}
            <div className="card-legs">
              {t.legs.map((leg, i) => (
                <LegBlock key={i} leg={leg} lang={lang} index={i} />
              ))}
            </div>
          </>
        ))}
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
