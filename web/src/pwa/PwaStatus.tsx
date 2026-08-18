import { useEffect, useState } from "react";
import { usePwa } from "./PwaProvider";

// A small, unobtrusive strip of toasts: offline notice, "ready to work offline",
// and an "updating…"/"checking…" notice. Service-worker state comes from
// <PwaProvider> (the single registration); updates auto-apply, so there's no
// manual reload prompt here — the Options panel's "Check for updates" button
// forces a check, and "Install as an app" replays the install prompt.
export function PwaStatus() {
  const { offlineReady, dismissOfflineReady, checking, updating } = usePwa();

  const [offline, setOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const goOnline = () => setOffline(false);
    const goOffline = () => setOffline(true);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  return (
    <div className="toasts" aria-live="polite">
      {offline && (
        <div className="toast offline" role="status">
          ⚡ You’re offline — the app still works.
        </div>
      )}

      {updating && (
        <div className="toast update" role="status">
          Updating to the latest version…
        </div>
      )}

      {checking && !updating && (
        <div className="toast update" role="status">
          Checking for updates…
        </div>
      )}

      {offlineReady && !updating && (
        <div className="toast ok" role="status">
          ✓ Ready to work offline.
          <button className="link-btn" onClick={dismissOfflineReady}>
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
