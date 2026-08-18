import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRegisterSW } from "virtual:pwa-register/react";

// Single owner of the service-worker registration. It auto-applies a new version
// (activate the waiting SW + reload once) the moment one is detected — so a plain
// reload after a deploy always lands on the latest build, no DevTools needed —
// and exposes a manual "check for updates" for the header button. Everything
// SW-related reads from here (there must be exactly one useRegisterSW caller).
interface PwaContextValue {
  offlineReady: boolean;
  dismissOfflineReady: () => void;
  checkForUpdate: () => void;
  checking: boolean; // a manual check is in flight
  updating: boolean; // a new version is being applied (page will reload)
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
      }}
    >
      {children}
    </PwaContext.Provider>
  );
}
