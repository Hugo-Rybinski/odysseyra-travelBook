// The whole-trip map's geometry: every day's located points and drive routes
// merged into a single `MapGeo` — the same shape the per-day interactive map
// renders from, so the Overview tab can reuse `DayMapGL` untouched.
//
// Each pin is labeled with its **day number** (rather than the day map's 1..N /
// ★ / A-B-C labels, which only mean something within one day); the point's own
// identity moves into the popup title.
//
// Two sources, per day, in this order:
//   1. `day.map.geo` — the rendered day map's points *and* its real OSRM drive
//      geometry. Only present when the itinerary opts into maps and that day's
//      render has landed (they stream in one by one).
//   2. otherwise the coordinates the resolved model carries directly, so the
//      trip map still works with maps off (or before the renders arrive) —
//      points only, since routes need the routing pass.

import type { Activity, Coordinate, Day, Itinerary, MapGeo, MapPoint } from "../types/resolved";
import { tr, type Lang } from "./format";
import { palette } from "./palette";

export type LatLng = [number, number];

interface RawPoint {
  lat: number;
  long: number;
  title: string;
}

// A day's explicit coordinates, walked in timeline order (one level of nesting).
// Roads contribute their *named* waypoints — the arrival and any named stop —
// rather than their departure, which is normally the previous activity's spot.
function modelPoints(day: Day): RawPoint[] {
  const out: RawPoint[] = [];
  const push = (c: Coordinate | null | undefined, title: string) => {
    if (c && c.show_on_map) out.push({ lat: c.lat, long: c.long, title });
  };
  const walk = (acts: Activity[]) => {
    for (const a of acts) {
      if (a.type === "buffer") continue;
      if (a.type === "road") {
        for (const w of a.waypoints ?? []) if (w.location) push(w.coordinate, w.location);
      } else {
        push(a.coordinate, a.title);
      }
      if (a.activities?.length) walk(a.activities);
    }
  };
  walk(day.activities);
  if (day.stay) push(day.stay.coordinate, day.stay.city || day.stay.name);
  return out;
}

// --- outlier clusters -------------------------------------------------------
//
// A trip that departs from the other side of the world (a "Manhattan → JFK"
// first day before a France tour) would otherwise fit its initial view to the
// whole Atlantic, squashing the actual trip into a corner. So a point stops
// driving the initial view once it sits both >`FACTOR`× the median distance from
// the trip's median center *and* >`FLOOR_KM` away — the factor alone would trim
// a legitimate day trip out of a tight city stay, the floor alone would trim the
// far end of a genuinely wide trip. At most `MAX_SHARE` of the points can be
// trimmed: beyond that they're a real second cluster, not strays, and the map
// shows both. Trimmed geometry is still drawn — the map just starts zoomed on
// the trip, one zoom out away from the rest.
//
// The PDF's whole-trip map page ports this same trimming (see
// `maps/build.py`'s `_trip_extent`); keep the two in step.
const OUTLIER_FACTOR = 6;
const OUTLIER_FLOOR_KM = 400;
const OUTLIER_MAX_SHARE = 1 / 3;
const OUTLIER_MIN_ANCHORS = 4; // below this there's no "cluster" to speak of

function median(xs: number[]): number {
  const s = [...xs].sort((a, b) => a - b);
  const mid = s.length >> 1;
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

// A center to measure from, plus the km-per-degree-of-longitude at that latitude.
interface Center {
  lat: number;
  long: number;
  kx: number;
}

const KM_PER_DEG = 111.32;

function centerOf(sample: LatLng[]): Center {
  const lat = median(sample.map(([la]) => la));
  return {
    lat,
    long: median(sample.map(([, lo]) => lo)),
    kx: KM_PER_DEG * Math.cos((lat * Math.PI) / 180),
  };
}

// Equirectangular km — ample for a "is this in another part of the world" test.
function kmFrom(c: Center, lat: number, long: number): number {
  return Math.hypot((long - c.long) * c.kx, (lat - c.lat) * KM_PER_DEG);
}

// An endpoint pair for one transport leg, when both ends are mapped.
function legOf(t: Itinerary["transports"][number]): LatLng[] | null {
  const a = t.start_coordinate;
  const b = t.end_coordinate;
  if (!a || !b || !a.show_on_map || !b.show_on_map) return null;
  return [
    [a.lat, a.long],
    [b.lat, b.long],
  ];
}

/** Merge the trip into one map geometry, or `null` when nothing is located.
 *
 * Its `legs` are the trip's transport legs as straight `[origin, destination]`
 * pairs — flights, trains, ferries — drawn dotted, since the real path isn't
 * known (and for a flight isn't a path on the ground at all). Only legs whose
 * JSON gives both a `start_coordinate` and an `end_coordinate` appear: nothing
 * infers them, here or in Python. */
export function tripGeo(itinerary: Itinerary, lang: Lang): MapGeo | null {
  const points: MapPoint[] = [];
  const routes: LatLng[][] = [];
  const seen = new Set<string>();
  let accent = "";

  for (const day of itinerary.days) {
    const label = String(day.day_number);
    const add = ({ lat, long, title }: RawPoint) => {
      // one pin per spot per day (a place revisited on another day keeps its own)
      const key = `${label}|${lat.toFixed(4)}|${long.toFixed(4)}`;
      if (seen.has(key)) return;
      seen.add(key);
      points.push({ lat, long, label, title: `${tr(lang, "day")} ${label} · ${title}` });
    };

    const geo = day.map?.geo ?? null;
    if (geo) {
      if (!accent) accent = geo.accent;
      for (const line of geo.routes) routes.push(line);
      // `geo.areas` is skipped: an area's nested points collapse into its single
      // main pin at trip zoom, where they'd only be clutter.
      for (const p of geo.points) add(p);
    } else {
      for (const p of modelPoints(day)) add(p);
    }
  }

  // Transport legs: one straight dotted line per leg. The legs are the trip's
  // own list, so an overnight one is drawn once rather than on both of its days.
  const legs = itinerary.transports
    .map(legOf)
    .filter((line): line is LatLng[] => line !== null);

  if (!points.length && !routes.length && !legs.length) return null;

  // --- what the initial view is fitted to ----------------------------------
  // Drives and transport legs are both polylines from here on.
  const lines = [...routes, ...legs];

  // The center/scale statistics come from the pins alone — route vertices are
  // hundreds per drive and would drag the center toward whichever day drove
  // furthest. With no pins at all (a trip of pure drives/legs) the vertices are
  // all there is to go on.
  const sample: LatLng[] = points.length
    ? points.map((p) => [p.lat, p.long])
    : lines.flat();
  const center = centerOf(sample);
  const cutoff = Math.max(
    median(sample.map(([lat, long]) => kmFrom(center, lat, long))) * OUTLIER_FACTOR,
    OUTLIER_FLOOR_KM,
  );

  // Anchors = every pin, plus every drive/leg as a single unit. A line counts as
  // far off only when it lies *entirely* beyond the cutoff, so one reaching into
  // the trip (an inbound flight, say) still counts as part of it. Weighing lines
  // matters: with maps on, a "Manhattan → JFK" departure day is a route and no
  // pin at all, so a pin-only rule would let it drag the view across the Atlantic.
  const farPin = points.map((p) => kmFrom(center, p.lat, p.long) > cutoff);
  const farLine = lines.map(
    (line) =>
      line.length > 0 && line.every(([lat, long]) => kmFrom(center, lat, long) > cutoff),
  );
  const anchors = points.length + lines.length;
  const far = farPin.filter(Boolean).length + farLine.filter(Boolean).length;
  // Trim only when there's something to set aside, enough of a trip to judge
  // against, and the far-off anchors are a small minority — over a third and
  // they're a real second cluster, which stays in view.
  const trim = far > 0 && anchors >= OUTLIER_MIN_ANCHORS && far <= anchors * OUTLIER_MAX_SHARE;
  const inView = (lat: number, long: number) => !trim || kmFrom(center, lat, long) <= cutoff;

  let minLat = Infinity;
  let minLng = Infinity;
  let maxLat = -Infinity;
  let maxLng = -Infinity;
  const grow = (lat: number, long: number) => {
    if (!inView(lat, long)) return;
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    minLng = Math.min(minLng, long);
    maxLng = Math.max(maxLng, long);
  };
  for (const p of points) grow(p.lat, p.long);
  for (const line of lines) for (const [lat, long] of line) grow(lat, long);

  return {
    points,
    routes,
    route_nodes: [], // the day maps' route stops are noise under the day pins
    areas: [],
    legs,
    accent: accent || palette(itinerary.cover_color).accent,
    bounds: [
      [minLat, minLng],
      [maxLat, maxLng],
    ],
  };
}
