import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRegisterSW } from "virtual:pwa-register/react";

import { COMMIT_HASH, fetchDeployedVersion } from "../version";

// Non-standard install-prompt event (not in the DOM lib).
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/** What a manual "Check for updates" turned up. `null` before one has run, and
 * again once the notice has been on screen long enough to read.
 *
 * Three outcomes, not two: "couldn't ask" is not "up to date". The button is
 * enabled offline, and reporting a failed check as good news is the one answer
 * that would be actively wrong. */
export type UpdateCheck =
  | { kind: "none" }
  | { kind: "found"; hash: string; date: string }
  | { kind: "unreachable" };

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
  /** The last check's outcome, for the caller to word and show. */
  updateCheck: UpdateCheck | null;
  updating: boolean; // a new version is being applied (page will reload)
  canInstall: boolean; // the browser offered an install prompt we can replay
  install: () => Promise<void>;
  // iOS Safari has no install API (`beforeinstallprompt` never fires), so the
  // button can't work there — the UI shows "Share → Add to Home Screen" instead.
  isIOS: boolean;
  // Already running as an installed PWA (standalone) — hide the install UI.
  isStandalone: boolean;
}

// iOS Safari (incl. iPadOS pretending to be desktop) — no programmatic install.
function detectIOS(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent || "";
  return (
    /iphone|ipad|ipod/i.test(ua) ||
    // iPadOS 13+ reports as "MacIntel" but is touch-capable.
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

function detectStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    // Non-standard iOS Safari flag.
    (navigator as unknown as { standalone?: boolean }).standalone === true
  );
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
  const [updateCheck, setUpdateCheck] = useState<UpdateCheck | null>(null);
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

  // How long a finished check's notice stays up. Long enough to read a hash and
  // a date; short enough that it doesn't linger as a permanent badge.
  const NOTICE_MS = 6000;

  const checkForUpdate = useCallback(() => {
    setChecking(true);
    setUpdateCheck(null);
    void (async () => {
      // Ask the *server* what is deployed, and compare. Asking the service
      // worker instead would only tell us whether it decided to install
      // something — never which build, which is what the notice has to name.
      // It also means the check still answers with no registration at all
      // (dev, or a browser with the SW disabled), where it used to bail out
      // silently and leave the button doing nothing.
      const deployed = await fetchDeployedVersion();
      if (!deployed) setUpdateCheck({ kind: "unreachable" });
      else if (deployed.hash && deployed.hash !== COMMIT_HASH) {
        setUpdateCheck({ kind: "found", hash: deployed.hash, date: deployed.date });
      } else setUpdateCheck({ kind: "none" });

      // Then let the service worker do the applying: a found update flips
      // `needRefresh` → the effect above activates it and reloads. So the
      // "Update found" notice is what the user reads on the way to the reload,
      // and `updating` takes the line over when it starts.
      if (registration) await registration.update().catch(() => {});
      setChecking(false);
    })();
  }, [registration]);

  // Retire a finished notice on its own. Deliberately not cleared on the next
  // click — `checkForUpdate` does that — so a second check can't briefly show
  // the previous answer.
  useEffect(() => {
    if (!updateCheck) return;
    const id = setTimeout(() => setUpdateCheck(null), NOTICE_MS);
    return () => clearTimeout(id);
  }, [updateCheck]);

  return (
    <PwaContext.Provider
      value={{
        offlineReady,
        dismissOfflineReady: () => setOfflineReady(false),
        checkForUpdate,
        checking,
        updateCheck,
        updating,
        canInstall: !!installEvt,
        install,
        isIOS: detectIOS(),
        isStandalone: detectStandalone(),
      }}
    >
      {children}
    </PwaContext.Provider>
  );
}
