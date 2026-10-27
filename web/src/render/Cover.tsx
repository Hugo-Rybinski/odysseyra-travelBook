import { useState } from "react";
import type { Day, Itinerary, TransportLeg } from "../types/resolved";
import { fill, fmtDate, fmtDateRange, idx, tr, type Lang } from "./format";
import { Clamp } from "./Clamp";
import { Caret } from "./Icon";

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
        {/* The cartouche's facts ledger: a field name over each value, as a
            map sheet's margin states its edition. */}
        <dl className="cover-meta">
          {range && (
            <div className="cover-fact cover-fact-wide">
              <dt>{tr(lang, "ledgerDates")}</dt>
              <dd>{range}</dd>
            </div>
          )}
          <div className="cover-fact">
            <dt>{tr(lang, "ledgerDays")}</dt>
            <dd>{itinerary.day_count}</dd>
          </div>
          {itinerary.accommodations.length > 0 && (
            <div className="cover-fact">
              <dt>{tr(lang, "ledgerStays")}</dt>
              <dd>{itinerary.accommodations.length}</dd>
            </div>
          )}
        </dl>
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
          <Caret open={overviewOpen} className="overview-caret" />
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
                  {idx(d.day_number)}
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
const STOP_TYPES = ["point_of_interest", "place", "hike"];

function highlightsOf(day: Day, lang: Lang): string {
  const items = [
    ...day.activities.map((a) => ({ t: a.start_time ?? "", act: a })),
    ...day.transports.map((tp) => ({ t: tp.start_time ?? "", transport: tp })),
  ].sort((a, b) => a.t.localeCompare(b.t));

  // A drive is dropped once the day has two other stops to advertise: it is how
  // you got to them, not what the day is for, and this cell is a few words on a
  // table row. Below two it stays, so a day of one visit and a long transfer
  // still reads as both. Only activities count toward the two — a transport leg
  // isn't one. Keep in step with the PDF cover's `_day_highlights`.
  const stops = day.activities.filter(
    (a) => !a.detour && STOP_TYPES.includes(a.type),
  ).length;

  const titles: string[] = [];
  for (const item of items) {
    if ("act" in item) {
      const a = item.act;
      // A detour is never a highlight: it's the stop you probably won't make,
      // so listing it here would advertise the day as something it isn't. The
      // PDF cover's `_day_highlights` skips them too.
      if (a.detour) continue;
      if (STOP_TYPES.includes(a.type)) {
        titles.push(a.title);
      } else if (a.type === "road" && (a.duration_min ?? 0) > 60 && stops < 2) {
        titles.push(`${tr(lang, "road")} ${a.title}`.trim());
      }
    } else {
      titles.push(item.transport.title);
    }
  }
  if (titles.length) return titles.join(", ");

  const drives = day.activities
    .filter((a) => a.type === "road" && !a.detour)
    .map((a) => `${tr(lang, "road")} ${a.title}`.trim());
  return drives.join(", ") || day.title || "—";
}

function overnightName(leg: TransportLeg, lang: Lang): string {
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
