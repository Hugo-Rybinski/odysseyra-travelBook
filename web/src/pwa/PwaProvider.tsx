import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRegisterSW } from "virtual:pwa-register/react";

// Non-standard install-prompt event (not in the DOM lib).
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

// Single owner of the service-worker registration. It auto-applies a new version
// (activate the waiting SW + reload once) the moment one is detected — so a plain
// reload after a deploy always lands on the latest build, no DevTools needed —
// and exposes a manual "check for updates" for the header button. It also owns
// the deferred install prompt (`beforeinstallprompt`), surfacing it as
// `canInstall` + `install()` for the Options panel's "Install as an app" action.
// Everything PWA-related reads from here (there must be exactly one
// useRegisterSW caller).
interface PwaContextValue {
  offlineReady: boolean;
  dismissOfflineReady: () => void;
  checkForUpdate: () => void;
  checking: boolean; // a manual check is in flight
  updating: boolean; // a new version is being applied (page will reload)
  canInstall: boolean; // the browser offered an install prompt we can replay
  install: () => Promise<void>;
}

const PwaContext = createContext<PwaContextValue | null>(null);

export function usePwa(): PwaContextValue {
  const ctx = useContext(PwaContext);
  if (!ctx) throw new Error("usePwa must be used within <PwaProvider>");
  return ctx;
}

export function PwaProvider({ children }: { children: ReactNode }) {
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | undefined>();
  const [checking, setChecking] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [installEvt, setInstallEvt] = useState<BeforeInstallPromptEvent | null>(null);

  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_swUrl, r) {
      setRegistration(r);
    },
  });

  // Auto-apply: as soon as a new version is waiting, activate it and reload.
  useEffect(() => {
    if (needRefresh) {
      setUpdating(true);
      void updateServiceWorker(true);
    }
  }, [needRefresh, updateServiceWorker]);

  // Capture the browser's deferred install prompt so we can replay it on demand
  // (from the Options panel), and drop it once the app is installed.
  useEffect(() => {
    const onBeforeInstall = (e: Event) => {
      e.preventDefault();
      setInstallEvt(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => setInstallEvt(null);
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  const install = useCallback(async () => {
    if (!installEvt) return;
    await installEvt.prompt();
    await installEvt.userChoice;
    setInstallEvt(null); // a prompt can only be used once
  }, [installEvt]);

  const checkForUpdate = useCallback(() => {
    if (!registration) return;
    setChecking(true);
    // A found update flips needRefresh → the effect above applies it (reload).
    // If nothing's new, just clear the transient "checking" state.
    void registration
      .update()
      .catch(() => {})
      .finally(() => setTimeout(() => setChecking(false), 1200));
  }, [registration]);

  return (
    <PwaContext.Provider
      value={{
        offlineReady,
        dismissOfflineReady: () => setOfflineReady(false),
        checkForUpdate,
        checking,
        updating,
        canInstall: !!installEvt,
        install,
      }}
    >
      {children}
    </PwaContext.Provider>
  );
}
