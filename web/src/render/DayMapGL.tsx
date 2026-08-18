import { useEffect, useRef } from "react";
import { Map as MapLibreMap, Marker, Popup, setWorkerUrl } from "maplibre-gl";
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

  useEffect(() => {
    const el = holder.current;
    if (!el) return;

    let map: MapLibreMap | null = null;
    let cancelled = false;
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
        map = new MapLibreMap({ container: holder.current, style });
      } catch {
        onFail?.();
        return;
      }
      const m = map;

      // Backstop: if the style never loads (e.g. tiles blocked despite being
      // online), fall back to the static PNG rather than showing a blank box.
      timer = window.setTimeout(() => {
        if (!loaded) onFail?.();
      }, 8000);
      m.on("error", () => {
        if (!loaded) onFail?.();
      });

      m.on("load", () => {
      loaded = true;
      window.clearTimeout(timer);

      const [[minLat, minLng], [maxLat, maxLng]] = geo.bounds;
      m.fitBounds(
        [
          [minLng, minLat],
          [maxLng, maxLat],
        ],
        { padding: 40, duration: 0, maxZoom: 15 },
      );

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
      window.clearTimeout(timer);
      map?.remove();
    };
  }, [geo, onFail]);

  return (
    <figure className="day-map day-map-gl">
      <figcaption>{caption}</figcaption>
      <div ref={holder} className="gl-canvas" />
    </figure>
  );
}
