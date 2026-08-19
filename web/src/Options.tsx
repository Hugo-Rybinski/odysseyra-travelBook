import type { ReactNode } from "react";
import type { Lang } from "./render/format";
import { useT } from "./i18n";

// The options panel: every control that used to live in the top bar, moved into
// one place and grouped by theme (File / Language / Maps / PDF export / App).
// App owns all the state and handlers; this is a pure presentational panel.
//
// Controls are never hidden — when one can't be used yet (no file open, the
// itinerary opts out of maps, the browser hasn't offered an install prompt…) it
// is greyed out and a hover/focus tooltip explains why. The tooltip is a custom
// CSS bubble (`data-tip`), not the native `title` attribute, which proved
// unreliable (delayed, and swallowed by disabled controls). Disabled controls
// get `pointer-events: none` (see CSS) so hover reaches the titled wrapper.
export interface OptionsProps {
  // File
  onOpen: () => void;
  onReopen: () => void;
  onOpenSample: () => void;
  canReopen: boolean;
  busy: boolean;
  // Language
  lang: Lang;
  onToggleLang: (next: Lang) => void;
  // Context
  hasItinerary: boolean;
  mapsInRender: boolean;
  engineReady: boolean;
  // Maps
  interactiveMaps: boolean;
  setInteractiveMaps: (v: boolean) => void;
  onRedraw: () => void;
  redrawing: boolean;
  // PDF export
  inkSaver: boolean;
  setInkSaver: (v: boolean) => void;
  mapsExport: boolean;
  setMapsExport: (v: boolean) => void;
  onExport: () => void;
  exporting: boolean;
  // App
  checkForUpdate: () => void;
  checking: boolean;
  updating: boolean;
  canInstall: boolean;
  install: () => void;
}

// Anchor a hover/focus tooltip on a control. The bubble is drawn by CSS from the
// `data-tip` attribute; the span still receives hover even when the inner
// control is disabled (which has pointer-events: none).
function Tip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <span className="tip" data-tip={text}>
      {children}
    </span>
  );
}

export function Options(props: OptionsProps) {
  const {
    onOpen,
    onReopen,
    onOpenSample,
    canReopen,
    busy,
    lang,
    onToggleLang,
    hasItinerary,
    mapsInRender,
    engineReady,
    interactiveMaps,
    setInteractiveMaps,
    onRedraw,
    redrawing,
    inkSaver,
    setInkSaver,
    mapsExport,
    setMapsExport,
    onExport,
    exporting,
    checkForUpdate,
    checking,
    updating,
    canInstall,
    install,
  } = props;

  const t = useT();

  // Why a control is unavailable (empty string = available). Transient states
  // (busy / exporting / a check in flight) just disable without an explanation.
  const noFile = t("Open an itinerary first");
  const engineReason = engineReady ? "" : t("The engine is still starting…");
  const reopenReason = canReopen ? "" : t("No previously opened file to reopen");
  const fileReason = hasItinerary ? "" : noFile;
  const mapsReason = !hasItinerary
    ? noFile
    : !mapsInRender
      ? t("This itinerary doesn't enable maps (include_maps_in_render is off)")
      : "";
  const installReason = canInstall
    ? ""
    : t(
        "Your browser hasn't offered to install the app (it may already be installed, or your browser doesn't support this)",
      );

  return (
    <div className="options" role="region" aria-label={t("Options")}>
      <section className="opt-group">
        <h2>{t("File")}</h2>
        <div className="opt-row">
          <Tip text={t("Open a travelbook JSON file from your device")}>
            <button className="btn" onClick={onOpen} disabled={busy}>
              {t("Open JSON…")}
            </button>
          </Tip>
          <Tip text={reopenReason || t("Reopen the last opened file")}>
            <button className="btn subtle" onClick={onReopen} disabled={!canReopen || busy}>
              {t("Reopen last")}
            </button>
          </Tip>
          <Tip text={t("Load the bundled Pyrenees sample itinerary")}>
            <button className="btn subtle" onClick={onOpenSample} disabled={busy}>
              {t("Sample")}
            </button>
          </Tip>
        </div>
      </section>

      <section className="opt-group">
        <h2>{t("Language")}</h2>
        <div className="opt-row">
          <div className="seg" role="group" aria-label={t("Language")}>
            {(["en", "fr"] as Lang[]).map((l) => (
              <button
                key={l}
                className={`seg-btn ${lang === l ? "active" : ""}`}
                onClick={() => onToggleLang(l)}
                aria-pressed={lang === l}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="opt-group">
        <h2>{t("Maps")}</h2>
        <div className="opt-row">
          <Tip
            text={
              mapsReason ||
              t(
                "Interactive (pan/zoom) maps; each day's area is prefetched for offline use, and falls back to the static image if it can't load",
              )
            }
          >
            <label className={`opt-check ${mapsReason ? "disabled" : ""}`}>
              <input
                type="checkbox"
                checked={interactiveMaps}
                disabled={!!mapsReason}
                onChange={(e) => setInteractiveMaps(e.target.checked)}
              />
              {t("Interactive maps")}
            </label>
          </Tip>
          <Tip text={mapsReason || engineReason || t("Discard this file's cached map images and rebuild them")}>
            <button
              className="btn subtle"
              onClick={onRedraw}
              disabled={!!mapsReason || redrawing || !engineReady}
            >
              {redrawing ? t("Redrawing…") : t("Redraw maps")}
            </button>
          </Tip>
        </div>
      </section>

      <section className="opt-group">
        <h2>{t("PDF export")}</h2>
        <div className="opt-row">
          <Tip
            text={
              fileReason || t("Outlines instead of solid accent fills — less colored ink when printing")
            }
          >
            <label className={`opt-check ${fileReason ? "disabled" : ""}`}>
              <input
                type="checkbox"
                checked={inkSaver}
                disabled={!!fileReason}
                onChange={(e) => setInkSaver(e.target.checked)}
              />
              {t("Ink-saver")}
            </label>
          </Tip>
          <Tip
            text={
              fileReason || t("Embed the per-day maps in the exported PDF (fetches map tiles; slower)")
            }
          >
            <label className={`opt-check ${fileReason ? "disabled" : ""}`}>
              <input
                type="checkbox"
                checked={mapsExport}
                disabled={!!fileReason}
                onChange={(e) => setMapsExport(e.target.checked)}
              />
              {t("Include maps")}
            </label>
          </Tip>
          <Tip
            text={
              fileReason ||
              engineReason ||
              (mapsExport ? t("Maps are embedded in the PDF") : t("Maps are omitted from the PDF"))
            }
          >
            <button
              className="btn"
              onClick={onExport}
              disabled={!!fileReason || exporting || !engineReady}
            >
              {exporting ? t("Exporting…") : t("Export PDF")}
            </button>
          </Tip>
        </div>
      </section>

      <section className="opt-group">
        <h2>{t("App")}</h2>
        <div className="opt-row">
          <Tip text={installReason || t("Install Travelbook Viewer as an app on this device")}>
            <button className="btn" onClick={install} disabled={!canInstall}>
              {t("Install as an app")}
            </button>
          </Tip>
          <Tip text={t("Check for a new version and update to it")}>
            <button
              className="btn subtle"
              onClick={checkForUpdate}
              disabled={checking || updating}
            >
              {updating ? t("Updating…") : checking ? t("Checking…") : t("Check for updates")}
            </button>
          </Tip>
        </div>
      </section>
    </div>
  );
}
