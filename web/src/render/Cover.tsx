import { useState } from "react";
import type { Day, Itinerary, Transport } from "../types/resolved";
import { fill, fmtDate, fmtDateRange, tr, type Lang } from "./format";
import { Clamp } from "./Clamp";

// The cover: title / subtitle / inferred date range / day count / summary, plus
// a day-by-day overview table (day number, date, the day's highlights, and the
// town you sleep in) — the same overview the PDF cover carries.
export function Cover({
  itinerary,
  lang,
  onJump,
  startOverviewOpen = false,
}: {
  itinerary: Itinerary;
  lang: Lang;
  onJump: (dayNumber: number) => void;
  // Force the day-by-day table open on first render (the Overview tab, where
  // the table is the point), overriding the mobile default below.
  startOverviewOpen?: boolean;
}) {
  const range = fmtDateRange(itinerary.start_date, itinerary.end_date, lang);

  // The day-by-day overview collapses under its heading. Open on desktop but
  // collapsed by default on mobile (narrow viewports), so the phone lands on
  // the title + summary rather than a full-height table.
  const [overviewOpen, setOverviewOpen] = useState<boolean>(
    () =>
      startOverviewOpen ||
      !(typeof window !== "undefined" && window.matchMedia?.("(max-width: 640px)").matches),
  );

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

      {itinerary.summary && <Clamp className="cover-summary" text={itinerary.summary} />}

      <div className={`overview ${overviewOpen ? "" : "collapsed"}`}>
        <h2
          className="overview-toggle"
          role="button"
          tabIndex={0}
          aria-expanded={overviewOpen}
          onClick={() => setOverviewOpen((o) => !o)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setOverviewOpen((o) => !o);
            }
          }}
        >
          <span className="overview-caret" aria-hidden>
            {overviewOpen ? "▾" : "▸"}
          </span>
          {tr(lang, "overview")}
        </h2>
        {overviewOpen && (
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
              <tr
                key={d.day_number}
                className="row-link"
                tabIndex={0}
                aria-label={`${tr(lang, "day")} ${d.day_number}`}
                onClick={() => onJump(d.day_number)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onJump(d.day_number);
                  }
                }}
              >
                <td className="num" data-label={tr(lang, "day")}>
                  {d.day_number}
                </td>
                <td className="date">{fmtDate(d.date, lang)}</td>
                <td>{highlightsOf(d, lang)}</td>
                <td className="sleep">{sleepLabel(d, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        )}
      </div>
    </section>
  );
}

// Time-ordered highlights, mirroring the PDF cover: POIs / places / hikes,
// long drives (>60 min), and transport legs — falling back to the drives, then
// the day title.
function highlightsOf(day: Day, lang: Lang): string {
  const items = [
    ...day.activities.map((a) => ({ t: a.start_time ?? "", act: a })),
    ...day.transports.map((tp) => ({ t: tp.start_time ?? "", transport: tp })),
  ].sort((a, b) => a.t.localeCompare(b.t));

  const titles: string[] = [];
  for (const item of items) {
    if ("act" in item) {
      const a = item.act;
      if (a.type === "point_of_interest" || a.type === "place" || a.type === "hike") {
        titles.push(a.title);
      } else if (a.type === "road" && (a.duration_min ?? 0) > 60) {
        titles.push(`${tr(lang, "road")} ${a.title}`.trim());
      }
    } else {
      titles.push(item.transport.title);
    }
  }
  if (titles.length) return titles.join(", ");

  const drives = day.activities
    .filter((a) => a.type === "road")
    .map((a) => `${tr(lang, "road")} ${a.title}`.trim());
  return drives.join(", ") || day.title || "—";
}

function overnightName(leg: Transport, lang: Lang): string {
  const type = (leg.type || "").trim();
  if (!type) return tr(lang, "overnightTravel");
  if (/night|overnight|nuit/i.test(type)) return type[0].toUpperCase() + type.slice(1);
  return fill(tr(lang, "overnightType"), { type });
}

// Where you sleep that night: the stay's town, an overnight leg, or the day city.
function sleepLabel(day: Day, lang: Lang): string {
  if (day.stay) return day.stay.city || day.stay.name;
  if (day.night_transport) return overnightName(day.night_transport, lang);
  return day.city || "—";
}
