import type { Accommodation, Itinerary } from "../types/resolved";
import { fmtDate, tr, type Lang } from "./format";
import { Price, Status } from "./Parts";

const TYPE_ICON: Record<string, string> = {
  hotel: "🏨",
  camping: "⛺",
  "b&b": "🛏",
  other: "🏠",
};

// The accommodation summary: one card per stay.
export function AccommodationSummary({
  itinerary,
  lang,
}: {
  itinerary: Itinerary;
  lang: Lang;
}) {
  const stays = itinerary.accommodations;
  if (!stays.length) return null;

  return (
    <section className="section accommodation" aria-label={tr(lang, "accommodation")}>
      <h2>{tr(lang, "accommodation")}</h2>
      <div className="cards">
        {stays.map((a, i) => (
          <StayCard key={i} a={a} lang={lang} />
        ))}
      </div>
    </section>
  );
}

function StayCard({ a, lang }: { a: Accommodation; lang: Lang }) {
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

  return (
    <div className="card">
      <div className="card-head">
        <span className="badge" aria-hidden>
          {TYPE_ICON[a.type] ?? TYPE_ICON.other}
        </span>
        <span className="card-title">{a.name}</span>
        <Status status={a.status} lang={lang} />
      </div>
      <p className="card-meta">
        {a.city && <span>{a.city}</span>}
        {range && <span>{range}</span>}
        {nights && <span>{nights}</span>}
        {a.breakfast_included && <span>🥐 {tr(lang, "breakfastIncluded")}</span>}
      </p>
      {a.address && <p className="card-addr">{a.address}</p>}
      {a.price && (
        <p className="card-price">
          <Price price={a.price} lang={lang} />
        </p>
      )}
    </div>
  );
}
