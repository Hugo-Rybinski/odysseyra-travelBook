import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { viteStaticCopy } from "vite-plugin-static-copy";

// The travel-book viewer runs the Python `travelbook` package in the browser via
// Pyodide (loaded from a version-pinned CDN, then cached by the service worker
// so the app works offline after first load). The local wheel and the bundled
// example itineraries are copied into the build and precached.
export default defineConfig({
  // Allow the production preview to be reached over a Tailscale HTTPS hostname
  // (needed so a phone can install the PWA + test offline over a secure origin).
  preview: { host: true, allowedHosts: [".ts.net"] },
  build: {
    // MapLibre is a deliberately large, lazily-loaded chunk — don't warn on it.
    chunkSizeWarningLimit: 1100,
    rollupOptions: {
      output: {
        // Split MapLibre into its own chunk so it loads on demand (interactive
        // maps only) and can be kept out of the offline precache.
        manualChunks(id) {
          if (id.includes("node_modules/maplibre-gl")) return "maplibre";
        },
      },
    },
  },
  plugins: [
    react(),
    // Copy the example itineraries in as bundled samples to open.
    viteStaticCopy({
      targets: [{ src: "../examples/*.json", dest: "samples" }],
    }),
    VitePWA({
      // "prompt" so the app controls the update lifecycle (see PwaProvider): it
      // auto-applies a new version and reloads once, and exposes a manual
      // "Update" button — no DevTools dance to pick up a new deploy.
      registerType: "prompt",
      includeAssets: ["icon.svg"],
      manifest: {
        name: "Travelbook Viewer",
        short_name: "Travelbook",
        description:
          "Open a local itinerary JSON and render the travel book, with PDF export on the side.",
        theme_color: "#1f4e5f",
        background_color: "#ffffff",
        display: "standalone",
        start_url: "./",
        icons: [
          {
            src: "icon.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any maskable",
          },
        ],
      },
      workbox: {
        // Precache the app shell + the local Python wheel (fonts included). The
        // MapLibre chunk is included too: it's code-split (so it's only parsed
        // when the interactive map is used) but precaching it means it's served
        // with the correct MIME from cache and works offline — rather than being
        // fetched at runtime, which risked the navigation fallback returning
        // index.html for it (a "non-JavaScript MIME type" module error).
        globPatterns: ["**/*.{js,css,html,svg,json,whl}"],
        maximumFileSizeToCacheInBytes: 8 * 1024 * 1024,
        // Never serve the SPA fallback (index.html) for asset URLs — a missing
        // hashed chunk should 404 cleanly (and trigger a reload, see main.tsx),
        // not masquerade as HTML.
        navigateFallbackDenylist: [/^\/assets\//],
        runtimeCaching: [
          {
            // Pyodide runtime + core packages (wasm, stdlib, Pillow, …).
            urlPattern: /^https:\/\/cdn\.jsdelivr\.net\/pyodide\/.*/,
            handler: "CacheFirst",
            options: {
              cacheName: "pyodide-cdn",
              expiration: { maxEntries: 64 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Pure-Python dependency wheels micropip pulls from PyPI (fpdf2, …).
            urlPattern: /^https:\/\/files\.pythonhosted\.org\/.*/,
            handler: "CacheFirst",
            options: {
              cacheName: "pypi-wheels",
              expiration: { maxEntries: 32 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Carto basemaps for the maps: the raster tiles (static PNG), the
            // vector style/glyphs/sprite, and the vector tiles for the
            // interactive map — including the sharded tiles-a/b/c/d hosts. Cache
            // heavily so a day built (and prefetched) once works offline.
            urlPattern: /^https:\/\/([a-z0-9-]+\.)?basemaps\.cartocdn\.com\/.*/,
            handler: "CacheFirst",
            options: {
              cacheName: "map-tiles",
              expiration: { maxEntries: 4000, maxAgeSeconds: 60 * 60 * 24 * 90 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // OSRM driving routes and Nominatim geocoding for the maps.
            urlPattern: /^https:\/\/(router\.project-osrm\.org|nominatim\.openstreetmap\.org)\/.*/,
            handler: "CacheFirst",
            options: {
              cacheName: "map-data",
              expiration: { maxEntries: 500, maxAgeSeconds: 60 * 60 * 24 * 90 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
});
