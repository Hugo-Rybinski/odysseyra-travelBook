import { useEffect, useState } from "react";
import { usePwa } from "./PwaProvider";

// Non-standard install-prompt event (not in the DOM lib).
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

// A small, unobtrusive strip of toasts: offline notice, "ready to work offline",
// an "updating…" notice, and an install prompt. Service-worker state comes from
// <PwaProvider> (the single registration); updates auto-apply, so there's no
// manual reload prompt here — the header's "Update" button forces a check.
export function PwaStatus() {
  const { offlineReady, dismissOfflineReady, checking, updating } = usePwa();

  const [offline, setOffline] = useState(!navigator.onLine);
  const [installEvt, setInstallEvt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    const goOnline = () => setOffline(false);
    const goOffline = () => setOffline(true);
    const onBeforeInstall = (e: Event) => {
      e.preventDefault();
      setInstallEvt(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => setInstallEvt(null);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  const install = async () => {
    if (!installEvt) return;
    await installEvt.prompt();
    await installEvt.userChoice;
    setInstallEvt(null);
  };

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

      {installEvt && (
        <div className="toast install" role="status">
          Install Travelbook Viewer as an app?
          <span className="toast-actions">
            <button className="btn" onClick={install}>
              Install
            </button>
            <button className="btn ghost dark" onClick={() => setInstallEvt(null)}>
              Not now
            </button>
          </span>
        </div>
      )}
    </div>
  );
}
