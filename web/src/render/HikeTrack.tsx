import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import type { Activity, HikeTrack, MapGeo } from "../types/resolved";
import { downloadBytes, slugify } from "../file/saveExport";
import { fill, tr, type Lang } from "./format";
import { MapErrorBoundary } from "./MapErrorBoundary";
import { useAccent } from "./palette";
import { useRouteGpx } from "./routeExport";

// Same lazy chunk as the day and trip maps (MapLibre is heavy, precached once).
const DayMapGL = lazy(() => import("./DayMapGL").then((m) => ({ default: m.DayMapGL })));

// A hike's embedded GPX, drawn as the PDF draws it (pdf/hike_map.py): the trail
// over the basemap, then the elevation profile under it. Both come from the same
// resolved `track` the Python model derived — keep the two renderers in step.
//
// Two deliberate differences from the print, both because a screen isn't paper:
//   * the map is the interactive MapLibre one, with no static-PNG fallback. The
//     PDF needs a raster; here the geometry is already in hand (it arrives with
//     the text, not with the per-day map render), so the map draws immediately
//     and pans and zooms. It follows the Options "interactive maps" toggle: with
//     that off, the profile stands alone.
//   * the profile is inline SVG rather than a drawn chart — same data, same
//     shape, but it scales with the column and reflows on a phone.
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

  // Must be a STABLE reference: DayMapGL remounts when `geo`'s identity changes,
  // so a fresh literal each render would tear the map down before it draws.
  const geo = useMemo<MapGeo | null>(() => {
    if (!track || track.points.length < 2) return null;
    return {
      points: [], // one trail on the map — a pin would label the only thing on it
      routes: [track.points],
      // the two ends, as the small accent discs a drive's named stops get
      route_nodes: [track.points[0], track.points[track.points.length - 1]],
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

  return (
    <div className="hike-track">
      {interactive && geo && !failed && (
        <MapErrorBoundary key={mapKey} onError={onFail} fallback={null}>
          <Suspense
            fallback={
              <div className="day-map-loading" role="status" aria-live="polite">
                <span className="spin" aria-hidden />
                {tr(lang, "buildingMap")}
              </div>
            }
          >
            <DayMapGL geo={geo} caption={caption} onFail={onFail} />
          </Suspense>
        </MapErrorBoundary>
      )}
      <ElevationProfile track={track} lang={lang} accent={accent} />
    </div>
  );
}

// The profile's drawing box in SVG user units. The viewBox scales to whatever
// width the column gives it, so these are proportions, not pixels.
const VB_W = 600;
const VB_H = 110;

// Distance against elevation, as a filled area under a stroked curve — the same
// figure pdf/hike_map.py draws with vector primitives, from the same samples.
// The y range is padded by a tenth of the climb (and at least 5 m) so a flat
// walk reads as a flat line across the middle instead of a curve pinned between
// the floor and ceiling of its own noise. Same padding as the PDF's.
function ElevationProfile({
  track,
  lang,
  accent,
}: {
  track: HikeTrack;
  lang: Lang;
  accent: string;
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
    return {
      km,
      low: Math.round(low),
      high: Math.round(high),
      line: `M${points.join("L")}`,
      area: `M0,${VB_H}L${points.join("L")}L${VB_W},${VB_H}Z`,
    };
  }, [track]);

  // No elevations in the file — the trail map stands alone (as in the PDF).
  if (!geometry) return null;

  return (
    <figure className="hike-profile">
      <figcaption>
        <span className="hike-profile-title">{tr(lang, "hikeProfile")}</span>
        <span className="hike-profile-climb">
          {fill(tr(lang, "hikeAscent"), { m: track.ascent_m ?? 0 })}
          {"  ·  "}
          {fill(tr(lang, "hikeDescent"), { m: track.descent_m ?? 0 })}
        </span>
      </figcaption>
      {/* The high mark rides inside the band's top-left corner (the padding
          above it is what keeps the curve clear of it); the low mark and the
          length share the axis row underneath — exactly as in the print, where
          a low mark inside the band would collide with the curve at every
          trailhead. */}
      <div className="hike-profile-plot">
        <svg
          viewBox={`0 0 ${VB_W} ${VB_H}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={fill(tr(lang, "hikeProfileAlt"), {
            km: geometry.km.toFixed(1),
            low: geometry.low,
            high: geometry.high,
          })}
        >
          <path d={geometry.area} fill={accent} fillOpacity={0.18} />
          {/* vectorEffect keeps the stroke one pixel wide however the box is
              scaled — the non-uniform viewBox stretch would otherwise fatten
              it unevenly. */}
          <path
            d={geometry.line}
            fill="none"
            stroke={accent}
            strokeWidth={1.6}
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        <span className="hike-profile-high">{geometry.high} m</span>
      </div>
      <p className="hike-profile-axis">
        <span>{geometry.low} m</span>
        <span>{geometry.km.toFixed(1)} km</span>
      </p>
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
