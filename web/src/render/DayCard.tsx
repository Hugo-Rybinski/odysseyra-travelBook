import { Fragment, lazy, Suspense, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import type {
  Activity,
  CarEvent,
  Day,
  DayMap,
  MapGeo,
  RenderedMap,
  Transport,
} from "../types/resolved";
import { fill, fmtDate, tr, type Lang, type LabelKey } from "./format";
import { Clamp } from "./Clamp";
import { ForecastChip } from "./forecast";
import { AddressLink, Links, NavLink } from "./Links";
import { MapErrorBoundary } from "./MapErrorBoundary";
import {
  activityNav,
  fmtDurationMin,
  navUrl,
  roadLegs,
  transportTimes,
  useMapProvider,
} from "./nav";

// MapLibre is heavy (~300KB gz) and only needed for the interactive map, so it's
// code-split into its own chunk loaded on demand (not parsed until interactive
// is used). It's still precached, so it's served with the right MIME and works
// offline; a failed load falls back to the static PNG via the error boundary.
const DayMapGL = lazy(() => import("./DayMapGL").then((m) => ({ default: m.DayMapGL })));

// A rendered day/area map (a base64 PNG from the Python renderer, pixel-identical
// to the PDF) with an accent caption aligned to the PDF's map cards.
function MapFigure({ rendered, caption }: { rendered: RenderedMap; caption: string }) {
  return (
    <figure className="day-map">
      <figcaption>{caption}</figcaption>
      <img src={rendered.image} alt={caption} loading="lazy" />
    </figure>
  );
}

// The small accent disc carrying an activity's map-pin label (number / area
// letter / ★ stay), shown inline before its title — mirroring the PDF's pin discs.
function PinDisc({ label }: { label: string | null | undefined }) {
  if (!label) return null;
  return <span className="pin-disc" aria-hidden>{label}</span>;
}

// Placeholder shown in the map's slot while that day's map is still being built
// (the images are fetched per day, after the book text is already on screen).
function MapLoading({ lang }: { lang: Lang }) {
  return (
    <div className="day-map-loading" role="status" aria-live="polite">
      <span className="spin" aria-hidden />
      {tr(lang, "buildingMap")}
    </div>
  );
}

// One map slot (used for both the day overview and each area detail map): the
// interactive MapLibre map when possible (toggle on, geo present, loads OK),
// otherwise the static PNG. A load failure or a fresh geo re-tries via the
// error boundary + remount key.
function MapView({
  geo,
  staticMap,
  interactive,
  caption,
  lang,
}: {
  geo: MapGeo | null;
  staticMap: RenderedMap | null;
  interactive: boolean;
  caption: string;
  lang: Lang;
}) {
  const [glFailed, setGlFailed] = useState(false);
  const [mapKey, setMapKey] = useState(0);
  useEffect(() => {
    setGlFailed(false);
    setMapKey((k) => k + 1);
  }, [geo]);
  // Stable so DayMapGL (which remounts when its props' identity changes) isn't
  // torn down on every re-render.
  const onFail = useCallback(() => setGlFailed(true), []);

  const staticFigure = staticMap ? <MapFigure rendered={staticMap} caption={caption} /> : null;
  const canInteractive =
    interactive &&
    !glFailed &&
    !!geo &&
    (geo.points.length > 0 || geo.routes.length > 0 || (geo.legs?.length ?? 0) > 0);

  if (canInteractive && geo) {
    return (
      <MapErrorBoundary key={mapKey} onError={onFail} fallback={staticFigure}>
        <Suspense fallback={<MapLoading lang={lang} />}>
          <DayMapGL geo={geo} caption={caption} onFail={onFail} />
        </Suspense>
      </MapErrorBoundary>
    );
  }
  return staticFigure;
}

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
  mapExpected = false,
  interactive = false,
}: {
  day: Day;
  lang: Lang;
  collapsed: boolean;
  onToggle: (dayNumber: number) => void;
  mapExpected?: boolean; // the itinerary opts into maps; show a loader until day.map arrives
  interactive?: boolean; // user wants the interactive (MapLibre) map when possible
}) {
  const timeline = mergeTimeline(day);
  const toggle = () => onToggle(day.day_number);

  const mapCaption = fill(tr(lang, "dayMapCaption"), { index: day.day_number });

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
        <span className="day-band-body">
          <span className="day-meta">
            <span className="day-num">
              {tr(lang, "day")} {day.day_number}
            </span>
            <span className="day-date">{fmtDate(day.date, lang, true)}</span>
          </span>
          <span className="day-title">{day.title}</span>
          {day.city && <span className="day-city">{day.city}</span>}
        </span>
      </header>

      {!collapsed && (
        <>
          {day.description && <Clamp className="day-intro" text={day.description} />}

          {day.map ? (
            <MapView
              geo={day.map.geo ?? null}
              staticMap={day.map.main}
              interactive={interactive}
              caption={mapCaption}
              lang={lang}
            />
          ) : mapExpected ? (
            <MapLoading lang={lang} />
          ) : null}

          <ol className="timeline">
            {timeline.map((item, i) =>
              item.kind === "car" ? (
                <CarEventRow key={i} event={item.event} lang={lang} />
              ) : item.kind === "transport" ? (
                <TransportRow key={i} t={item.t} lang={lang} />
              ) : (
                <ActivityRow
                  key={i}
                  act={item.act}
                  lang={lang}
                  dayMap={day.map}
                  interactive={interactive}
                />
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

function ActivityRow({
  act,
  lang,
  dayMap,
  interactive = false,
}: {
  act: Activity;
  lang: Lang;
  dayMap?: DayMap; // present on top-level rows, for a place's area detail map
  interactive?: boolean;
}) {
  // A place's zoomed detail map (matched by title), drawn inline after it —
  // interactive when possible, falling back to the static PNG, like the overview.
  // Computed before any early return so the hooks below run unconditionally.
  const isPlace = act.type === "place";
  const dayGeo = dayMap?.geo ?? null;
  const areaStatic = isPlace ? dayMap?.areas.find((a) => a.title === act.title) ?? null : null;
  const areaGeoEntry = isPlace ? dayGeo?.areas.find((a) => a.title === act.title) : undefined;
  // Must be a STABLE reference across renders — MapView remounts the map when
  // `geo` identity changes, so a fresh object literal each render would tear the
  // map down before its markers render.
  const areaGeo = useMemo<MapGeo | null>(
    () =>
      areaGeoEntry && dayGeo
        ? {
            points: areaGeoEntry.points,
            routes: [],
            route_nodes: [],
            areas: [],
            accent: dayGeo.accent,
            bounds: areaGeoEntry.bounds,
          }
        : null,
    [areaGeoEntry, dayGeo],
  );
  const areaCaption = fill(tr(lang, "areaMapCaption"), { area: act.title });

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

  const provider = useMapProvider();
  // A multi-leg drive carries its Navigate links per VIA leg (not on the head).
  const multiLeg = act.type === "road" && roadLegs(act.start ?? "", act.waypoints ?? []).length > 1;
  const nav = multiLeg ? "" : activityNav(provider, act);
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
          <PinDisc label={act.map_pin} />
          {act.title}
          {act.type === "road" && act.off_road && (
            <span className="chip outline">{tr(lang, "offRoad")}</span>
          )}
          {act.type === "hike" && act.route_label && (
            <span className="chip outline">{act.route_label}</span>
          )}
          <ForecastChip act={act} lang={lang} />
        </div>
        <ActivityDetails act={act} lang={lang} nav={nav} />
        {act.type === "road" && <RoadVia act={act} lang={lang} />}
        {act.type === "point_of_interest" && <Links lang={lang} website={act.website} />}
      </div>
      {/* Nested sub-activities and the area map live outside .act-body so they
          sit in the .act grid: in the content column on desktop, and full-width
          below the badge on mobile (see the mobile block). */}
      {act.activities && act.activities.length > 0 && (
        <ol className="nested">
          {act.activities.map((sub, i) => (
            <ActivityRow key={i} act={sub} lang={lang} />
          ))}
        </ol>
      )}
      {(areaStatic || areaGeo) && (
        <div className="act-map">
          <MapView
            geo={areaGeo}
            staticMap={areaStatic}
            interactive={interactive}
            caption={areaCaption}
            lang={lang}
          />
        </div>
      )}
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
  } else if (act.type === "point_of_interest") {
    if (act.duration_display) bits.push(act.duration_display);
  } else if (act.type === "place") {
    if (act.duration_display) bits.push(act.duration_display);
  }

  // The address is rendered as its own clickable AddressLink (navigate by the
  // address text) rather than as a plain bit, so it complements the
  // coordinate-based Navigate link.
  const address =
    act.type === "meal" || act.type === "point_of_interest" ? act.address : undefined;

  // A hike's trailhead line, when the title is the hike name (not start → end).
  const trail =
    act.type === "hike" && act.name && act.start && act.end
      ? `${act.start} → ${act.end}`
      : "";
  const description =
    act.type === "point_of_interest" || act.type === "place" ? act.description : "";

  // Compose the meta line from nodes so the address stays a link amid the
  // text bits and the Navigate link, all "·"-separated.
  const chips: ReactNode[] = [];
  if (bits.length) chips.push(bits.join("  ·  "));
  if (address) chips.push(<AddressLink key="addr" address={address} />);
  if (nav) chips.push(<NavLink key="nav" lang={lang} href={nav} />);

  if (!chips.length && !trail && !description) return null;
  return (
    <div className="act-details">
      {chips.length > 0 && (
        <p className="chips-line">
          {chips.map((c, i) => (
            <Fragment key={i}>
              {i > 0 ? "  ·  " : ""}
              {c}
            </Fragment>
          ))}
        </p>
      )}
      {trail && <p className="trail">{trail}</p>}
      {description && <Clamp className="desc" text={description} />}
    </div>
  );
}

// The VIA breakdown for a multi-leg drive: one row per named leg with its own
// duration/distance and a Navigate link.
function RoadVia({ act, lang }: { act: Activity; lang: Lang }) {
  const provider = useMapProvider();
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
        const nav = navUrl(provider, leg.destCoord, leg.dest ?? "");
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
  const provider = useMapProvider();
  const booking = transportBooking(t, lang);
  const nav = navUrl(provider, t.start_coordinate ?? t.coordinate, t.start);
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
  const provider = useMapProvider();
  const pickup = event.kind === "car_pickup";
  // Descriptor "company · car_model (Type)", mirroring the PDF's _car_descriptor.
  let who = [event.company, event.car_model].filter(Boolean).join("  ·  ");
  if (event.car_type_label) who = who ? `${who} (${event.car_type_label})` : event.car_type_label;
  const bits = [
    event.location,
    event.duration_display,
    who,
    event.booking_number ? fill(tr(lang, "ref"), { ref: event.booking_number }) : "",
  ].filter(Boolean);
  const nav = navUrl(provider, event.coordinate, event.location);
  return (
    <li className="act car">
      <Gutter
        label={pickup ? tr(lang, "pickUp") : tr(lang, "dropOff")}
        start={event.start_time}
        end={event.end_time}
        startTz={event.start_tz_label}
        endTz={event.end_tz_label}
      />
      <div className="act-body">
        <div className="act-title">{tr(lang, pickup ? "pickUpCar" : "dropOffCar")}</div>
        {(bits.length > 0 || nav) && (
          <p className="chips-line">
            {bits.join("  ·  ")}
            {nav ? (
              <>
                {bits.length ? "  ·  " : ""}
                <NavLink lang={lang} href={nav} />
              </>
            ) : null}
          </p>
        )}
      </div>
    </li>
  );
}

function StayBar({ day, lang }: { day: Day; lang: Lang }) {
  const provider = useMapProvider();
  // The night's moon phase (opt-in via defaults.show_moon_phase), shown as just
  // the emoji before "Tonight:", with the phase name on hover — via the app's
  // CSS `data-tip` bubble (the native `title` proved unreliable, see Options).
  const moon = day.moon ? (
    <span className="moon-phase" data-tip={tr(lang, day.moon.key as LabelKey)}>
      {day.moon.emoji}
    </span>
  ) : null;
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
    const where = [s.name, s.city].filter(Boolean).join(", ");
    const nav = navUrl(provider, s.coordinate, s.address, where);
    // Address (clickable, navigate-by-address), booked-via, then the
    // coordinate-based Navigate link — all "·"-separated.
    const subChips: ReactNode[] = [];
    if (s.address) subChips.push(<AddressLink key="addr" address={s.address} />);
    if (bookedVia) subChips.push(bookedVia);
    if (nav) subChips.push(<NavLink key="nav" lang={lang} href={nav} />);
    return (
      <footer className="stay-bar">
        <div className="stay-line">
          <span>
            {moon}
            <strong className="tonight">{tr(lang, "tonight")}:</strong> <PinDisc label={s.map_pin} />
            <strong>{s.name}</strong>
            {s.city ? ` (${s.city})` : ""}
          </span>
          {progress && <span className="stay-progress">{progress}</span>}
        </div>
        {subChips.length > 0 && (
          <p className="stay-sub">
            {subChips.map((c, i) => (
              <Fragment key={i}>
                {i > 0 ? "  ·  " : ""}
                {c}
              </Fragment>
            ))}
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
            {moon}
            <strong className="tonight">{tr(lang, "tonight")}:</strong> {tr(lang, "aboard")}{" "}
            <strong>{leg.title}</strong>
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
      {moon}
      <strong className="tonight">{tr(lang, "tonight")}:</strong> {tr(lang, "nowhere")}
    </footer>
  );
}
