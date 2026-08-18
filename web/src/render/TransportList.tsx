import type { CarRental, Itinerary, Stamp, Transport } from "../types/resolved";
import { fmtDate, tr, type Lang } from "./format";
import { Price, Status } from "./Parts";

const TYPE_ICON: Record<string, string> = {
  plane: "✈️",
  train: "🚆",
  bus: "🚌",
  taxi: "🚕",
  ferry: "⛴️",
  other: "🚊",
};

// The transport section: travel legs plus rental-car bookings.
export function TransportList({
  itinerary,
  lang,
}: {
  itinerary: Itinerary;
  lang: Lang;
}) {
  const { transports, car_rentals } = itinerary;
  if (!transports.length && !car_rentals.length) return null;

  return (
    <section className="section transport" aria-label={tr(lang, "transport")}>
      <h2>{tr(lang, "transport")}</h2>

      <div className="cards">
        {transports.map((t, i) => (
          <TransportCard key={i} t={t} lang={lang} />
        ))}
      </div>

      {car_rentals.length > 0 && (
        <>
          <h3 className="sub">{tr(lang, "carRentals")}</h3>
          <div className="cards">
            {car_rentals.map((c, i) => (
              <CarRentalCard key={i} c={c} lang={lang} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function TransportCard({ t, lang }: { t: Transport; lang: Lang }) {
  const number = t.flight_number || t.train_number;
  const dateStr = t.start_date
    ? fmtDate(t.start_date, lang) +
      (t.end_date && t.end_date !== t.start_date ? ` → ${fmtDate(t.end_date, lang)}` : "")
    : "";
  return (
    <div className="card">
      <div className="card-head">
        <span className="badge" aria-hidden>
          {TYPE_ICON[t.type] ?? TYPE_ICON.other}
        </span>
        <span className="card-title">{t.title}</span>
        <Status status={t.status} lang={lang} />
      </div>
      <p className="card-meta">
        {dateStr && <span>{dateStr}</span>}
        {t.time_range && <span>{t.time_range}</span>}
        {t.duration_display && <span>{t.duration_display}</span>}
        {number && <span className="mono">{number}</span>}
      </p>
      {t.price && (
        <p className="card-price">
          <Price price={t.price} lang={lang} />
        </p>
      )}
    </div>
  );
}

function stampLine(s: Stamp, lang: Lang): string {
  return [fmtDate(s.date, lang), s.time].filter(Boolean).join(" · ");
}

function CarRentalCard({ c, lang }: { c: CarRental; lang: Lang }) {
  return (
    <div className="card">
      <div className="card-head">
        <span className="badge" aria-hidden>
          🚙
        </span>
        <span className="card-title">
          {c.title}
          {c.car_type_label ? ` · ${c.car_type_label}` : ""}
        </span>
        <Status status={c.status} lang={lang} />
      </div>
      <p className="card-meta">
        <span>
          {tr(lang, "pickUp")}: {c.pickup_location} — {stampLine(c.pickup, lang)}
        </span>
        <span>
          {tr(lang, "dropOff")}: {c.dropoff_location} — {stampLine(c.dropoff, lang)}
        </span>
      </p>
      {c.price && (
        <p className="card-price">
          <Price price={c.price} lang={lang} />
        </p>
      )}
    </div>
  );
}
