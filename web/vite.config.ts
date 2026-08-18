import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { viteStaticCopy } from "vite-plugin-static-copy";

// The travel-book viewer runs the Python `travelbook` package in the browser via
// Pyodide (loaded from a version-pinned CDN, then cached by the service worker
// so the app works offline after first load). The local wheel and the bundled
// example itineraries are copied into the build and precached.
export default defineConfig({
  plugins: [
    react(),
    // Copy the example itineraries in as bundled samples to open.
    viteStaticCopy({
      targets: [{ src: "../examples/*.json", dest: "samples" }],
    }),
    VitePWA({
      registerType: "autoUpdate",
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
        // Precache the app shell + the local Python wheel (fonts included).
        globPatterns: ["**/*.{js,css,html,svg,json,whl}"],
        maximumFileSizeToCacheInBytes: 8 * 1024 * 1024,
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
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
});
