import type { SrcActivity, SrcActivityType, SrcCoordinate, SrcWaypoint } from "../../types/source";
import {
  ACTIVITY_FIELDS,
  ACTIVITY_TYPE_LABELS,
  ACTIVITY_TYPES,
  newActivity,
  newWaypoint,
  SCHEDULED_FIELDS,
  WAYPOINT_FIELDS,
} from "../schema";
import { ArrayEditor } from "../fields/ArrayEditor";
import { CoordinateField } from "../fields/CoordinateField";
import { FieldList } from "../fields/FieldList";

type Rec = Record<string, unknown>;

// A short title for an activity, used in array-item headers and nav.
export function activityTitle(a: SrcActivity, index: number): string {
  const label = ACTIVITY_TYPE_LABELS[a.type];
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
          ? `${label}: ${a.meal_type}`
          : label;
    case "buffer":
      return a.duration ? `${label} (${a.duration})` : label;
    default:
      return `Activity ${index + 1}`;
  }
}

const SCHED_KEYS = ["start_time", "end_time", "duration", "start_tz", "end_tz"] as const;

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
  const type = activity.type;
  const rec = activity as unknown as Rec;
  const set = (next: Rec) => onChange(next as unknown as SrcActivity);

  const specs = type === "buffer" ? ACTIVITY_FIELDS.buffer : [...SCHEDULED_FIELDS, ...ACTIVITY_FIELDS[type]];

  // What may be nested, per container type (see README nesting rules).
  const nestedTypes: readonly SrcActivityType[] =
    type === "point_of_interest" || type === "place"
      ? (["point_of_interest", "hike", "meal"] as const)
      : type === "road" || type === "hike"
        ? (["meal"] as const)
        : [];

  return (
    <div className="activity-form">
      <label className="edit-field">
        <span className="edit-field-label">Type</span>
        <select
          className="edit-input"
          value={type}
          onChange={(e) => onChange(changeType(activity, e.target.value as SrcActivityType))}
        >
          {ACTIVITY_TYPES.filter((t) => allowedTypes.includes(t)).map((t) => (
            <option key={t} value={t}>
              {ACTIVITY_TYPE_LABELS[t]}
            </option>
          ))}
        </select>
      </label>

      <FieldList specs={specs} value={rec} path={path} onChange={set} />

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
          <h4>Waypoints</h4>
          <ArrayEditor<SrcWaypoint>
            items={activity.waypoints ?? []}
            onChange={(wp) => set({ ...rec, waypoints: wp })}
            basePath={`${path}.waypoints`}
            itemTitle={(w, i) => w.location || `Waypoint ${i + 1}`}
            add={[{ label: "waypoint", make: newWaypoint }]}
            emptyLabel="No waypoints — a road needs at least one (the arrival)."
            renderItem={(w, _i, onItemChange, itemPath) => (
              <>
                <FieldList
                  specs={WAYPOINT_FIELDS}
                  value={w as unknown as Rec}
                  path={itemPath}
                  onChange={(next) => onItemChange(next as unknown as SrcWaypoint)}
                />
                <CoordinateField
                  path={`${itemPath}.coordinate`}
                  value={w.coordinate}
                  geocodeQuery={w.location}
                  onChange={(c: SrcCoordinate | undefined) => onItemChange({ ...w, coordinate: c })}
                />
              </>
            )}
          />
        </section>
      )}

      {allowNesting && nestedTypes.length > 0 && (
        <section className="sub-array">
          <h4>Nested activities</h4>
          <ArrayEditor<SrcActivity>
            items={(rec.activities as SrcActivity[] | undefined) ?? []}
            onChange={(acts) => set({ ...rec, activities: acts })}
            basePath={`${path}.activities`}
            defaultOpen={false}
            itemTitle={activityTitle}
            add={nestedTypes.map((t) => ({
              label: ACTIVITY_TYPE_LABELS[t].toLowerCase(),
              make: () => newActivity(t),
            }))}
            emptyLabel="No nested activities."
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
