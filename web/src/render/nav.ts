// Client-side helpers that mirror bits of the Python renderer/model so the UI
// can offer the same links and leg breakdown without another round-trip.
import type { Activity, Coordinate, Transport, Waypoint } from "../types/resolved";

// A Google Maps URL to the first available location — the exact coordinate, else
// the first non-empty name — mirroring models.geo.maps_url. "" when nothing is
// locatable. The same URL opens navigation on mobile and Maps on desktop.
export function navUrl(
  coordinate: Coordinate | null | undefined,
  ...names: (string | null | undefined)[]
): string {
  let query = "";
  if (coordinate) {
    query = `${coordinate.lat},${coordinate.long}`;
  } else {
    const name = names.find((n) => n && n.trim());
    if (!name) return "";
    query = name.trim();
  }
  return "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(query);
}

export interface RoadLeg {
  src: string;
  dest: string | null; // null for a trailing unnamed arrival
  durationMin: number | null;
  distanceKm: number | null;
  destCoord: Coordinate | null;
}

// Collapse a road's waypoints into display legs, mirroring
// pdf.days.road_display_legs: unnamed (route-shaping) waypoints merge forward
// into the next named leg, summing their duration/distance.
export function roadLegs(start: string, waypoints: Waypoint[]): RoadLeg[] {
  const legs: RoadLeg[] = [];
  let prev = start;
  let dur = 0;
  let dist = 0;
  let hasDur = false;
  let hasDist = false;
  let pending = false;
  let coord: Coordinate | null = null;

  const flush = (dest: string | null) => {
    legs.push({
      src: prev,
      dest,
      durationMin: hasDur ? dur : null,
      distanceKm: hasDist ? dist : null,
      destCoord: coord,
    });
    prev = dest ?? prev;
    dur = 0;
    dist = 0;
    hasDur = false;
    hasDist = false;
    pending = false;
    coord = null;
  };

  for (const wp of waypoints) {
    pending = true;
    coord = wp.coordinate;
    if (wp.duration_min != null) {
      dur += wp.duration_min;
      hasDur = true;
    }
    if (wp.distance_km != null) {
      dist += wp.distance_km;
      hasDist = true;
    }
    if (wp.location) flush(wp.location);
  }
  if (pending) flush(null);
  return legs;
}

/** Minutes → "1h30" / "45 min" (mirrors models.parsers._format_duration). */
export function fmtDurationMin(min: number | null): string {
  if (min == null || min === 0) return "";
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h}h${String(m).padStart(2, "0")}` : `${h}h`;
}

/** A transport's time line with tz labels and the arrival day-offset ("+1"). */
export function transportTimes(t: Transport): string {
  const stamp = (time: string | null, tz: string, off = 0) => {
    if (!time) return "";
    return time + (tz ? ` ${tz}` : "") + (off ? ` +${off}` : "");
  };
  let line = "";
  if (t.start_time && t.end_time) {
    line = `${stamp(t.start_time, t.start_tz_label)} → ${stamp(
      t.end_time,
      t.end_tz_label,
      t.end_day_offset,
    )}`;
  } else if (t.start_time) {
    line = stamp(t.start_time, t.start_tz_label);
  } else if (t.end_time) {
    line = stamp(t.end_time, t.end_tz_label, t.end_day_offset);
  }
  if (t.duration_display) line += `${line ? "  ·  " : ""}${t.duration_display}`;
  return line;
}

/** The navigate target for an activity (its coordinate, else a sensible name). */
export function activityNav(act: Activity): string {
  const names: (string | undefined)[] = [
    act.type === "road" ? act.destination : undefined,
    act.address,
    act.name,
    act.type === "road" ? act.start : undefined,
    act.type === "hike" ? act.start : undefined,
    act.restaurant,
    act.area,
  ];
  const coord = act.type === "road" ? act.waypoints?.at(-1)?.coordinate ?? null : act.coordinate;
  return navUrl(coord, ...names);
}
