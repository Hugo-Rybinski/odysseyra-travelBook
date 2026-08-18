// Carto Positron vector basemap glue for the interactive map.
//
// Two jobs, both in service of *offline* interactive maps:
//   1. cartoStyle() — fetch Carto's keyless Positron GL style and pin its vector
//      source to a single tile host. Carto's TileJSON normally shards tiles over
//      tiles-a/b/c/d, and MapLibre round-robins them; pinning one host makes the
//      URLs deterministic so our prefetch fetches the exact URLs MapLibre will
//      later request — which is what makes them cache-hit offline.
//   2. prefetchTiles() — warm the service-worker cache with the vector tiles
//      covering a day's bounds across a small zoom window, so panning/zooming
//      within that day works offline after one online view.
//
// The style JSON, glyphs, sprite and tiles all live under *.basemaps.cartocdn.com
// (CORS-open) and are cached CacheFirst by the service worker (see vite.config).
import type { StyleSpecification } from "maplibre-gl";

const STYLE_URL = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";
// Single-host vector template (Carto's carto.streets v1, max native zoom 14).
const VECTOR_TILE_URL =
  "https://tiles-a.basemaps.cartocdn.com/vectortiles/carto.streets/v1/{z}/{x}/{y}.mvt";
const MAX_ZOOM = 14;

let styleTextPromise: Promise<string> | null = null;

/** The Positron style with its vector source pinned to a single tile host. A
 * fresh object is returned each call (MapLibre may mutate the style it's given);
 * the underlying fetch happens once and is service-worker cached for offline. */
export function cartoStyle(): Promise<StyleSpecification> {
  if (!styleTextPromise) {
    styleTextPromise = fetch(STYLE_URL)
      .then((r) => {
        if (!r.ok) throw new Error(`style ${r.status}`);
        return r.json();
      })
      .then((style) => {
        if (style?.sources?.carto) {
          style.sources.carto = {
            type: "vector",
            tiles: [VECTOR_TILE_URL],
            minzoom: 0,
            maxzoom: MAX_ZOOM,
          };
        }
        return JSON.stringify(style);
      })
      .catch((e) => {
        styleTextPromise = null; // allow a retry on the next mount
        throw e;
      });
  }
  return styleTextPromise.then((t) => JSON.parse(t) as StyleSpecification);
}

// --- tile math + prefetch ---------------------------------------------------

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

function lngLatToTileXY(lng: number, lat: number, z: number) {
  const n = 2 ** z;
  const x = Math.floor(((lng + 180) / 360) * n);
  const latRad = (lat * Math.PI) / 180;
  const y = Math.floor(
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n,
  );
  return { x: clamp(x, 0, n - 1), y: clamp(y, 0, n - 1) };
}

// The zoom MapLibre would fit the bounds to in a ~620×360 map (mirrors fitBounds).
function fitZoom(
  bounds: [[number, number], [number, number]],
  w = 620,
  h = 360,
  pad = 40,
): number {
  const [[minLat, minLng], [maxLat, maxLng]] = bounds;
  const TILE = 256;
  const mercY = (lat: number) => {
    const s = Math.sin((lat * Math.PI) / 180);
    return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI);
  };
  const lngFrac = Math.max((maxLng - minLng) / 360, 1e-6);
  const latFrac = Math.max(Math.abs(mercY(minLat) - mercY(maxLat)), 1e-6);
  const zx = Math.log2((w - 2 * pad) / TILE / lngFrac);
  const zy = Math.log2((h - 2 * pad) / TILE / latFrac);
  return clamp(Math.floor(Math.min(zx, zy)), 1, MAX_ZOOM);
}

/** Warm the SW cache with the vector tiles over `bounds` at fit-1…fit+1 (capped),
 * so this day pans/zooms offline. Best-effort and fire-and-forget; failures are
 * ignored. Overzoom past 14 reuses z14 tiles, so capping at 14 covers deeper
 * zooms too. */
export async function prefetchTiles(
  bounds: [[number, number], [number, number]],
  cap = 160,
): Promise<void> {
  const zFit = fitZoom(bounds);
  const zMin = Math.max(0, zFit - 1);
  const zMax = Math.min(MAX_ZOOM, zFit + 1);
  const [[minLat, minLng], [maxLat, maxLng]] = bounds;

  const jobs: string[] = [];
  for (let z = zMin; z <= zMax && jobs.length < cap; z++) {
    const nw = lngLatToTileXY(minLng, maxLat, z);
    const se = lngLatToTileXY(maxLng, minLat, z);
    for (let x = nw.x; x <= se.x && jobs.length < cap; x++) {
      for (let y = nw.y; y <= se.y && jobs.length < cap; y++) {
        jobs.push(
          VECTOR_TILE_URL.replace("{z}", String(z))
            .replace("{x}", String(x))
            .replace("{y}", String(y)),
        );
      }
    }
  }

  let i = 0;
  const worker = async () => {
    while (i < jobs.length) {
      const url = jobs[i++];
      try {
        await fetch(url, { mode: "cors", credentials: "omit" });
      } catch {
        /* offline / transient — ignore, it's a warm-up */
      }
    }
  };
  await Promise.all(Array.from({ length: 6 }, worker));
}
