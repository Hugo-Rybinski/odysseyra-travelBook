// Client-side helpers that mirror bits of the Python renderer/model so the UI
// can offer the same links and leg breakdown without another round-trip.
import { createContext, useContext } from "react";
import type { Activity, Coordinate, TransportLeg, Waypoint } from "../types/resolved";

// Which mapping app the "Navigate" links open. Chosen in Options and shared with
// every render component via MapProviderContext (default Google Maps).
export type MapProvider = "google" | "apple" | "osm" | "waze" | "mapsme";

// The picker's options, in display order. Labels are plain product names, so
// they read the same in both languages (no translation needed).
export const MAP_PROVIDERS: { id: MapProvider; label: string }[] = [
  { id: "google", label: "Google Maps" },
  { id: "apple", label: "Apple Plans / Maps" },
  { id: "osm", label: "OpenStreetMap" },
  { id: "waze", label: "Waze" },
  { id: "mapsme", label: "MAPS.ME" },
];

export const MapProviderContext = createContext<MapProvider>("google");
export const useMapProvider = (): MapProvider => useContext(MapProviderContext);

// A URL to the first available location — the exact coordinate, else the first
// non-empty name — in the chosen mapping app. "" when nothing is locatable. The
// URL opens navigation on mobile and the map on desktop.
export function navUrl(
  provider: MapProvider,
  coordinate: Coordinate | null | undefined,
  ...names: (string | null | undefined)[]
): string {
  if (coordinate) {
    const { lat, long } = coordinate;
    switch (provider) {
      case "apple":
        return `https://maps.apple.com/?ll=${lat},${long}&q=${encodeURIComponent(`${lat},${long}`)}`;
      case "osm":
        return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${long}#map=16/${lat}/${long}`;
      case "waze":
        return `https://waze.com/ul?ll=${lat},${long}&navigate=yes`;
      case "mapsme":
        // MAPS.ME only opens via its app-scheme deep link (no web fallback).
        return `mapsme://map?v=1&ll=${lat},${long}&zoom=16`;
      case "google":
      default:
        return `https://www.google.com/maps/search/?api=1&query=${lat},${long}`;
    }
  }
  const name = names.find((n) => n && n.trim());
  if (!name) return "";
  const q = encodeURIComponent(name.trim());
  switch (provider) {
    case "apple":
      return `https://maps.apple.com/?q=${q}`;
    case "osm":
      return `https://www.openstreetmap.org/search?query=${q}`;
    case "waze":
      return `https://waze.com/ul?q=${q}&navigate=yes`;
    case "mapsme":
      return `mapsme://search?query=${q}`;
    case "google":
    default:
      return `https://www.google.com/maps/search/?api=1&query=${q}`;
  }
}

// A directions/route URL from ``origin`` to the destination (its ``destCoord``
// when known, else ``destName``) in the chosen app — used by the "Check online
// to fill it." link on a road leg that's missing its travel time / distance, so
// the provider shows the real figures. "" when there's no destination at all.
// Google / Apple / OpenStreetMap render a full A→B route on the web; Waze and
// MAPS.ME have no usable web route link, so they fall back to the destination.
export function directionsUrl(
  provider: MapProvider,
  origin: string | null | undefined,
  destCoord: Coordinate | null | undefined,
  destName: string | null | undefined,
): string {
  const dest = destCoord ? `${destCoord.lat},${destCoord.long}` : (destName ?? "").trim();
  if (!dest) return "";
  const org = (origin ?? "").trim();
  const d = encodeURIComponent(dest);
  const o = encodeURIComponent(org);
  switch (provider) {
    case "apple":
      return `https://maps.apple.com/?daddr=${d}&dirflg=d` + (org ? `&saddr=${o}` : "");
    case "osm":
      return `https://www.openstreetmap.org/directions?from=${o}&to=${d}`;
    case "waze":
    case "mapsme":
      return navUrl(provider, destCoord, destName ?? "");
    case "google":
    default:
      return `https://www.google.com/maps/dir/?api=1&destination=${d}` + (org ? `&origin=${o}` : "");
  }
}

export interface RoadLeg {
  src: string;
  dest: string | null; // null for a trailing unnamed arrival
  durationMin: number | null;
  distanceKm: number | null;
  destCoord: Coordinate | null;
  offRoad: boolean;
}

// Collapse a road's waypoints into display legs, mirroring
// pdf.days.road_display_legs: unnamed (route-shaping) waypoints merge forward
// into the next named leg, summing their duration/distance and OR-ing their
// off_road flag.
export function roadLegs(start: string, waypoints: Waypoint[]): RoadLeg[] {
  const legs: RoadLeg[] = [];
  let prev = start;
  let dur = 0;
  let dist = 0;
  let hasDur = false;
  let hasDist = false;
  let pending = false;
  let coord: Coordinate | null = null;
  let off = false;

  const flush = (dest: string | null) => {
    legs.push({
      src: prev,
      dest,
      durationMin: hasDur ? dur : null,
      distanceKm: hasDist ? dist : null,
      destCoord: coord,
      offRoad: off,
    });
    prev = dest ?? prev;
    dur = 0;
    dist = 0;
    hasDur = false;
    hasDist = false;
    pending = false;
    coord = null;
    off = false;
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
    if (wp.off_road) off = true;
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

/** A leg's time line with tz labels and the arrival day-offset ("+1"). */
export function transportTimes(t: TransportLeg): string {
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
export function activityNav(provider: MapProvider, act: Activity): string {
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
  return navUrl(provider, coord, ...names);
}
