import { useEffect, useState } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";

// Non-standard install-prompt event (not in the DOM lib).
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

// A small, unobtrusive strip of toasts: offline notice, "ready to work offline",
// a new-version prompt (from the service worker), and an install prompt. The SW
// only registers in a production build, so the update/offline-ready toasts are
// inert in dev — the offline banner and install prompt still work.
export function PwaStatus() {
  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW();

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

      {needRefresh && (
        <div className="toast update" role="alert">
          A new version is available.
          <span className="toast-actions">
            <button className="btn" onClick={() => updateServiceWorker(true)}>
              Reload
            </button>
            <button className="btn ghost dark" onClick={() => setNeedRefresh(false)}>
              Later
            </button>
          </span>
        </div>
      )}

      {offlineReady && !needRefresh && (
        <div className="toast ok" role="status">
          ✓ Ready to work offline.
          <button className="link-btn" onClick={() => setOfflineReady(false)}>
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
