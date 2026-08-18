import type { Activity, CarEvent, Day, Transport } from "../types/resolved";
import { fill, fmtDate, tr, type Lang } from "./format";
import { Links, NavLink } from "./Links";
import { activityNav, fmtDurationMin, navUrl, roadLegs, transportTimes } from "./nav";

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
// (activities + same-day transport legs + car pick-up/drop-off), and the
// tonight's-stay bar. The band toggles the day open/closed; the article carries
// a `day-N` id so the cover overview can jump to it.
export function DayCard({
  day,
  lang,
  collapsed,
  onToggle,
}: {
  day: Day;
  lang: Lang;
  collapsed: boolean;
  onToggle: (dayNumber: number) => void;
}) {
  const timeline = mergeTimeline(day);
  const toggle = () => onToggle(day.day_number);

  return (
    <article
      id={`day-${day.day_number}`}
      className={`day ${collapsed ? "collapsed" : ""}`}
      aria-label={`${tr(lang, "day")} ${day.day_number}`}
    >
      <header
        className="day-band"
        role="button"
        tabIndex={0}
        aria-expanded={!collapsed}
        onClick={toggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggle();
          }
        }}
      >
        <span className="day-caret" aria-hidden>
          {collapsed ? "▸" : "▾"}
        </span>
        <span className="day-num">
          {tr(lang, "day")} {day.day_number}
        </span>
        <span className="day-date">{fmtDate(day.date, lang, true)}</span>
        <span className="day-title">{day.title}</span>
        {day.city && <span className="day-city">{day.city}</span>}
      </header>

      {!collapsed && (
        <>
          {day.description && <p className="day-intro">{day.description}</p>}

          <ol className="timeline">
            {timeline.map((item, i) =>
              item.kind === "car" ? (
                <CarEventRow key={i} event={item.event} lang={lang} />
              ) : item.kind === "transport" ? (
                <TransportRow key={i} t={item.t} lang={lang} />
              ) : (
                <ActivityRow key={i} act={item.act} lang={lang} />
              ),
            )}
          </ol>

          <StayBar day={day} lang={lang} />
        </>
      )}
    </article>
  );
}

// --- timeline merge ---------------------------------------------------------

type TimelineItem =
  | { kind: "act"; act: Activity; t: string }
  | { kind: "transport"; t: Transport; sort: string }
  | { kind: "car"; event: CarEvent; sort: string };

function mergeTimeline(day: Day): TimelineItem[] {
  const items: (TimelineItem & { s: string })[] = [
    ...day.activities.map((act) => ({ kind: "act" as const, act, t: act.start_time ?? "", s: act.start_time ?? "" })),
    ...day.transports.map((t) => ({ kind: "transport" as const, t, sort: t.start_time ?? "", s: t.start_time ?? "" })),
    ...day.car_events.map((event) => ({ kind: "car" as const, event, sort: event.start_time ?? "", s: event.start_time ?? "" })),
  ];
  // "HH:MM" sorts chronologically as strings; keep a stable order for ties.
  return items
    .map((item, i) => ({ item, i }))
    .sort((a, b) => a.item.s.localeCompare(b.item.s) || a.i - b.i)
    .map(({ item }) => item);
}

// --- gutter (type badge stacked above the times) ----------------------------

function Gutter({
  label,
  start,
  end,
  startTz,
  endTz,
  endDayOffset = 0,
}: {
  label: string;
  start: string | null;
  end: string | null;
  startTz?: string;
  endTz?: string;
  endDayOffset?: number;
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
          {endDayOffset ? <em>+{endDayOffset}</em> : null}
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

  // A multi-leg drive carries its Navigate links per VIA leg (not on the head).
  const multiLeg = act.type === "road" && roadLegs(act.start ?? "", act.waypoints ?? []).length > 1;
  const nav = multiLeg ? "" : activityNav(act);
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
        <div className="act-title">
          {act.title}
          {act.type === "road" && act.off_road && (
            <span className="chip outline">{tr(lang, "offRoad")}</span>
          )}
          {act.type === "hike" && act.route_label && (
            <span className="chip outline">{act.route_label}</span>
          )}
        </div>
        <ActivityDetails act={act} lang={lang} nav={nav} />
        {act.type === "road" && <RoadVia act={act} lang={lang} />}
        {act.type === "point_of_interest" && <Links lang={lang} website={act.website} />}
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

function ActivityDetails({ act, lang, nav }: { act: Activity; lang: Lang; nav: string }) {
  const bits: string[] = [];

  if (act.type === "road") {
    if (act.duration_display) bits.push(act.duration_display);
    if (act.distance_km != null) bits.push(`${act.distance_km} km`);
    // off-road shown as a chip beside the title
  } else if (act.type === "hike") {
    // route (loop / back-and-forth …) shown as a chip beside the title
    if (act.duration_display) bits.push(act.duration_display);
    if (act.distance_km != null) bits.push(`${act.distance_km} km`);
    if (act.elevation_m != null) bits.push(`+${act.elevation_m} m`);
  } else if (act.type === "meal") {
    if (act.duration_display) bits.push(act.duration_display);
    if (act.area) bits.push(act.area);
    if (act.address) bits.push(act.address);
  } else if (act.type === "point_of_interest") {
    if (act.duration_display) bits.push(act.duration_display);
    if (act.address) bits.push(act.address);
  } else if (act.type === "place") {
    if (act.duration_display) bits.push(act.duration_display);
  }

  // A hike's trailhead line, when the title is the hike name (not start → end).
  const trail =
    act.type === "hike" && act.name && act.start && act.end
      ? `${act.start} → ${act.end}`
      : "";
  const description =
    act.type === "point_of_interest" || act.type === "place" ? act.description : "";

  if (!bits.length && !trail && !description && !nav) return null;
  return (
    <div className="act-details">
      {(bits.length > 0 || nav) && (
        <p className="chips-line">
          {bits.join("  ·  ")}
          {nav && (
            <>
              {bits.length > 0 ? "  ·  " : ""}
              <NavLink lang={lang} href={nav} />
            </>
          )}
        </p>
      )}
      {trail && <p className="trail">{trail}</p>}
      {description && <p className="desc">{description}</p>}
    </div>
  );
}

// The VIA breakdown for a multi-leg drive: one row per named leg with its own
// duration/distance and a Navigate link.
function RoadVia({ act, lang }: { act: Activity; lang: Lang }) {
  const legs = roadLegs(act.start ?? "", act.waypoints ?? []);
  if (legs.length <= 1) return null;
  return (
    <div className="via">
      <p className="via-head">{tr(lang, "via").toUpperCase()}</p>
      {legs.map((leg, i) => {
        const meta = [
          fmtDurationMin(leg.durationMin),
          leg.distanceKm != null ? `${leg.distanceKm} km` : "",
        ].filter(Boolean);
        const nav = navUrl(leg.destCoord, leg.dest ?? "");
        return (
          <p key={i} className="via-leg">
            <span className="via-route">
              {leg.src || "?"} → {leg.dest || "?"}
            </span>
            {meta.length > 0 && <span className="via-meta">{meta.join("  ·  ")}</span>}
            {nav && (
              <a className="link" href={nav} target="_blank" rel="noreferrer">
                {tr(lang, "navigate")}
              </a>
            )}
          </p>
        );
      })}
    </div>
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

function TransportRow({ t, lang }: { t: Transport; lang: Lang }) {
  const booking = transportBooking(t, lang);
  const nav = navUrl(t.start_coordinate ?? t.coordinate, t.start);
  return (
    <li className="act transport">
      <Gutter
        label={(t.type || "transport").toUpperCase()}
        start={t.start_time}
        end={t.end_time}
        startTz={t.start_tz_label}
        endTz={t.end_tz_label}
        endDayOffset={t.end_day_offset}
      />
      <div className="act-body">
        <div className="act-title">
          {t.title}
          {nav && (
            <>
              {" "}
              <NavLink lang={lang} href={nav} />
            </>
          )}
          {t.overnight && <span className="chip filled">{tr(lang, "overnight")}</span>}
        </div>
        {t.duration_display && <p className="chips-line accent">{t.duration_display}</p>}
        {booking && <p className="chips-line">{booking}</p>}
        <Links lang={lang} website={t.website} reservation={t.booking_link} />
      </div>
    </li>
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
        {event.location && (
          <p className="chips-line">
            {event.location}{"  "}
            <NavLink lang={lang} href={navUrl(null, event.location)} />
          </p>
        )}
      </div>
    </li>
  );
}

function StayBar({ day, lang }: { day: Day; lang: Lang }) {
  if (day.stay) {
    const s = day.stay;
    const total = s.nights;
    const progress =
      day.stay_night != null && total && total > 1
        ? fill(tr(lang, "nightIndex"), { n: day.stay_night, total })
        : total != null
          ? `${total} ${total === 1 ? tr(lang, "night") : tr(lang, "nights")}`
          : "";
    const bookedVia = s.booking_source
      ? fill(tr(lang, "bookedVia"), { source: s.booking_source })
      : "";
    const sub = [s.address, bookedVia].filter(Boolean).join("  ·  ");
    const where = [s.name, s.city].filter(Boolean).join(", ");
    const nav = navUrl(s.coordinate, s.address, where);
    return (
      <footer className="stay-bar">
        <div className="stay-line">
          <span>
            🛏 {tr(lang, "tonight")}: <strong>{s.name}</strong>
            {s.city ? ` (${s.city})` : ""}
          </span>
          {progress && <span className="stay-progress">{progress}</span>}
        </div>
        {(sub || nav) && (
          <p className="stay-sub">
            {sub}
            {nav && (
              <>
                {sub ? "  ·  " : ""}
                <NavLink lang={lang} href={nav} />
              </>
            )}
          </p>
        )}
        <Links lang={lang} website={s.website} reservation={s.booking_link} />
      </footer>
    );
  }
  if (day.night_transport) {
    const leg = day.night_transport;
    return (
      <footer className="stay-bar aboard">
        <div className="stay-line">
          <span>
            🌙 {tr(lang, "tonight")}: {tr(lang, "aboard")} <strong>{leg.title}</strong>
          </span>
          <span className="stay-progress">{tr(lang, "onBoard")}</span>
        </div>
        {transportTimes(leg) && <p className="stay-sub">{transportTimes(leg)}</p>}
        <Links lang={lang} website={leg.website} reservation={leg.booking_link} />
      </footer>
    );
  }
  return (
    <footer className="stay-bar none">
      🛏 {tr(lang, "tonight")}: {tr(lang, "nowhere")}
    </footer>
  );
}
