import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import type { Activity, HikeTrack, MapGeo } from "../types/resolved";
import { downloadBytes, slugify } from "../file/saveExport";
import { elevationGrid, fill, fmtKm, roundElevation, roundKm, tr, type Lang } from "./format";
import { MapErrorBoundary } from "./MapErrorBoundary";
import { MapFigure } from "./Parts";
import { useAccent } from "./palette";
import { useRouteGpx } from "./routeExport";
import { elevationAt, nearestOnTrail, type Fix, type TrailFix } from "./trailPosition";

// Same lazy chunk as the day and trip maps (MapLibre is heavy, precached once).
const DayMapGL = lazy(() => import("./DayMapGL").then((m) => ({ default: m.DayMapGL })));

// A hike's embedded GPX, drawn as the PDF draws it (pdf/hike_map.py): the trail
// over the basemap, then the elevation profile under it. Both come from the same
// resolved `track` the Python model derived — keep the two renderers in step.
//
// One deliberate difference from the print, because a screen isn't paper: the
// profile is inline SVG rather than a drawn chart — same data, same shape, but
// it scales with the column, and a walk with more kilometre marks than the
// column can number scrolls sideways instead of setting them on top of each
// other (`MARK_MIN_PX` below). The print never has to: it has a fixed column and
// at most fifteen marks on it.
//
// The map follows the Options "interactive maps" toggle, by the same
// alternatives-not-a-fallback-chain rule as the day maps (see `MapView` in
// DayCard.tsx): on, it is the MapLibre map, which draws straight away because
// the geometry arrives with the text; off, it is the pre-rendered PNG that
// bridge.py's `_stamp_hike_maps` puts on `track.map` with the day's other
// images. A GL failure shows nothing rather than swapping the PNG in — the
// static map is what the user switched *away* from, so substituting it reads as
// the map having lost its controls. With the toggle off and no PNG yet (or none
// possible, offline), the profile stands alone, as it does on paper when the
// tiles can't be fetched.
export function HikeTrackFigure({
  act,
  lang,
  interactive = false,
}: {
  act: Activity;
  lang: Lang;
  interactive?: boolean;
}) {
  const track = act.track ?? null;
  const accent = useAccent();
  const [failed, setFailed] = useState(false);
  const [mapKey, setMapKey] = useState(0);
  const onFail = useCallback(() => setFailed(true), []);
  // "You are here", on the profile. The fix comes from the trail map's own
  // geolocate control, so it exists only while that map does — with the
  // interactive-maps toggle off there is no control and deliberately no dot.
  const [fix, setFix] = useState<Fix | null>(null);
  const here = useMemo(
    () => (track && fix ? nearestOnTrail(track.points, track.cum_km, fix, act.route) : null),
    [track, fix, act.route],
  );

  // Must be a STABLE reference: DayMapGL remounts when `geo`'s identity changes,
  // so a fresh literal each render would tear the map down before it draws.
  const geo = useMemo<MapGeo | null>(() => {
    if (!track || track.points.length < 2) return null;
    return {
      points: [], // one trail on the map — a pin would label the only thing on it
      routes: [track.points],
      // The two ends and the named points are `trail`'s, not `route_nodes`':
      // those are all one marker, and a trail needs three that differ (start,
      // finish, landmark) plus the arrowheads saying which way round it goes.
      route_nodes: [],
      trail: {
        line: track.points,
        waypoints: track.waypoints ?? [],
        km_marks: track.km_marks ?? [],
      },
      areas: [],
      accent,
      bounds: track.bounds,
    };
  }, [track, accent]);

  useEffect(() => {
    setFailed(false);
    setMapKey((k) => k + 1);
  }, [geo]);

  if (!track) return null;
  const caption = fill(tr(lang, "hikeMapCaption"), { name: act.title });
  // The hike's own `show_map` drops the trail **map**, both renderings of it,
  // and nothing else: the profile below is a chart of figures the hike already
  // states, and the GPX is still there to download. `defaults.include_hike_maps`
  // remains the switch for the whole figure. Mirrors pdf/hike_map.py's
  // `hike_track`, which gates `_hike_map` alone the same way.
  const wantsMap = act.show_map !== false;

  return (
    <div className="hike-track">
      {!wantsMap ? null : interactive ? (
        geo &&
        !failed && (
          <MapErrorBoundary key={mapKey} onError={onFail} fallback={null}>
            <Suspense
              fallback={
                <div className="day-map-loading" role="status" aria-live="polite">
                  <span className="spin" aria-hidden />
                  {tr(lang, "buildingMap")}
                </div>
              }
            >
              <DayMapGL geo={geo} caption={caption} onFail={onFail} onPosition={setFix} />
            </Suspense>
          </MapErrorBoundary>
        )
      ) : track.map ? (
        <MapFigure rendered={track.map} caption={caption} />
      ) : null}
      <ElevationProfile track={track} lang={lang} accent={accent} here={here} />
    </div>
  );
}

// The profile's drawing box in SVG user units. The viewBox scales to whatever
// width the column gives it, so these are proportions, not pixels.
const VB_W = 600;
const VB_H = 110;

// A distance number this close to either end of the axis (as a fraction of the
// width) is dropped: the row already carries the low elevation on the left and
// the total length on the right. Same rule and same fraction as
// `_KM_LABEL_EDGE` in pdf/hike_map.py — keep the two in step, since the point of
// the marks is that the two figures agree.
const KM_LABEL_EDGE = 0.07;

// The room one kilometre number needs along the axis. The print has a fixed
// column and at most `MAX_KM_MARKS` (15) numbers on it, so it can't crowd; a
// screen can be 320 px wide, where fifteen numbers would be 21 px apart and set
// on top of each other. So the plot claims this much per mark and **scrolls**
// horizontally inside the card when the column can't give it that — a long walk
// on a phone is read by dragging the profile, which is the one thing paper
// can't do, rather than by reading numbers laid over each other.
const MARK_MIN_PX = 44;

// Distance against elevation, as a filled area under a stroked curve — the same
// figure pdf/hike_map.py draws with vector primitives, from the same samples.
// The y range is padded by a tenth of the climb (and at least 5 m) so a flat
// walk reads as a flat line across the middle instead of a curve pinned between
// the floor and ceiling of its own noise. Same padding as the PDF's.
function ElevationProfile({
  track,
  lang,
  accent,
  here,
}: {
  track: HikeTrack;
  lang: Lang;
  accent: string;
  here: TrailFix | null;
}) {
  const geometry = useMemo(() => {
    const profile = track.profile;
    if (profile.length < 2) return null;
    const km = profile[profile.length - 1][0];
    const low = Math.min(...profile.map((p) => p[1]));
    const high = Math.max(...profile.map((p) => p[1]));
    const pad = Math.max((high - low) * 0.1, 5);
    const floor = low - pad;
    const ceiling = high + pad;
    const px = (k: number) => (km > 0 ? (VB_W * k) / km : 0);
    const py = (m: number) => VB_H - (VB_H * (m - floor)) / (ceiling - floor);
    const points = profile.map(([k, m]) => `${px(k).toFixed(1)},${py(m).toFixed(1)}`);
    // The whole-kilometre marks the trail map ticks too, so the steep stretch
    // here can be found over there. Only their `km` matters on this figure —
    // its x axis *is* distance walked.
    const marks = (track.km_marks ?? [])
      .filter((m) => m.km > 0 && m.km < km)
      .map((m) => ({ km: m.km, x: px(m.km), at: m.km / km }));
    // The altitude scale: round heights between the walk's own low and high
    // marks, ruled across the band and numbered in the gutter beside it. `at` is
    // the fraction of the band's height each sits at, which is what lets the
    // gutter — a DOM column outside the scroller, so it stays put while the plot
    // is dragged — line its numbers up with lines drawn in SVG units.
    const grid = elevationGrid(low, high).map((m) => ({ m, y: py(m), at: py(m) / VB_H }));
    return {
      km,
      low: Math.round(low),
      high: Math.round(high),
      marks,
      grid,
      px,
      py,
      line: `M${points.join("L")}`,
      area: `M0,${VB_H}L${points.join("L")}L${VB_W},${VB_H}Z`,
    };
  }, [track]);

  // "You are here", placed on the curve. The dot itself is a DOM disc rather
  // than an SVG circle: the viewBox is stretched non-uniformly to whatever width
  // the column gives it, which would draw a circle as an ellipse. Its band and
  // drop line are SVG, where a rect and a line stretch without complaint.
  const you = useMemo(() => {
    if (!here || !geometry) return null;
    const m = elevationAt(track.profile, here.km);
    return {
      at: geometry.px(here.km) / VB_W, // fraction of the plot's width
      atY: geometry.py(m) / VB_H,
      x: geometry.px(here.km),
      y: geometry.py(m),
      // the fix's own accuracy, as a width on the distance axis: a 40 m fix on
      // a switchback really is several hundred metres of walking
      halfW: Math.max(geometry.px(here.accuracyM / 1000), 0),
      km: roundKm(here.km),
      m: Math.round(m),
    };
  }, [here, geometry, track.profile]);

  // No elevations in the file — the trail map stands alone (as in the PDF).
  if (!geometry) return null;

  return (
    <figure className="hike-profile">
      <figcaption>
        <span className="hike-profile-title">{tr(lang, "hikeProfile")}</span>
        <span className="hike-profile-climb">
          {fill(tr(lang, "hikeAscent"), { m: roundElevation(track.ascent_m ?? 0) })}
          {"  ·  "}
          {fill(tr(lang, "hikeDescent"), { m: roundElevation(track.descent_m ?? 0) })}
        </span>
        {/* The dot's reading, in the caption rather than beside the dot: a label
            on the curve is one more thing to collide with the kilometre numbers,
            and this is the line a walker reads on a phone without hovering. */}
        {you && (
          <span className="hike-profile-here">
            {fill(tr(lang, "hikeHere"), { km: you.km, m: you.m })}
          </span>
        )}
      </figcaption>
      {/* Two columns: the altitude scale, then the plot and its distance axis
          in a scroller. The gutter is deliberately *outside* that scroller — it
          is the one thing you still need after dragging a long walk sideways,
          and its numbers can't be laid over the band anyway (the curve reaches
          the left edge at the trailhead, which is the line they would label).
          The high mark rides inside the band's top-left corner (the padding
          above it is what keeps the curve clear of it); the low mark and the
          length share the axis row underneath — exactly as in the print, where
          a low mark inside the band would collide with the curve at every
          trailhead. Those two keep their `m`: they are the walk's own
          altitudes, where the gutter's bare numbers are the scale. */}
      <div className="hike-profile-body">
        <div className="hike-profile-scale" aria-hidden>
          {geometry.grid.map((g) => (
            <span key={g.m} style={{ top: `${g.at * 100}%` }}>
              {g.m}
            </span>
          ))}
        </div>
        <div className="hike-profile-scroll">
          <div
            className="hike-profile-inner"
            style={{ minWidth: `${(geometry.marks.length + 1) * MARK_MIN_PX}px` }}
          >
            <div className="hike-profile-plot">
              <svg
                viewBox={`0 0 ${VB_W} ${VB_H}`}
                preserveAspectRatio="none"
                role="img"
                aria-label={fill(tr(lang, "hikeProfileAlt"), {
                  km: roundKm(geometry.km),
                  low: geometry.low,
                  high: geometry.high,
                })}
              >
                <path d={geometry.area} fill={accent} fillOpacity={0.18} />
                {/* the altitude scale, lighter than the distance marks: those
                    pair the figure with the trail map, so they read first */}
                {geometry.grid.map((g) => (
                  <line
                    key={g.m}
                    x1={0}
                    y1={g.y}
                    x2={VB_W}
                    y2={g.y}
                    stroke={accent}
                    strokeOpacity={0.22}
                    strokeWidth={1}
                    vectorEffect="non-scaling-stroke"
                  />
                ))}
                {/* the distance marks, over the fill and under the curve, so the
                    profile still reads as one shape (as in the print) */}
                {geometry.marks.map((m) => (
                  <line
                    key={m.km}
                    x1={m.x}
                    y1={0}
                    x2={m.x}
                    y2={VB_H}
                    stroke={accent}
                    strokeOpacity={0.35}
                    strokeWidth={1}
                    vectorEffect="non-scaling-stroke"
                  />
                ))}
                {/* vectorEffect keeps the stroke one pixel wide however the box
                    is scaled — the non-uniform viewBox stretch would otherwise
                    fatten it unevenly. */}
                <path
                  d={geometry.line}
                  fill="none"
                  stroke={accent}
                  strokeWidth={1.6}
                  vectorEffect="non-scaling-stroke"
                />
                {/* where you are: the fix's accuracy as a band, and a drop line
                    down to the distance axis so the kilometre can be read off
                    the numbers already there */}
                {you && (
                  <>
                    {you.halfW > 1 && (
                      <rect
                        x={you.x - you.halfW}
                        y={0}
                        width={you.halfW * 2}
                        height={VB_H}
                        fill={accent}
                        fillOpacity={0.1}
                      />
                    )}
                    <line
                      x1={you.x}
                      y1={you.y}
                      x2={you.x}
                      y2={VB_H}
                      stroke={accent}
                      strokeWidth={1}
                      strokeOpacity={0.6}
                      vectorEffect="non-scaling-stroke"
                    />
                  </>
                )}
              </svg>
              <span className="hike-profile-high">{geometry.high} m</span>
              {you && (
                <span
                  className="hike-profile-you"
                  style={{
                    left: `${you.at * 100}%`,
                    top: `${you.atY * 100}%`,
                    background: accent,
                  }}
                  title={fill(tr(lang, "hikeHere"), { km: you.km, m: you.m })}
                />
              )}
            </div>
            <p className="hike-profile-axis">
              <span>{geometry.low} m</span>
              {geometry.marks
                .filter((m) => m.at > KM_LABEL_EDGE && m.at < 1 - KM_LABEL_EDGE)
                .map((m) => (
                  <span
                    key={m.km}
                    className="hike-profile-km"
                    style={{ left: `${m.at * 100}%` }}
                  >
                    {m.km}
                  </span>
                ))}
              <span>{fmtKm(geometry.km)}</span>
            </p>
          </div>
        </div>
      </div>
    </figure>
  );
}

// --- the "(Get GPX track)" link ---------------------------------------------

/** The bytes behind a base64 (possibly gzipped) payload. Tolerates a `data:`
 *  URI prefix and line wrapping, exactly as models/gpx.py's `decode_gpx` does —
 *  the field is hand-writable, so both ends have to accept the same shapes. */
function fromBase64(text: string): Uint8Array {
  const payload = text.startsWith("data:") ? text.slice(text.indexOf(",") + 1) : text;
  const binary = atob(payload.replace(/\s+/g, ""));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function gunzip(bytes: Uint8Array): Promise<Uint8Array> {
  const DS = (globalThis as { DecompressionStream?: typeof DecompressionStream })
    .DecompressionStream;
  if (!DS) throw new Error("no DecompressionStream");
  const stream = new Blob([bytes as BlobPart]).stream().pipeThrough(new DS("gzip"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

/** The GPX file a hike carries, decoded back to XML bytes (inflating it when the
 *  itinerary stored it gzipped — which is how the Edit tab writes it). */
async function gpxBytes(base64: string): Promise<Uint8Array> {
  const raw = fromBase64(base64);
  const gzipped = raw[0] === 0x1f && raw[1] === 0x8b;
  return gzipped ? gunzip(raw) : raw;
}

// Hands back a `.gpx` the itinerary carries, for a watch, a GPS or another app.
// It's the file that was attached, byte-for-byte — not a re-export of the line
// the map draws — so what you load elsewhere is what you gave.
//
// Decoding is async (inflating a gzipped payload goes through a stream), so this
// is a button rather than an `<a href>`: there is nothing to point at until the
// click. It's styled as one of the inline links beside it all the same.
//
// Paper can't hand back a file, so this has no PDF twin — the same deliberate
// split as the road-leg download below.
export function GpxDownload({
  base64,
  name,
  lang,
}: {
  base64: string | null | undefined;
  name: string;
  lang: Lang;
}) {
  const [failed, setFailed] = useState(false);
  if (!base64) return null;

  const download = async () => {
    setFailed(false);
    try {
      const bytes = await gpxBytes(base64);
      downloadBytes(bytes, `${slugify(name || "track")}.gpx`, "application/gpx+xml");
    } catch {
      setFailed(true);
    }
  };

  if (failed) return <span className="gpx-error">{tr(lang, "gpxFailed")}</span>;
  return (
    <button type="button" className="link gpx-link" onClick={() => void download()}>
      {tr(lang, "getGpx")}
    </button>
  );
}

// A hike's trail file, from the `track` its GPX was reduced to.
export function GpxDownloadLink({ act, lang }: { act: Activity; lang: Lang }) {
  return <GpxDownload base64={act.track?.gpx} name={act.title || "trail"} lang={lang} />;
}

// The other half of the pair: a leg with **no** recording, whose file the app
// builds on demand from the route the map draws (`buildLegGpx` → the engine's
// `legGpx` op). Distinct wording from the download above — this file didn't
// exist until you clicked, and what it holds is a computed route, not something
// that was recorded — and it stays silent when there is no route to build from
// (the engine refuses to pass a straight line off as one).
export function GpxBuildLink({
  dayIndex,
  roadIndex,
  legIndex,
  lang,
}: {
  dayIndex: number;
  roadIndex: number;
  legIndex: number;
  lang: Lang;
}) {
  const api = useRouteGpx();
  const [state, setState] = useState<"idle" | "busy" | "failed">("idle");
  if (!api) return null;

  const build = async () => {
    setState("busy");
    try {
      const { gpx, name } = await api.build(dayIndex, roadIndex, legIndex);
      downloadBytes(new TextEncoder().encode(gpx), `${slugify(name || "route")}.gpx`,
        "application/gpx+xml");
      setState("idle");
    } catch {
      setState("failed");
    }
  };

  if (state === "failed") return <span className="gpx-error">{tr(lang, "gpxUnavailable")}</span>;
  return (
    <button
      type="button"
      className="link gpx-link"
      disabled={!api.ready || state === "busy"}
      onClick={() => void build()}
    >
      {tr(lang, "buildGpx")}
    </button>
  );
}
