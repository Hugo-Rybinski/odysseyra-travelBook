import { Fragment, lazy, Suspense, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import type {
  Activity,
  CarEvent,
  Day,
  DayMap,
  MapGeo,
  RenderedMap,
  TransportLeg,
} from "../types/resolved";
import { fill, fmtDate, fmtWeekdayRuns, tr, type Lang, type LabelKey } from "./format";
import { Clamp } from "./Clamp";
import { ForecastChip } from "./forecast";
import { GpxBuildLink, GpxDownload, GpxDownloadLink, HikeTrackFigure } from "./HikeTrack";
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
// `mid` marks a disc that sits *inside* a line rather than leading it (a drive's
// arrival, in the title and in the VIA rows): it needs a gap on its left as well
// as the right one every disc has, and in `.act-title` — a flex row — the space
// in the text before it is collapsed away, so the margin is the only thing left.
function PinDisc({ label, mid }: { label: string | null | undefined; mid?: boolean }) {
  if (!label) return null;
  return (
    <span className={mid ? "pin-disc pin-disc-mid" : "pin-disc"} aria-hidden>
      {label}
    </span>
  );
}

// An activity's title, led by its map-pin disc.
//
// A drive is the one activity that is *two* places, so when it pins its arrival
// as well the discs split to sit beside the names they label —
// `(1) Amboise → (4) Sarlat-la-Canéda`. Both leading the line would read as two
// labels on the departure. Mirrors pdf/days.py's `_road_title`; keep in step.
function ActivityTitle({ act }: { act: Activity }) {
  const legs = act.type === "road" ? roadLegs(act.start ?? "", act.waypoints ?? []) : [];
  const arrival = legs.length ? legs[legs.length - 1] : null;
  // Only a *named* arrival is ever pinned, so an unnamed one falls through to
  // the plain title on its own.
  if (arrival?.destPin && act.start && arrival.dest)
    return (
      <>
        <PinDisc label={act.map_pin} />
        {`${act.start} → `}
        <PinDisc label={arrival.destPin} mid />
        {arrival.dest}
      </>
    );
  return (
    <>
      <PinDisc label={act.map_pin} />
      {act.title}
    </>
  );
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

// One map slot (used for both the day overview and each area detail map).
//
// The two renderings are **alternatives chosen in Options, not a fallback
// chain**: with interactive maps on the slot is the MapLibre map or nothing, and
// the pre-rendered PNG appears only with the toggle off. A GL failure therefore
// says so rather than quietly substituting the static image — which the user
// switched away from, and which can't be panned or zoomed, so silently swapping
// it in reads as "the map lost its controls". A fresh geo re-tries via the error
// boundary + remount key.
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

  const hasGeo =
    !!geo && (geo.points.length > 0 || geo.routes.length > 0 || (geo.legs?.length ?? 0) > 0);

  if (interactive) {
    // Nothing locatable — there's no map to draw either way, so stay silent
    // rather than report a failure that didn't happen.
    if (!hasGeo || !geo) return null;
    const unavailable = <p className="section-empty">{tr(lang, "mapUnavailable")}</p>;
    if (glFailed) return unavailable;
    return (
      <MapErrorBoundary key={mapKey} onError={onFail} fallback={unavailable}>
        <Suspense fallback={<MapLoading lang={lang} />}>
          <DayMapGL geo={geo} caption={caption} onFail={onFail} />
        </Suspense>
      </MapErrorBoundary>
    );
  }
  return staticMap ? <MapFigure rendered={staticMap} caption={caption} /> : null;
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

  // Which drive of the day each road is — the address the engine wants for a
  // leg's GPX (see render/routeExport.ts). Counted over the day's own
  // activities, so buffers woven into the resolved timeline don't shift it, and
  // it matches "the Nth road of day D" in the input JSON.
  const roadOrdinals = new Map<Activity, number>();
  day.activities
    .filter((a) => a.type === "road")
    .forEach((a, i) => roadOrdinals.set(a, i));

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
          <BankHolidayBanner day={day} lang={lang} />

          <SunTimes day={day} lang={lang} />

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
                  dayIndex={day.day_number - 1}
                  roadIndex={roadOrdinals.get(item.act)}
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
  | { kind: "transport"; t: TransportLeg; sort: string }
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
  dayIndex,
  roadIndex,
}: {
  act: Activity;
  lang: Lang;
  dayMap?: DayMap; // present on top-level rows, for a place's area detail map
  interactive?: boolean;
  // Where this row sits, for a road leg's on-demand GPX. Absent on a nested row
  // (a road is never nested), which simply leaves the leg without that link.
  dayIndex?: number;
  roadIndex?: number;
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
          <ActivityTitle act={act} />
          {act.type === "road" && (act.off_road || singleLegOffRoad(act)) && (
            <span className="chip outline">{tr(lang, "offRoad")}</span>
          )}
          {act.type === "hike" && act.route_label && (
            <span className="chip outline">{act.route_label}</span>
          )}
          <ForecastChip act={act} lang={lang} />
        </div>
        <ActivityDetails
          act={act}
          lang={lang}
          nav={nav}
          dayIndex={dayIndex}
          roadIndex={roadIndex}
        />
        {act.type === "road" && (
          <RoadVia act={act} lang={lang} dayIndex={dayIndex} roadIndex={roadIndex} />
        )}
        {act.type === "point_of_interest" && <Links lang={lang} website={act.website} />}
      </div>
      {/* A hike's embedded GPX: the trail map + elevation profile, sitting in
          the .act grid (like the nested list and the area map) rather than in
          .act-body, so it goes full width under the badge on a phone. Renders
          nothing unless the hike has a `track`. */}
      {act.type === "hike" && act.track && (
        <div className="act-map">
          <HikeTrackFigure act={act} lang={lang} interactive={interactive} />
        </div>
      )}
      {/* Nested sub-activities and the area map live outside .act-body so they
          sit in the .act grid: in the content column on desktop, and full-width
          below the badge on mobile (see the mobile block). */}
      {act.activities && act.activities.length > 0 && (
        <ol className="nested">
          {act.activities.map((sub, i) => (
            <ActivityRow key={i} act={sub} lang={lang} interactive={interactive} />
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

// A point of interest's opening days and hours, as one row led by an accent
// label — `Open  Tue–Sun · 09:30–12:30, 14:00–18:00`. Mirrors the PDF's
// `_opening_line` (pdf/days.py) and sits where it does, under the address line.
// Either half may be missing: no days means every day, no hours means all day,
// so only what is known is printed. Nothing here flags a visit that falls
// *outside* the hours — that's the validator's warning, since the fix belongs in
// the itinerary rather than in the page.
function Opening({ act, lang }: { act: Activity; lang: Lang }) {
  const opening = act.opening;
  if (!opening) return null;
  const parts: string[] = [];
  if (opening.day_runs?.length) parts.push(fmtWeekdayRuns(opening.day_runs, lang));
  if (opening.hours_display) parts.push(opening.hours_display);
  if (!parts.length) return null;
  return (
    <p className="act-opening">
      <span className="act-opening-label">{tr(lang, "open")}</span>
      {parts.join("  ·  ")}
    </p>
  );
}

function ActivityDetails({
  act,
  lang,
  nav,
  dayIndex,
  roadIndex,
}: {
  act: Activity;
  lang: Lang;
  nav: string;
  dayIndex?: number;
  roadIndex?: number;
}) {
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
  // Every activity type the model gives a `description` to — road, poi, place
  // and hike (the PDF prints all four; the hike was once missed here). It
  // follows the trail line, so a hike reads title → chips → trailhead → prose;
  // a road's lands above its VIA legs, as in the PDF.
  const described =
    act.type === "point_of_interest" ||
    act.type === "place" ||
    act.type === "hike" ||
    act.type === "road";
  const description = described ? act.description : "";
  // The guidebook page reference rides along with the description, on the same
  // four types. It's a pill appended at the *end of the description text* (as in
  // the PDF's `_para_with_pill`), falling back to a line of its own when the
  // activity has pages but no prose.
  const guidebook = described ? act.guidebook_pages : "";
  const pill = guidebook ? (
    <span className="chip guidebook">{fill(tr(lang, "guidebook"), { pages: guidebook })}</span>
  ) : null;

  // Compose the meta line from nodes so the address stays a link amid the
  // text bits and the Navigate link, all "·"-separated.
  const chips: ReactNode[] = [];
  if (bits.length) chips.push(bits.join("  ·  "));
  if (address) chips.push(<AddressLink key="addr" address={address} />);
  if (nav) chips.push(<NavLink key="nav" lang={lang} href={nav} />);
  // A hike carrying a GPX offers the file itself, alongside its other inline
  // links (renders nothing for every other activity).
  if (act.type === "hike" && act.track?.gpx)
    chips.push(<GpxDownloadLink key="gpx" act={act} lang={lang} />);
  // A drive's GPX normally sits on its leg's VIA row — but a plain one-leg
  // drive draws no VIA list, so the link had nowhere to go and simply vanished.
  // It is promoted to the road's own line instead, the same way a single leg's
  // off-road flag is promoted to the road's chip. (Only when there really is no
  // VIA row: a one-leg drive with a pinned arrival gets one, and would
  // otherwise offer the file twice.)
  if (act.type === "road") {
    const legs = roadLegs(act.start ?? "", act.waypoints ?? []);
    if (legs.length === 1 && !legs[0].destPin) {
      if (legs[0].gpx)
        chips.push(
          <GpxDownload
            key="gpx"
            base64={legs[0].gpx}
            name={legs[0].dest || act.title}
            lang={lang}
          />,
        );
      else if (dayIndex != null && roadIndex != null)
        chips.push(
          <GpxBuildLink key="gpx" dayIndex={dayIndex} roadIndex={roadIndex} legIndex={0} lang={lang} />,
        );
    }
  }

  if (!chips.length && !trail && !description && !guidebook && !act.opening) return null;
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
      <Opening act={act} lang={lang} />
      {trail && <p className="trail">{trail}</p>}
      {description ? (
        <Clamp className="desc" text={description} trailing={pill} />
      ) : (
        pill && <p className="desc">{pill}</p>
      )}
    </div>
  );
}

// A single-leg drive draws no VIA list, so a per-leg off-road flag would have
// nowhere to show — it is promoted to the road's own chip instead (mirrors
// pdf/days.py's `_details_road`).
function singleLegOffRoad(act: Activity): boolean {
  const legs = roadLegs(act.start ?? "", act.waypoints ?? []);
  return legs.length === 1 && legs[0].offRoad;
}

// The VIA breakdown for a multi-leg drive: one row per leg carrying both ends'
// map pins, its duration/distance, a Navigate link and — when the leg was
// recorded — the GPX it was drawn from.
//
// A junction is one place written twice (it ends one leg and starts the next),
// so its disc shows on both rows and the numbers chain (1)→(2), (2)→(3) …, each
// beside the town it names.
//
// A single-leg drive normally shows nothing here (its title says the same
// thing), but a pinned arrival needs a row to be read against: a pin number is
// only legible beside the place it points at. Mirrors pdf/days.py's
// `_road_waypoints` — keep the two in step.
function RoadVia({
  act,
  lang,
  dayIndex,
  roadIndex,
}: {
  act: Activity;
  lang: Lang;
  dayIndex?: number;
  roadIndex?: number;
}) {
  const provider = useMapProvider();
  const legs = roadLegs(act.start ?? "", act.waypoints ?? [], act.map_pin ?? null);
  if (legs.length <= 1 && !legs.some((l) => l.destPin)) return null;
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
              <PinDisc label={leg.srcPin} />
              {`${leg.src || "?"} → `}
              <PinDisc label={leg.destPin} mid />
              {leg.dest || "?"}
            </span>
            {meta.length > 0 && <span className="via-meta">{meta.join("  ·  ")}</span>}
            {/* the same small chip the road-level flag uses, on the rough leg */}
            {leg.offRoad && <span className="chip outline">{tr(lang, "offRoad")}</span>}
            {/* the shared NavLink, so this row's links match the ones on every
                other activity — and the GPX buttons sitting right beside it */}
            {nav && <NavLink lang={lang} href={nav} />}
            {/* the file this leg carries, or — for a leg with none — one the
                app builds from the drawn route, which says so in its label */}
            {leg.gpx ? (
              <GpxDownload base64={leg.gpx} name={leg.dest || act.title} lang={lang} />
            ) : dayIndex != null && roadIndex != null ? (
              <GpxBuildLink
                dayIndex={dayIndex}
                roadIndex={roadIndex}
                legIndex={i}
                lang={lang}
              />
            ) : null}
          </p>
        );
      })}
    </div>
  );
}

function transportBooking(t: TransportLeg, lang: Lang): string {
  const bits: string[] = [];
  if (t.type === "plane" && t.flight_number)
    bits.push(fill(tr(lang, "flight"), { number: t.flight_number }));
  else if (t.type === "train" && t.train_number)
    bits.push(fill(tr(lang, "train"), { number: t.train_number }));
  if (t.booking_number) bits.push(fill(tr(lang, "ref"), { ref: t.booking_number }));
  if (t.booking_source) bits.push(fill(tr(lang, "bookedVia"), { source: t.booking_source }));
  return bits.join("  ·  ");
}

function TransportRow({ t, lang }: { t: TransportLeg; lang: Lang }) {
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
        {t.description && <Clamp className="act-note" text={t.description} />}
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
        {/* The owning rental's note, repeated on both of its events — this is
            where you read it on the day. Mirrors pdf/days.py's car row. */}
        {event.description && <Clamp className="act-note" text={event.description} />}
      </div>
    </li>
  );
}

// The day's sun times, opening the day's body above the intro (on unless
// defaults.show_sun_times is off, and absent when there's no coordinate to
// compute them for). The `sunTimes` template is the same one the PDF localizes,
// so both read alike; it spells the labels out, so it needs no tooltip.
//
// With `show_moon_phase` on as well, the night's phase closes the same line —
// today's sky in one reading. The stay bar then drops it (see `StayBar`), so the
// day shows it once. The PDF does the same, bar a width fallback its header band
// needs and this line doesn't.
function SunTimes({ day, lang }: { day: Day; lang: Lang }) {
  if (!day.sun) return null;
  const { sunrise, sunset } = day.sun;
  return (
    <p className="day-sun">
      {day.moon
        ? fill(tr(lang, "sunTimesMoon"), {
            sunrise,
            sunset,
            emoji: day.moon.emoji,
            moon: tr(lang, day.moon.key as LabelKey),
          })
        : fill(tr(lang, "sunTimes"), { sunrise, sunset })}
    </p>
  );
}

// A public-holiday call-out opening the day's body — the PDF's `_notice` strip,
// which sits in the same spot (ahead of the intro and the map): what's open and
// how things run changes, so it's the first thing read.
function BankHolidayBanner({ day, lang }: { day: Day; lang: Lang }) {
  if (!day.bank_holiday) return null;
  return (
    <p className="day-holiday">
      <span className="day-holiday-label">
        <span aria-hidden>⚠️</span> {tr(lang, "bankHoliday")}
      </span>
      <span className="day-holiday-note">{tr(lang, "bankHolidayNote")}</span>
    </p>
  );
}

function StayBar({ day, lang }: { day: Day; lang: Lang }) {
  const provider = useMapProvider();
  // The night's moon phase (on by default; defaults.show_moon_phase opts out),
  // shown as just the emoji before "Tonight:", with the name on hover — via the
  // CSS `data-tip` bubble (the native `title` proved unreliable, see Options).
  // Only when the sun-times line above isn't already naming it: with both
  // switches on that line closes with the phase, and repeating it a few
  // centimetres below would just be noise.
  const moon = day.moon && !day.sun ? (
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
        {/* The stay's note (a door code, where to park). The PDF's bar caps it
            at two lines to protect the page foot; here Clamp plays that role,
            with the full text one tap away. */}
        {s.description && <Clamp className="stay-note" text={s.description} />}
        <Links lang={lang} website={s.website} reservation={s.booking_link} />
      </footer>
    );
  }
  if (day.night_transport) {
    const leg = day.night_transport;
    // The leg is normally also a row in the day's itinerary above (both the
    // day's `transports` and its `night_transport` select on the departure
    // date), and that row already shows its note — so the bar doesn't repeat
    // it. Matched on the departure stamp + route because the resolved doc holds
    // two independently serialized copies of the same leg. Mirrors
    // pdf/days.py's `_day_stay`.
    const legKey = (t: TransportLeg) => `${t.start_date}|${t.start_time}|${t.title}`;
    const alsoListed = day.transports.some((t) => legKey(t) === legKey(leg));
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
        {!alsoListed && leg.description && (
          <Clamp className="stay-note" text={leg.description} />
        )}
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
