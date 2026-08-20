import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { PwaProvider } from "./pwa/PwaProvider";
import "./index.css";
import "./tipPosition";

// The service worker is registered by useRegisterSW() inside <PwaStatus/>, which
// also surfaces the update-available / offline-ready toasts.

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
