import type { SrcActivity, SrcActivityType, SrcCoordinate, SrcWaypoint } from "../../types/source";
import {
  ACTIVITY_FIELDS,
  ACTIVITY_TYPE_LABELS,
  ACTIVITY_TYPES,
  newActivity,
  newWaypoint,
  PLACE_SCHEDULED_FIELDS,
  SCHEDULED_FIELDS,
  WAYPOINT_FIELDS,
} from "../schema";
import { useT, type TFn } from "../../i18n";
import { directionsUrl, useMapProvider } from "../../render/nav";
import { ArrayEditor } from "../fields/ArrayEditor";
import { CoordinateField } from "../fields/CoordinateField";
import { FieldFindings } from "../fields/FieldFindings";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

// A short title for an activity, used in array-item headers and nav. `t` is
// threaded in so the type label (and meal type) localize with the UI language.
export function activityTitle(a: SrcActivity, index: number, t: TFn): string {
  const label = t(ACTIVITY_TYPE_LABELS[a.type]);
  switch (a.type) {
    case "road":
      return a.start ? `${label}: ${a.start} → …` : label;
    case "point_of_interest":
    case "place":
    case "hike":
      return a.name ? `${label}: ${a.name}` : label;
    case "meal":
      return a.restaurant || a.area
        ? `${label}: ${a.restaurant || a.area}`
        : a.meal_type
          ? `${label}: ${t(a.meal_type)}`
          : label;
    case "buffer":
      return a.duration ? `${label} (${a.duration})` : label;
    default:
      return t("Activity {n}", { n: index + 1 });
  }
}

const SCHED_KEYS = ["start_time", "end_time", "duration", "start_tz", "end_tz"] as const;

// The amber "check online to fill it" hint: names what's missing (travel time /
// distance / both) and links to the given directions URL when one is available.
function GapWarning({
  missingTime,
  missingDist,
  href,
}: {
  missingTime: boolean;
  missingDist: boolean;
  href: string;
}) {
  const t = useT();
  const message =
    missingTime && missingDist
      ? t("Travel time and distance are missing.")
      : missingTime
        ? t("Travel time is missing.")
        : t("Distance is missing.");
  return (
    <p className="road-check">
      <span aria-hidden>⚠️</span> {message}
      {href && (
        <>
          {" "}
          <a className="road-check-link" href={href} target="_blank" rel="noreferrer">
            {t("Check online to fill it.")}
          </a>
        </>
      )}
    </p>
  );
}

function srcCoord(c?: SrcCoordinate) {
  return c && c.lat != null && c.long != null
    ? { lat: c.lat, long: c.long, show_on_map: c.show_on_map ?? true }
    : null;
}

interface LegGap {
  index: number; // the waypoint the leg ends at
  origin: string; // the previous named point, else the road's start
  destName: string;
  destCoord: { lat: number; long: number; show_on_map: boolean } | null;
  missingTime: boolean;
  missingDist: boolean;
}

// One entry per NAMED waypoint (a leg end), summing any preceding unnamed
// (route-shaping) waypoints into that leg — mirroring the viewer's roadLegs
// merge — so a leg counts as complete if its figures sit on any of its points.
function roadLegGaps(activity: SrcActivity): LegGap[] {
  if (activity.type !== "road") return [];
  const wps = activity.waypoints ?? [];
  const out: LegGap[] = [];
  let origin = (activity.start ?? "").trim();
  let hasDur = false;
  let hasDist = false;
  for (let i = 0; i < wps.length; i++) {
    const w = wps[i];
    if ((w.duration ?? "").trim() !== "") hasDur = true;
    if (w.distance_km != null) hasDist = true;
    if ((w.location ?? "").trim() !== "") {
      out.push({
        index: i,
        origin,
        destName: w.location ?? "",
        destCoord: srcCoord(w.coordinate),
        missingTime: !hasDur,
        missingDist: !hasDist,
      });
      origin = (w.location ?? "").trim() || origin;
      hasDur = false;
      hasDist = false;
    }
  }
  return out;
}

// A single-leg road (0/1 waypoints) whose driving time and/or distance is blank:
// warn on the road with a start → arrival directions link. Multi-leg roads warn
// per waypoint instead (see the waypoint editor below).
function RoadCheckOnline({ activity }: { activity: SrcActivity }) {
  const provider = useMapProvider();
  if (activity.type !== "road") return null;
  const wps = activity.waypoints ?? [];
  if (wps.length > 1) return null;

  const hasLegDist = wps.some((w) => w.distance_km != null);
  const hasLegDur = wps.some((w) => (w.duration ?? "").trim() !== "");
  const missingDist = activity.distance_km == null && !hasLegDist;
  const missingTime = (activity.duration ?? "").trim() === "" && !hasLegDur;
  if (!missingDist && !missingTime) return null;

  const last = wps.length ? wps[wps.length - 1] : undefined;
  const href = directionsUrl(provider, activity.start, srcCoord(last?.coordinate), last?.location);
  return <GapWarning missingTime={missingTime} missingDist={missingDist} href={href} />;
}

// Carry the scheduling fields across a type change so re-typing an activity
// doesn't wipe its times.
function changeType(prev: SrcActivity, type: SrcActivityType): SrcActivity {
  const base = newActivity(type) as unknown as Rec;
  if (type !== "buffer") {
    const prevRec = prev as unknown as Rec;
    for (const k of SCHED_KEYS) {
      const v = prevRec[k];
      if (v !== undefined) base[k] = v;
    }
  }
  return base as unknown as SrcActivity;
}

export interface ActivityFormProps {
  activity: SrcActivity;
  path: string;
  onChange: (next: SrcActivity) => void;
  // Which types this slot may hold (top level: all six; nested varies).
  allowedTypes: readonly SrcActivityType[];
  // Nested activities can't nest further (the model is one level deep).
  allowNesting: boolean;
}

export function ActivityForm({ activity, path, onChange, allowedTypes, allowNesting }: ActivityFormProps) {
  const t = useT();
  const provider = useMapProvider();
  const type = activity.type;
  const rec = activity as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcActivity);

  // Per-leg gaps for a multi-leg road, keyed by the waypoint they end at, so the
  // "check online" hint sits on the waypoint that's missing its figures.
  const legGaps = roadLegGaps(activity);
  const multiLegRoad = type === "road" && (activity.waypoints ?? []).length > 1;

  // A hand-edited draft may carry an unknown/absent type; fall back to the
  // scheduling fields only (ACTIVITY_FIELDS[type] would be undefined → a
  // "not iterable" spread crash) so the form still renders and the type finding
  // can be fixed.
  const typeFields = ACTIVITY_FIELDS[type] ?? [];
  const scheduled = type === "place" ? PLACE_SCHEDULED_FIELDS : SCHEDULED_FIELDS;
  const specs = type === "buffer" ? ACTIVITY_FIELDS.buffer : [...scheduled, ...typeFields];

  // What may be nested, per container type (see README nesting rules).
  const nestedTypes: readonly SrcActivityType[] =
    type === "point_of_interest" || type === "place"
      ? (["point_of_interest", "hike", "meal"] as const)
      : type === "road" || type === "hike"
        ? (["meal"] as const)
        : [];

  return (
    <div className="activity-form">
      <div className="box-findings">
        <FieldFindings path={path} />
      </div>
      <div className="edit-field-wrap">
        <label className="edit-field">
          <span className="edit-field-label">{t("Type")}</span>
          <select
            className="edit-input"
            value={type}
            onChange={(e) => onChange(changeType(activity, e.target.value as SrcActivityType))}
          >
            {ACTIVITY_TYPES.filter((ty) => allowedTypes.includes(ty)).map((ty) => (
              <option key={ty} value={ty}>
                {t(ACTIVITY_TYPE_LABELS[ty])}
              </option>
            ))}
          </select>
        </label>
        <FieldFindings path={`${path}.type`} />
      </div>

      <FieldList specs={specs} value={rec} path={path} onChange={set} />

      {type === "road" && <RoadCheckOnline activity={activity} />}

      {type !== "buffer" && (
        <CoordinateField
          path={`${path}.coordinate`}
          value={activity.coordinate}
          geocodeQuery={
            type === "road"
              ? activity.start
              : type === "hike"
                ? activity.start || activity.name
                : type === "point_of_interest"
                  ? activity.address || activity.name
                  : type === "place"
                    ? activity.name
                    : activity.address || activity.restaurant || activity.area
          }
          onChange={(c) => set({ ...rec, coordinate: c })}
        />
      )}

      {type === "road" && (
        <section className="sub-array">
          <h4>{t("Waypoints")}</h4>
          <div className="box-findings">
            <FieldFindings path={`${path}.waypoints`} />
          </div>
          <ArrayEditor<SrcWaypoint>
            items={activity.waypoints ?? []}
            onChange={(wp) => set({ ...rec, waypoints: wp })}
            basePath={`${path}.waypoints`}
            defaultOpen={false}
            itemTitle={(w, i) => w.location || t("Waypoint {n}", { n: i + 1 })}
            add={[{ label: t("waypoint"), make: newWaypoint }]}
            emptyLabel={t("No waypoints — a road needs at least one (the arrival).")}
            renderItem={(w, i, onItemChange, itemPath) => {
              // On a multi-leg road, this named waypoint's leg may be missing its
              // travel time / distance — hint here (not on the road) with a link
              // to the map for this leg (previous point → this waypoint).
              const gap = multiLegRoad ? legGaps.find((l) => l.index === i) : undefined;
              return (
                <>
                  <div className="box-findings">
                    <FieldFindings path={itemPath} />
                  </div>
                  <FieldList
                    specs={WAYPOINT_FIELDS}
                    value={w as unknown as Rec}
                    path={itemPath}
                    onChange={(next) => onItemChange(next as unknown as SrcWaypoint)}
                  />
                  {gap && (gap.missingTime || gap.missingDist) && (
                    <GapWarning
                      missingTime={gap.missingTime}
                      missingDist={gap.missingDist}
                      href={directionsUrl(provider, gap.origin, gap.destCoord, gap.destName)}
                    />
                  )}
                  <CoordinateField
                    path={`${itemPath}.coordinate`}
                    value={w.coordinate}
                    geocodeQuery={w.location}
                    onChange={(c: SrcCoordinate | undefined) => onItemChange({ ...w, coordinate: c })}
                  />
                </>
              );
            }}
          />
        </section>
      )}

      {allowNesting && nestedTypes.length > 0 && (
        <section className="sub-array">
          <h4>{t("Nested activities")}</h4>
          <ArrayEditor<SrcActivity>
            items={(rec.activities as SrcActivity[] | undefined) ?? []}
            onChange={(acts) => set({ ...rec, activities: acts })}
            basePath={`${path}.activities`}
            defaultOpen={false}
            itemTitle={(a, i) => activityTitle(a, i, t)}
            add={nestedTypes.map((ty) => ({
              label: t(ACTIVITY_TYPE_LABELS[ty]).toLowerCase(),
              make: () => newActivity(ty),
            }))}
            emptyLabel={t("No nested activities.")}
            renderItem={(a, _i, onItemChange, itemPath) => (
              <ActivityForm
                activity={a}
                path={itemPath}
                onChange={onItemChange}
                allowedTypes={nestedTypes}
                allowNesting={false}
              />
            )}
          />
        </section>
      )}
    </div>
  );
}
