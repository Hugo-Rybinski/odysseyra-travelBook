import { usePwa } from "./PwaProvider";
import { useT } from "../i18n";

// A small, unobtrusive strip of toasts for update lifecycle only
// ("updating…"/"checking…"). Connectivity state (online / ready-to-work-offline)
// is no longer a floating banner — it lives in the Options panel header instead.
// Service-worker state comes from <PwaProvider> (the single registration);
// updates auto-apply, so there's no manual reload prompt here.
export function PwaStatus() {
  const { checking, updating } = usePwa();
  const t = useT();

  return (
    <div className="toasts" aria-live="polite">
      {updating && (
        <div className="toast update" role="status">
          {t("Updating to the latest version…")}
        </div>
      )}

      {checking && !updating && (
        <div className="toast update" role="status">
          {t("Checking for updates…")}
        </div>
      )}
    </div>
  );
}
