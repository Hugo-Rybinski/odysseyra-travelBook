import type { Itinerary } from "../types/resolved";
import { fmtDate, fmtDateRange, tr, type Lang } from "./format";

// The cover: title / subtitle / inferred date range / day count / summary, plus
// a day-by-day overview table (day number, date, the day's highlights, and the
// town you sleep in) — the same overview the PDF cover carries.
export function Cover({ itinerary, lang }: { itinerary: Itinerary; lang: Lang }) {
  const range = fmtDateRange(itinerary.start_date, itinerary.end_date, lang);

  return (
    <section className="cover" aria-label="Cover">
      <div className="cover-band">
        <h1>{itinerary.title}</h1>
        {itinerary.subtitle && <p className="cover-sub">{itinerary.subtitle}</p>}
        <p className="cover-meta">
          {range && <span>{range}</span>}
          <span>
            {itinerary.day_count} {tr(lang, "days")}
          </span>
        </p>
      </div>

      {itinerary.summary && <p className="cover-summary">{itinerary.summary}</p>}

      <div className="overview">
        <h2>{tr(lang, "overview")}</h2>
        <table>
          <thead>
            <tr>
              <th>{tr(lang, "dayCol")}</th>
              <th>{tr(lang, "dateCol")}</th>
              <th>{tr(lang, "activitiesCol")}</th>
              <th>{tr(lang, "sleepCol")}</th>
            </tr>
          </thead>
          <tbody>
            {itinerary.days.map((d) => (
              <tr key={d.day_number}>
                <td className="num">{d.day_number}</td>
                <td className="date">{fmtDate(d.date, lang)}</td>
                <td>{highlightsOf(d)}</td>
                <td className="sleep">{d.sleep_city || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// A short "highlights" string for the overview row: the day's title, or the
// titles of its non-buffer activities when the title is generic/empty.
function highlightsOf(day: Itinerary["days"][number]): string {
  if (day.title) return day.title;
  const names = day.activities
    .filter((a) => a.type !== "buffer")
    .map((a) => a.title)
    .filter(Boolean);
  return names.slice(0, 3).join(" · ") || "—";
}
