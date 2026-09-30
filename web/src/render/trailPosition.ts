// Where you are, expressed as a distance along a hike's trail.
//
// The trail map already shows a GPS fix as a dot on the ground (MapLibre's
// `GeolocateControl`, added in DayMapGL). This turns that same fix into the one
// number the elevation profile is drawn against — kilometres walked — so the
// figure can mark the point you have reached on the curve: what is left to
// climb, and how steeply.
//
// The fix comes from the map's own control and nowhere else, so the dot exists
// only where that map does: with the Options interactive-maps toggle off there
// is no control, no position, and deliberately no dot. One owner of the GPS,
// one permission prompt, one watcher on the battery.

/** A fix matched to the trail. */
export interface TrailFix {
  /** Kilometres walked at the matched point — the profile's own x axis. */
  km: number;
  /** How far the fix sits from the trail, in metres. */
  offMeters: number;
  /** The fix's own reported accuracy, in metres. */
  accuracyM: number;
}

export interface Fix {
  lat: number;
  long: number;
  accuracyM: number;
}

// Past this, the fix isn't on this walk: no dot. A hike being read at home, or
// on another day of the trip, would otherwise be marked at whichever end of the
// trail happens to be nearest — which is a lie a walker can act on.
const OFF_TRAIL_KM = 1;

// A trail whose two ends are this close came back to where it started, so a
// `back_and_forth` recording holds both the outward and the return leg. Same
// threshold as `LOOP_MERGE_KM` in DayMapGL.tsx and `maps/render.py` (the one
// that decides whether to draw a separate finish marker) — keep the three in
// step.
const ENDS_MERGE_KM = 0.03;

const EARTH_R_KM = 6371.0088;

/** Kilometres between two coordinates, planar with the longitude scaled by the
 *  latitude's cosine. At a hike's scale that is exact enough, and it is the same
 *  approximation `models/gpx.py`'s `_bearing` and `maps/render.py` make. */
function km(aLat: number, aLong: number, bLat: number, bLong: number): number {
  const rad = Math.PI / 180;
  const kx = Math.cos(((aLat + bLat) / 2) * rad);
  return EARTH_R_KM * rad * Math.hypot(aLat - bLat, (aLong - bLong) * kx);
}

/** True when the line ends where it began — so a there-and-back walk really did
 *  record both legs, rather than being a one-way recording of it. */
function doubledBack(points: [number, number][]): boolean {
  const a = points[0];
  const b = points[points.length - 1];
  return km(a[0], a[1], b[0], b[1]) <= ENDS_MERGE_KM;
}

/** Match `fix` to the nearest point of a hike's trail and return how far along
 *  the walk that is. `null` when the trail can't be measured (no distances — a
 *  day cached before `cum_km` existed) or when the fix is more than
 *  `OFF_TRAIL_KM` from it.
 *
 *  `route` is the hike's own: an **out-and-back** whose recording holds both
 *  legs is matched against its **first half only**, so standing on the path
 *  reads as the outward distance rather than as one of two answers a kilometre
 *  apart on the profile. The two legs are drawn metres apart on the ground and
 *  there is nothing in a single fix to tell them apart, so the honest thing is
 *  to pick the one the walker is on first — and the second half of the curve is
 *  the first half mirrored anyway. A loop or a one-way walk passes each point
 *  once and is matched over its whole length.
 */
export function nearestOnTrail(
  points: [number, number][],
  cumKm: number[] | undefined,
  fix: Fix,
  route?: string,
): TrailFix | null {
  if (!cumKm || cumKm.length !== points.length || points.length < 2) return null;

  const total = cumKm[cumKm.length - 1];
  const outboundOnly = route === "back_and_forth" && doubledBack(points) && total > 0;
  const limit = outboundOnly ? total / 2 : Infinity;

  const rad = Math.PI / 180;
  const kx = Math.cos(fix.lat * rad);
  // Work in "degrees of latitude", where one unit is the same distance on both
  // axes — projecting a point onto a segment needs a square metric, which raw
  // lat/long is not.
  const toXY = (lat: number, long: number): [number, number] => [long * kx, lat];
  const [fx, fy] = toXY(fix.lat, fix.long);

  let bestKm = 0;
  let bestOff = Infinity; // km
  for (let i = 0; i < points.length - 1; i++) {
    if (cumKm[i] >= limit) break;
    const [ax, ay] = toXY(points[i][0], points[i][1]);
    const [bx, by] = toXY(points[i + 1][0], points[i + 1][1]);
    const dx = bx - ax;
    const dy = by - ay;
    const len2 = dx * dx + dy * dy;
    // where along the segment the perpendicular falls, clamped to its ends
    let t = len2 === 0 ? 0 : ((fx - ax) * dx + (fy - ay) * dy) / len2;
    t = t < 0 ? 0 : t > 1 ? 1 : t;
    const off = EARTH_R_KM * rad * Math.hypot(fx - (ax + dx * t), fy - (ay + dy * t));
    if (off < bestOff) {
      bestOff = off;
      // the one segment straddling the turnaround reports it, rather than
      // dropping the ground right at the far end of the walk
      bestKm = Math.min(cumKm[i] + (cumKm[i + 1] - cumKm[i]) * t, limit);
    }
  }
  if (bestOff > OFF_TRAIL_KM) return null;
  return { km: bestKm, offMeters: bestOff * 1000, accuracyM: fix.accuracyM };
}

/** The elevation the profile shows at `km`, interpolated between its samples —
 *  so the dot sits *on* the curve rather than near it. */
export function elevationAt(profile: [number, number][], km: number): number {
  if (!profile.length) return 0;
  if (km <= profile[0][0]) return profile[0][1];
  for (let i = 1; i < profile.length; i++) {
    const [k1, e1] = profile[i];
    if (km <= k1) {
      const [k0, e0] = profile[i - 1];
      const span = k1 - k0;
      return span <= 0 ? e1 : e0 + ((e1 - e0) * (km - k0)) / span;
    }
  }
  return profile[profile.length - 1][1];
}
