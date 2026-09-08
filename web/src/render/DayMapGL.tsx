import { useEffect, useRef, useState } from "react";
import {
  FullscreenControl,
  GeolocateControl,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  Popup,
  ScaleControl,
  setWorkerUrl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre v6 loads its worker from a *computed* URL Vite can't statically see,
// so it never emits the worker file (→ a 404 that the SPA fallback answers with
// index.html → "non-JavaScript MIME type" error). Bundle the worker explicitly
// with `?worker&url` (Vite emits one self-contained, hashed, precached asset)
// and point MapLibre at it. Must be set before any Map is constructed.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { MapGeo } from "../types/resolved";
import { cartoStyle, prefetchTiles } from "../maps/carto";

setWorkerUrl(workerUrl);

// --- a trail's own decoration (the twin of maps/render.py's `Trail`) ----------

// A trail whose ends are this close is walked back to where it started — a loop,
// or an out-and-back — and shows its start marker alone. Same threshold as
// `LOOP_MERGE_KM` in maps/render.py: keep the two in step, or the same hike shows
// a finish on paper and not on screen.
const LOOP_MERGE_KM = 0.03;

// How near the viewport a map figure has to be to hold a GL context, and how
// far away before it gives it back. The gap between the two is deliberate — see
// the observer pair in DayMapGL. A day map is ~350 px tall, so 400/1600 mounts
// it roughly one screen early and releases it about two screens late: never
// visible as a rebuild, and only a handful live at once whatever the trip's
// length.
const MOUNT_MARGIN = "400px";
const KEEP_MARGIN = "1600px";

// Candidate direction arrowheads along the line. They are laid down generously
// and thinned by MapLibre's own collision engine (`icon-allow-overlap: false`),
// which is strictly better than the print's fixed spacing: heads appear as you
// zoom in and, on an out-and-back, the return leg's heads lose to the outbound
// ones because source order is walking order.
const ARROW_CANDIDATES = 40;

// Fraction of the line left clear at each end, so no head sits under a trailhead
// marker (the print's `ARROW_CLEAR`, expressed as a share of the length because
// here there is no one zoom to measure pixels at).
const ARROW_CLEAR_FRACTION = 0.04;

const ARROW_IMAGE = "tb-trail-arrow";
const TICK_IMAGE = "tb-trail-tick";

// How far a distance mark's number sits from its tick, in px. Placed on the
// **left of the way you were walking**, which on an out-and-back separates the
// two legs for free: the return walks the opposite bearing, so its left is the
// other side of the ground, and the outbound numbers line up along one side of
// the path with the return's along the other. Two numbers on the same side of
// two lines metres apart is what made a doubled-back trail unreadable.
// Mirrors `_draw_trail`'s preferred label direction in maps/render.py.
const KM_LABEL_OFFSET = 17;

function apartKm(a: [number, number], b: [number, number]): number {
  const kx = 111.32 * Math.cos(((a[0] + b[0]) / 2) * (Math.PI / 180));
  return Math.hypot((b[1] - a[1]) * kx, (b[0] - a[0]) * 110.574);
}

/** Bearing in degrees clockwise from north — what `icon-rotate` wants. */
function bearing(a: [number, number], b: [number, number]): number {
  const kx = Math.cos(((a[0] + b[0]) / 2) * (Math.PI / 180));
  return (Math.atan2((b[1] - a[1]) * kx, b[0] - a[0]) * 180) / Math.PI;
}

/** `[lng, lat, bearing]` for each candidate arrowhead, evenly spread along the
 *  walked line by *distance* (not by point index — a recorded track logs a point
 *  a second, so index-spacing would bunch every head where you stopped). */
function arrowCandidates(line: [number, number][]): [number, number, number][] {
  const spans: { a: [number, number]; b: [number, number]; len: number; at: number }[] = [];
  let total = 0;
  for (let i = 0; i < line.length - 1; i++) {
    const len = apartKm(line[i], line[i + 1]);
    if (len <= 0) continue;
    spans.push({ a: line[i], b: line[i + 1], len, at: total });
    total += len;
  }
  if (!spans.length || total <= 0) return [];
  const clear = total * ARROW_CLEAR_FRACTION;
  const span = total - 2 * clear;
  if (span <= 0) return [];
  const out: [number, number, number][] = [];
  let i = 0;
  for (let k = 0; k < ARROW_CANDIDATES; k++) {
    const target = clear + (span * (k + 0.5)) / ARROW_CANDIDATES;
    while (i < spans.length - 1 && spans[i].at + spans[i].len < target) i++;
    const s = spans[i];
    const f = (target - s.at) / s.len;
    out.push([
      s.a[1] + (s.b[1] - s.a[1]) * f,
      s.a[0] + (s.b[0] - s.a[0]) * f,
      bearing(s.a, s.b),
    ]);
  }
  return out;
}

/** An arrowhead as a tiny bitmap for `addImage`: a white triangle with an accent
 *  one inside it, pointing **up** (so `icon-rotate` can take a bearing straight).
 *  Drawn rather than shipped as a sprite because it has to wear the trip's accent
 *  — and it is a dozen triangles' worth of pixels. */
function arrowImage(accent: string, size = 28): ImageData | null {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  const triangle = (scale: number, fill: string) => {
    const cx = size / 2;
    const cy = size / 2;
    const l = size * 0.8 * scale;
    const w = size * 0.62 * scale;
    ctx.beginPath();
    ctx.moveTo(cx, cy - l / 2);
    ctx.lineTo(cx + w / 2, cy + l / 2);
    ctx.lineTo(cx - w / 2, cy + l / 2);
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
  };
  triangle(1, "#ffffff");
  triangle(0.72, accent);
  return ctx.getImageData(0, 0, size, size);
}

/** A distance tick as a bitmap: an accent bar with a white halo, drawn
 *  **horizontally** so that rotating it by the trail's bearing lays it *across*
 *  the line (a trail heading north wants a horizontal tick). */
function tickImage(accent: string, w = 26, h = 12): ImageData | null {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  const bar = (thickness: number, fill: string) => {
    ctx.fillStyle = fill;
    ctx.fillRect(1, (h - thickness) / 2, w - 2, thickness);
  };
  bar(h * 0.75, "#ffffff");
  bar(h * 0.34, accent);
  return ctx.getImageData(0, 0, w, h);
}

/** A trailhead / named-point marker element, styled by index.css. */
function trailMarker(kind: "start" | "end", accent: string): HTMLElement {
  const el = document.createElement("div");
  el.className = `trail-mark trail-${kind}`;
  el.style.borderColor = accent;
  if (kind === "start") el.style.background = accent;
  return el;
}

// Interactive day map: same points / route polylines / area pins as the static
// render, drawn live with MapLibre GL over Carto's keyless Positron vector style
// (the vector twin of the raster Positron tiles the PNG uses, so it matches the
// PDF). Calls `onFail` if the style/tiles can't load (offline & uncached,
// blocked) so the caller can fall back to the static PNG.
export function DayMapGL({
  geo,
  caption,
  onFail,
}: {
  geo: MapGeo;
  caption: string;
  onFail?: () => void;
}) {
  const holder = useRef<HTMLDivElement | null>(null);
  const figure = useRef<HTMLElement | null>(null);
  // Whether this map currently holds a GL context. See MOUNT_MARGIN.
  const [live, setLive] = useState(false);
  // Where the user left the camera, so scrolling away and back doesn't reset the
  // view they had panned to. Only meaningful once they've moved it — a map that
  // was never touched refits its bounds, which is also what a changed `geo`
  // should do.
  const camera = useRef<{ center: [number, number]; zoom: number; bearing: number; pitch: number } | null>(
    null,
  );

  // Hold a WebGL context only while the figure is near the viewport.
  //
  // A browser keeps a hard, small number of live WebGL contexts per page —
  // Chrome's is 16 — and **silently kills the oldest** past it, leaving a dead
  // canvas with no error to catch. MapLibre needs one context each, and a book
  // mounts one map per day plus one per area and one per hike trail: a 15-day
  // trip asked for 18 at once, so it lost two straight away and more as it
  // scrolled, which reads as "the dynamic maps don't render". An 8-day trip sits
  // just under the cap, which is why this only showed up on a long one.
  //
  // Two observers rather than one, for hysteresis: mount a little before the
  // figure scrolls into view, and don't release it until it is well clear.
  // Sharing one margin would rebuild the map every time a slow scroll wobbled
  // across the boundary.
  useEffect(() => {
    const el = figure.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setLive(true); // no observer to lean on: behave as it always did
      return;
    }
    const mount = new IntersectionObserver(
      (entries) => entries.some((e) => e.isIntersecting) && setLive(true),
      { rootMargin: MOUNT_MARGIN },
    );
    const keep = new IntersectionObserver(
      (entries) => entries.every((e) => !e.isIntersecting) && setLive(false),
      { rootMargin: KEEP_MARGIN },
    );
    mount.observe(el);
    keep.observe(el);
    return () => {
      mount.disconnect();
      keep.disconnect();
    };
  }, []);

  useEffect(() => {
    const el = holder.current;
    if (!el || !live) return;

    let map: MapLibreMap | null = null;
    let cancelled = false;
    // Set just before an intentional teardown, so the context-lost listener can
    // tell "we released it" from "the browser took it".
    let disposing = false;
    let loaded = false;
    let timer = 0;

    void (async () => {
      let style;
      try {
        style = await cartoStyle();
      } catch {
        if (!cancelled) onFail?.();
        return;
      }
      if (cancelled || !holder.current) return;
      try {
        map = new MapLibreMap({
          container: holder.current,
          style,
          // Require ⌘/ctrl (or two fingers) to zoom, so the map doesn't hijack
          // page scroll while it's embedded in the long book page.
          cooperativeGestures: true,
        });
      } catch {
        onFail?.();
        return;
      }
      const m = map;

      // Built-in controls: zoom/compass (+ pitch indicator), fullscreen (expand
      // a small embedded map), a distance scale, and "you are here".
      m.addControl(new NavigationControl({ visualizePitch: true }), "top-right");
      m.addControl(new FullscreenControl(), "top-right");
      m.addControl(new GeolocateControl({ trackUserLocation: true }), "top-right");
      m.addControl(new ScaleControl({ unit: "metric" }), "bottom-left");

      // MapLibre's attribution is already `compact: true` by default, but it
      // opens *expanded* — `_updateCompact` adds `maplibregl-compact` **and**
      // `maplibregl-compact-show` — and only folds into its ⓘ on the first drag.
      // On a map embedded as a figure in a long page that strip is a caption
      // nobody asked for, sitting over the corner of the map, so it is collapsed
      // as soon as the control exists: the same state a drag leaves it in,
      // reached by removing the one class `_updateCompactMinimize` removes.
      // Credit is one tap away, and the static PNG twin prints it in full
      // (maps/render.py's `_attribution`).
      holder.current
        ?.querySelectorAll(".maplibregl-ctrl-attrib.maplibregl-compact-show")
        .forEach((node) => node.classList.remove("maplibregl-compact-show"));

      // Backstop: if the style never loads (e.g. tiles blocked despite being
      // online), fall back to the static PNG rather than showing a blank box.
      timer = window.setTimeout(() => {
        if (!loaded) onFail?.();
      }, 8000);
      m.on("error", () => {
        if (!loaded) onFail?.();
      });

      // A context killed anyway (another tab eating the budget, a GPU reset)
      // must say so rather than leave a dead canvas sitting there — which is
      // precisely how the over-the-cap maps used to fail: silently.
      //
      // Guarded on `disposing`, because tearing a map down on purpose can lose
      // its context too: without that check every map that scrolled out of view
      // would report itself broken and come back as "couldn't be loaded".
      m.getCanvas().addEventListener("webglcontextlost", () => {
        if (!disposing) onFail?.();
      });

      m.on("load", () => {
      loaded = true;
      window.clearTimeout(timer);

      // Give back the view the user had panned to, if they had; otherwise frame
      // the day.
      const held = camera.current;
      if (held) {
        m.jumpTo(held);
      } else {
        const [[minLat, minLng], [maxLat, maxLng]] = geo.bounds;
        m.fitBounds(
          [
            [minLng, minLat],
            [maxLng, maxLat],
          ],
          { padding: 40, duration: 0, maxZoom: 15 },
        );
      }
      // Only a deliberate move is worth restoring, and `originalEvent` is what
      // says one: `moveend` also fires for the `fitBounds`/`jumpTo` above, so
      // recording every camera change would pin the map to its own first
      // framing and defeat the refit a changed `geo` is owed.
      m.on("moveend", (e) => {
        if (!(e as { originalEvent?: unknown }).originalEvent) return;
        camera.current = {
          center: m.getCenter().toArray() as [number, number],
          zoom: m.getZoom(),
          bearing: m.getBearing(),
          pitch: m.getPitch(),
        };
      });

      // Transport legs first, so a drive's solid geometry draws over them.
      // Dotted and thin: the real path isn't known (a flight has none on the
      // ground), so the line only claims "this leg connects these two points".
      const legs = geo.legs ?? [];
      if (legs.length) {
        m.addSource("tb-legs", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: legs.map((line) => ({
              type: "Feature",
              properties: {},
              geometry: {
                type: "LineString",
                coordinates: line.map(([lat, lng]) => [lng, lat]),
              },
            })),
          },
        });
        m.addLayer({
          id: "tb-legs",
          type: "line",
          source: "tb-legs",
          layout: { "line-cap": "butt", "line-join": "round" },
          paint: {
            "line-color": geo.accent,
            "line-width": 2,
            "line-opacity": 0.85,
            "line-dasharray": [1.5, 2],
          },
        });
      }

      if (geo.routes.length) {
        m.addSource("tb-routes", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: geo.routes.map((line) => ({
              type: "Feature",
              properties: {},
              geometry: {
                type: "LineString",
                coordinates: line.map(([lat, lng]) => [lng, lat]),
              },
            })),
          },
        });
        m.addLayer({
          id: "tb-routes",
          type: "line",
          source: "tb-routes",
          layout: { "line-cap": "round", "line-join": "round" },
          paint: { "line-color": geo.accent, "line-width": 4, "line-opacity": 0.6 },
        });
      }

      if (geo.route_nodes.length) {
        m.addSource("tb-nodes", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: geo.route_nodes.map(([lat, lng]) => ({
              type: "Feature",
              properties: {},
              geometry: { type: "Point", coordinates: [lng, lat] },
            })),
          },
        });
        m.addLayer({
          id: "tb-nodes",
          type: "circle",
          source: "tb-nodes",
          paint: {
            "circle-radius": 4,
            "circle-color": geo.accent,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.5,
          },
        });
      }

      // A trail's decoration, over its line: which way round you walk it, where
      // it starts and finishes, and the points its GPX names. Mirrors
      // `_draw_trail` in maps/render.py — keep the two in step.
      const trail = geo.trail;
      if (trail && trail.line.length >= 2) {
        // Distance ticks go in FIRST, and that ordering is load-bearing:
        // `icon-allow-overlap: true` draws every one of them (a kilometre that
        // silently went missing would make the scale a lie) while the default
        // `icon-ignore-placement: false` still lets each one claim a collision
        // box — so the arrow layer added below, which does respect collisions,
        // keeps clear of them. That is the same "a tick across the line under a
        // head along it is a smudge" rule the print applies with `blocked`.
        const marks = trail.km_marks ?? [];
        const tick = marks.length ? tickImage(geo.accent) : null;
        const tickArrow = marks.length ? arrowImage(geo.accent) : null;
        if (tick && tickArrow) {
          if (!m.hasImage(TICK_IMAGE)) m.addImage(TICK_IMAGE, tick, { pixelRatio: 2 });
          if (!m.hasImage(ARROW_IMAGE))
            m.addImage(ARROW_IMAGE, tickArrow, { pixelRatio: 2 });
          m.addSource("tb-trail-ticks", {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              // The bearing is the model's measured walking direction, never
              // derived from the drawn line here: on a doubled-back trail the
              // nearest point of the line can be on the other leg, i.e. the
              // way you didn't walk, which is the one thing these arrows exist
              // to settle.
              features: marks.map((mk) => ({
                type: "Feature",
                properties: { deg: mk.bearing ?? 0 },
                geometry: { type: "Point", coordinates: [mk.long, mk.lat] },
              })),
            },
          });
          m.addLayer({
            id: "tb-trail-ticks",
            type: "symbol",
            source: "tb-trail-ticks",
            layout: {
              "icon-image": TICK_IMAGE,
              "icon-rotate": ["get", "deg"],
              "icon-rotation-alignment": "map",
              "icon-pitch-alignment": "map",
              "icon-allow-overlap": true,
            },
          });
          // The direction arrow, just past its tick. `icon-anchor: "bottom"`
          // places the glyph above the point *before* `icon-rotate` swings it,
          // so it lands ahead along the bearing — the same "tick, then the way
          // you went" pairing `_draw_trail` offsets by hand.
          m.addLayer({
            id: "tb-trail-tick-arrows",
            type: "symbol",
            source: "tb-trail-ticks",
            layout: {
              "icon-image": ARROW_IMAGE,
              "icon-rotate": ["get", "deg"],
              "icon-anchor": "bottom",
              "icon-rotation-alignment": "map",
              "icon-pitch-alignment": "map",
              "icon-allow-overlap": true,
            },
          });
        }

        const arrows = arrowCandidates(trail.line);
        const image = arrows.length ? arrowImage(geo.accent) : null;
        if (image) {
          // pixelRatio 2: the bitmap is drawn at twice the CSS size it shows at,
          // so the head stays crisp on a retina screen.
          if (!m.hasImage(ARROW_IMAGE)) m.addImage(ARROW_IMAGE, image, { pixelRatio: 2 });
          m.addSource("tb-trail-arrows", {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              features: arrows.map(([lng, lat, deg]) => ({
                type: "Feature",
                properties: { deg },
                geometry: { type: "Point", coordinates: [lng, lat] },
              })),
            },
          });
          m.addLayer({
            id: "tb-trail-arrows",
            type: "symbol",
            source: "tb-trail-arrows",
            layout: {
              "icon-image": ARROW_IMAGE,
              "icon-rotate": ["get", "deg"],
              // rotate with the map, and stay put when it is tilted or turned
              "icon-rotation-alignment": "map",
              "icon-pitch-alignment": "map",
              // `false` is the point: MapLibre then thins the candidates itself,
              // per zoom, keeping the earlier (outbound) head where a trail
              // doubles back over itself.
              "icon-allow-overlap": false,
            },
          });
        }

        const [first] = trail.line;
        const last = trail.line[trail.line.length - 1];
        new Marker({ element: trailMarker("start", geo.accent), anchor: "center" })
          .setLngLat([first[1], first[0]])
          .addTo(m);
        if (apartKm(first, last) > LOOP_MERGE_KM) {
          new Marker({ element: trailMarker("end", geo.accent), anchor: "center" })
            .setLngLat([last[1], last[0]])
            .addTo(m);
        }

        for (const w of trail.waypoints) {
          const el = document.createElement("div");
          el.className = "trail-wpt";
          const dot = document.createElement("span");
          dot.className = "trail-wpt-dot";
          dot.style.background = geo.accent;
          const name = document.createElement("span");
          name.className = "trail-wpt-name";
          name.textContent = w.name;
          name.style.color = geo.accent;
          el.append(dot, name);
          // Anchored on its dot, with the name running off to the right — the
          // print places the label the same way (and tries the other three sides
          // when it collides; here the browser has no such budget, and a name
          // that overlaps can be read by panning).
          new Marker({ element: el, anchor: "left", offset: [-6, 0] })
            .setLngLat([w.long, w.lat])
            .addTo(m);
        }

        // Each tick's kilometre, beside it. A DOM label rather than part of the
        // tick bitmap: the tick rotates with the trail and the number must not.
        for (const mk of marks) {
          const el = document.createElement("div");
          el.className = "trail-km";
          el.textContent = String(mk.km);
          el.style.color = geo.accent;
          // Left of travel, in screen space: heading β points at
          // (sin β, −cos β) with y downwards, whose left is (−cos β, −sin β).
          const b = ((mk.bearing ?? 0) * Math.PI) / 180;
          new Marker({
            element: el,
            anchor: "center",
            offset: [-Math.cos(b) * KM_LABEL_OFFSET, -Math.sin(b) * KM_LABEL_OFFSET],
          })
            .setLngLat([mk.long, mk.lat])
            .addTo(m);
        }
      }

      for (const p of geo.points) {
        const marker = document.createElement("div");
        marker.className = "map-marker";
        marker.textContent = p.label;
        marker.style.background = geo.accent;
        new Marker({ element: marker, anchor: "center" })
          .setLngLat([p.long, p.lat])
          .setPopup(new Popup({ offset: 14, closeButton: false }).setText(p.title))
          .addTo(m);
      }

        // Warm this day's surrounding tiles (a small zoom window over its
        // bounds) so it pans/zooms offline later. Online-only, background.
        if (navigator.onLine) void prefetchTiles(geo.bounds);
      });
    })();

    return () => {
      cancelled = true;
      disposing = true;
      window.clearTimeout(timer);
      map?.remove();
    };
  }, [geo, onFail, live]);

  return (
    <figure className="day-map day-map-gl" ref={figure}>
      <figcaption>{caption}</figcaption>
      <div ref={holder} className="gl-canvas" />
    </figure>
  );
}
