import type { Activity, CarEvent, Day } from "../types/resolved";
import { fmtDate, tr, type Lang } from "./format";

// Uppercase type label shown in the gutter badge, mirroring the PDF's
// _badge_label (POIs use their category when it isn't the generic "other").
function badgeLabel(act: Activity): string {
  switch (act.type) {
    case "road":
      return "ROAD";
    case "hike":
      return "HIKE";
    case "meal":
      return "MEAL";
    case "place":
      return "PLACE";
    case "point_of_interest":
      return act.category && act.category !== "other"
        ? act.category.toUpperCase().slice(0, 14)
        : "POINT";
    default:
      return act.type.toUpperCase();
  }
}

// A day: colored header band, optional intro, the merged time-ordered timeline
// (activities + car pick-up/drop-off events), and the tonight's-stay bar.
export function DayCard({ day, lang }: { day: Day; lang: Lang }) {
  const timeline = mergeTimeline(day);

  return (
    <article className="day" aria-label={`${tr(lang, "day")} ${day.day_number}`}>
      <header className="day-band">
        <span className="day-num">
          {tr(lang, "day")} {day.day_number}
        </span>
        <span className="day-date">{fmtDate(day.date, lang, true)}</span>
        <span className="day-title">{day.title}</span>
        {day.city && <span className="day-city">{day.city}</span>}
      </header>

      {day.description && <p className="day-intro">{day.description}</p>}

      <ol className="timeline">
        {timeline.map((item, i) =>
          item.kind === "car" ? (
            <CarEventRow key={i} event={item.event} lang={lang} />
          ) : (
            <ActivityRow key={i} act={item.act} lang={lang} />
          ),
        )}
      </ol>

      <StayBar day={day} lang={lang} />
    </article>
  );
}

// --- timeline merge ---------------------------------------------------------

type TimelineItem =
  | { kind: "act"; act: Activity; t: string }
  | { kind: "car"; event: CarEvent; t: string };

function mergeTimeline(day: Day): TimelineItem[] {
  const items: TimelineItem[] = [
    ...day.activities.map((act) => ({ kind: "act" as const, act, t: act.start_time ?? "" })),
    ...day.car_events.map((event) => ({ kind: "car" as const, event, t: event.start_time ?? "" })),
  ];
  // "HH:MM" sorts chronologically as strings; keep a stable order for ties.
  return items
    .map((item, i) => ({ item, i }))
    .sort((a, b) => a.item.t.localeCompare(b.item.t) || a.i - b.i)
    .map(({ item }) => item);
}

// --- gutter (type badge stacked above the times) ----------------------------

function Gutter({
  label,
  start,
  end,
  startTz,
  endTz,
}: {
  label: string;
  start: string | null;
  end: string | null;
  startTz?: string;
  endTz?: string;
}) {
  const showEnd = end && end !== start;
  return (
    <div className="gutter">
      <span className="type-badge">{label}</span>
      {start && (
        <span className="t-start">
          {start}
          {startTz ? <em>{startTz}</em> : null}
        </span>
      )}
      {showEnd && (
        <span className="t-end">
          {end}
          {endTz ? <em>{endTz}</em> : null}
        </span>
      )}
    </div>
  );
}

// --- rows -------------------------------------------------------------------

function ActivityRow({ act, lang }: { act: Activity; lang: Lang }) {
  if (act.type === "buffer") {
    return (
      <li className="act buffer">
        <div className="gutter" />
        <span className="buffer-label">
          {tr(lang, "freeTime")}
          {act.duration_display ? ` · ${act.duration_display}` : ""}
        </span>
      </li>
    );
  }

  return (
    <li className={`act ${act.type}`}>
      <Gutter
        label={badgeLabel(act)}
        start={act.start_time}
        end={act.end_time}
        startTz={act.start_tz_label}
        endTz={act.end_tz_label}
      />
      <div className="act-body">
        <div className="act-title">{act.title}</div>
        <ActivityDetails act={act} lang={lang} />
        {act.activities && act.activities.length > 0 && (
          <ol className="nested">
            {act.activities.map((sub, i) => (
              <ActivityRow key={i} act={sub} lang={lang} />
            ))}
          </ol>
        )}
      </div>
    </li>
  );
}

function ActivityDetails({ act, lang }: { act: Activity; lang: Lang }) {
  const bits: string[] = [];

  if (act.type === "road") {
    if (act.duration_display) bits.push(act.duration_display);
    if (act.distance_km != null) bits.push(`${act.distance_km} km`);
    if (act.off_road) bits.push(tr(lang, "offRoad"));
  } else if (act.type === "hike") {
    if (act.route_label) bits.push(act.route_label);
    if (act.duration_display) bits.push(act.duration_display);
    if (act.distance_km != null) bits.push(`${act.distance_km} km`);
    if (act.elevation_m != null) bits.push(`${act.elevation_m} m ${tr(lang, "elevation")}`);
  } else if (act.type === "meal") {
    if (act.duration_display) bits.push(act.duration_display);
    if (act.area) bits.push(act.area);
    if (act.address) bits.push(act.address);
  } else if (act.type === "point_of_interest") {
    if (act.address) bits.push(act.address);
  }

  const description =
    act.type === "point_of_interest" || act.type === "place" ? act.description : "";
  const website = act.type === "point_of_interest" ? act.website : "";

  if (!bits.length && !description && !website) return null;
  return (
    <div className="act-details">
      {bits.length > 0 && <p className="chips-line">{bits.join("  ·  ")}</p>}
      {description && <p className="desc">{description}</p>}
      {website && (
        <a className="link" href={website} target="_blank" rel="noreferrer">
          {website.replace(/^https?:\/\//, "")}
        </a>
      )}
    </div>
  );
}

function CarEventRow({ event, lang }: { event: CarEvent; lang: Lang }) {
  const label = event.kind === "car_pickup" ? tr(lang, "pickUp") : tr(lang, "dropOff");
  const who = [event.company, event.car_model].filter(Boolean).join(" · ");
  return (
    <li className="act car">
      <Gutter
        label="CAR"
        start={event.start_time}
        end={event.end_time}
        startTz={event.start_tz_label}
        endTz={event.end_tz_label}
      />
      <div className="act-body">
        <div className="act-title">
          {label}
          {who ? ` — ${who}` : ""}
        </div>
        {event.location && <div className="act-details">{event.location}</div>}
      </div>
    </li>
  );
}

function StayBar({ day, lang }: { day: Day; lang: Lang }) {
  if (day.stay) {
    const nights =
      day.stay.nights != null
        ? ` · ${day.stay.nights} ${day.stay.nights === 1 ? tr(lang, "night") : tr(lang, "nights")}`
        : "";
    return (
      <footer className="stay-bar">
        🛏 {tr(lang, "tonight")}: <strong>{day.stay.name}</strong>
        {day.stay.city ? ` (${day.stay.city})` : ""}
        {nights}
      </footer>
    );
  }
  if (day.night_transport) {
    return (
      <footer className="stay-bar aboard">
        🌙 {tr(lang, "tonight")}: {tr(lang, "aboard")} {day.night_transport.title}
      </footer>
    );
  }
  return (
    <footer className="stay-bar none">
      🛏 {tr(lang, "tonight")}: {tr(lang, "nowhere")}
    </footer>
  );
}
