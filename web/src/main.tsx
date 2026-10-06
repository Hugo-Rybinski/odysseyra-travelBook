import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { PwaProvider } from "./pwa/PwaProvider";
import "./index.css";
import "./tipPosition";
import { loadPrefs } from "./file/prefs";
import { applyTheme, resolveTheme } from "./theme";

// Theme before the first paint, so a night launch doesn't flash white. No trip
// is loaded yet, so `auto` uses the 07:00–19:00 fallback here; <App> refines it
// with the trip's sun times once the book is open.
applyTheme(resolveTheme(loadPrefs().theme, new Date(), null));

// The service worker is registered by useRegisterSW() inside <PwaProvider>, the
// single owner of the update lifecycle. Its progress and the manual check's
// answer surface in <ActivityIndicator>, the same card the engine's work uses.

// If a lazily-imported chunk fails to load because the deploy moved on (a new
// build changed hashes while an old page/SW was live), reload once to pick up
// the fresh manifest. Only when online — offline failures are handled by the
// feature's own fallback (e.g. the map falls back to its static image).
window.addEventListener("vite:preloadError", () => {
  const KEY = "tb-preload-reloaded";
  if (navigator.onLine && !sessionStorage.getItem(KEY)) {
    sessionStorage.setItem(KEY, "1");
    window.location.reload();
  }
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PwaProvider>
      <App />
    </PwaProvider>
  </React.StrictMode>,
);
