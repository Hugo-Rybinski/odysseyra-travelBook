import type { ReactNode } from "react";
import type { Lang } from "./render/format";
import type { DayView } from "./render/Book";
import { MAP_PROVIDERS, type MapProvider } from "./render/nav";
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
  onCreateBlank: () => void;
  canReopen: boolean;
  busy: boolean;
  // Language
  lang: Lang;
  onToggleLang: (next: Lang) => void;
  // Context
  hasItinerary: boolean;
  mapsInRender: boolean;
  engineReady: boolean;
  // The translated engine boot-stage label, shown while the engine isn't ready.
  engineStageLabel: string;
  // The name of the currently opened file, if any.
  currentFile?: string;
  // Maps
  interactiveMaps: boolean;
  setInteractiveMaps: (v: boolean) => void;
  onRedraw: () => void;
  redrawing: boolean;
  // Display
  clampDescriptions: boolean;
  setClampDescriptions: (v: boolean) => void;
  daysView: DayView;
  setDaysView: (v: DayView) => void;
  transportView: DayView;
  setTransportView: (v: DayView) => void;
  accommodationView: DayView;
  setAccommodationView: (v: DayView) => void;
  mapProvider: MapProvider;
  setMapProvider: (v: MapProvider) => void;
  // PDF export
  inkSaver: boolean;
  setInkSaver: (v: boolean) => void;
  mapsExport: boolean;
  setMapsExport: (v: boolean) => void;
  inferCoords: boolean;
  setInferCoords: (v: boolean) => void;
  mapCountry: string;
  setMapCountry: (v: string) => void;
  onExport: () => void;
  exporting: boolean;
  // Calendar (ICS) export
  onExportIcs: () => void;
  exportingIcs: boolean;
  // App
  checkForUpdate: () => void;
  checking: boolean;
  updating: boolean;
  canInstall: boolean;
  install: () => void;
  isIOS: boolean;
  isStandalone: boolean;
  // Connectivity, surfaced here below the title instead of as a floating banner.
  online: boolean;
  offlineReady: boolean;
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

// A labelled dropdown choosing how a list (days / transports / accommodations)
// starts collapsed. The outer label gives context, so the options stay generic.
function CollapseSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: DayView;
  onChange: (v: DayView) => void;
}) {
  const t = useT();
  return (
    <label className="opt-select">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value as DayView)}>
        <option value="collapse-past">{t("Collapse past")}</option>
        <option value="collapse-all">{t("Collapse all")}</option>
        <option value="current-only">{t("Collapse all but the current")}</option>
        <option value="expand-all">{t("Expand all")}</option>
      </select>
    </label>
  );
}

// The File group (Open / Reopen / Sample + current-file line). Extracted so it
// can also stand alone on the empty state, letting a first-run user open a file
// without going to Options.
export function FileGroup({
  onOpen,
  onReopen,
  onOpenSample,
  onCreateBlank,
  canReopen,
  busy,
  currentFile,
}: {
  onOpen: () => void;
  onReopen: () => void;
  onOpenSample: () => void;
  onCreateBlank: () => void;
  canReopen: boolean;
  busy: boolean;
  currentFile?: string;
}) {
  const t = useT();
  const reopenReason = canReopen ? "" : t("No previously opened file to reopen");
  return (
    <section className="opt-group">
      <h2>{t("File")}</h2>
      <p className="opt-desc">{t("Create a new itinerary, open one, reopen the last one, or load a bundled sample.")}</p>
      <div className="opt-row">
        <Tip text={t("Start a new blank itinerary and edit it from scratch")}>
          <button className="btn" onClick={onCreateBlank} disabled={busy}>
            {t("➕ Create blank")}
          </button>
        </Tip>
        <Tip text={t("Open an Odysseyra TravelBook JSON file from your device")}>
          <button className="btn" onClick={onOpen} disabled={busy}>
            {t("📂 Open JSON…")}
          </button>
        </Tip>
        <Tip text={reopenReason || t("Reopen the last opened file")}>
          <button className="btn subtle" onClick={onReopen} disabled={!canReopen || busy}>
            {t("Reopen last")}
          </button>
        </Tip>
        <Tip text={t("Load the bundled France sample itinerary")}>
          <button className="btn subtle" onClick={onOpenSample} disabled={busy}>
            {t("Sample")}
          </button>
        </Tip>
      </div>
      {currentFile && (
        <p className="opt-current-file">
          {t("Current file opened:")} <span className="filename">{currentFile}</span>
        </p>
      )}
    </section>
  );
}

export function Options(props: OptionsProps) {
  const {
    onOpen,
    onReopen,
    onOpenSample,
    onCreateBlank,
    canReopen,
    busy,
    lang,
    onToggleLang,
    hasItinerary,
    mapsInRender,
    engineReady,
    engineStageLabel,
    currentFile,
    interactiveMaps,
    setInteractiveMaps,
    clampDescriptions,
    setClampDescriptions,
    daysView,
    setDaysView,
    transportView,
    setTransportView,
    accommodationView,
    setAccommodationView,
    mapProvider,
    setMapProvider,
    onRedraw,
    redrawing,
    inkSaver,
    setInkSaver,
    mapsExport,
    setMapsExport,
    inferCoords,
    setInferCoords,
    mapCountry,
    setMapCountry,
    onExport,
    exporting,
    onExportIcs,
    exportingIcs,
    checkForUpdate,
    checking,
    updating,
    canInstall,
    install,
    isIOS,
    isStandalone,
    online,
    offlineReady,
  } = props;

  const t = useT();

  // Why a control is unavailable (empty string = available). Transient states
  // (busy / exporting / a check in flight) just disable without an explanation.
  const noFile = t("Open an itinerary first");
  const engineReason = engineReady ? "" : t("The engine is still starting…");
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
    <section className="options-page" role="region" aria-label={t("Options")}>
      <h1 className="options-title">{t("Options")}</h1>
      <p className={`engine ${engineReady ? "ok" : ""}`}>
        {engineReady ? t("● Engine ready") : `◌ ${engineStageLabel}`}
        {busy && t(" · working…")}
      </p>
      <p className={`net-status ${online ? "online" : "offline"}`}>
        {online
          ? t("● Online")
          : offlineReady
            ? t("⚡ Offline — the app still works.")
            : t("⚡ Offline")}
      </p>
      <div className="options">
      <FileGroup
        onOpen={onOpen}
        onReopen={onReopen}
        onOpenSample={onOpenSample}
        onCreateBlank={onCreateBlank}
        canReopen={canReopen}
        busy={busy}
        currentFile={currentFile}
      />

      <section className="opt-group">
        <h2>{t("Language")}</h2>
        <p className="opt-desc">{t("Set the language of the viewer and PDF exports.")}</p>
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
        <p className="opt-desc">{t("Choose the navigation app, turn on interactive maps, and rebuild this file's cached map images.")}</p>
        <div className="opt-row">
          <label className="opt-select">
            {t("Navigate links open in")}
            <select
              value={mapProvider}
              onChange={(e) => setMapProvider(e.target.value as MapProvider)}
            >
              {MAP_PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </div>
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
        <h2>{t("Display")}</h2>
        <p className="opt-desc">{t("How the on-screen travel book collapses sections and shows long text.")}</p>
        <div className="opt-row">
          <CollapseSelect label={t("Days")} value={daysView} onChange={setDaysView} />
        </div>
        <div className="opt-row">
          <CollapseSelect label={t("Transports")} value={transportView} onChange={setTransportView} />
        </div>
        <div className="opt-row">
          <CollapseSelect
            label={t("Accommodations")}
            value={accommodationView}
            onChange={setAccommodationView}
          />
        </div>
        <div className="opt-row">
          <Tip
            text={t("Truncate long descriptions to a few lines with a 'Show more' link; off shows them in full")}
          >
            <label className="opt-check">
              <input
                type="checkbox"
                checked={clampDescriptions}
                onChange={(e) => setClampDescriptions(e.target.checked)}
              />
              {t("Truncate long descriptions")}
            </label>
          </Tip>
        </div>
      </section>

      <section className="opt-group">
        <h2>{t("PDF export")}</h2>
        <p className="opt-desc">{t("Choose print options, then export the print-ready PDF.")}</p>
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
          {/* Address-inference options only bite when maps are embedded. */}
          <Tip
            text={
              fileReason ||
              (!mapsExport
                ? t("Turn on “Include maps” to use this")
                : t("Geocode activities that have an address but no coordinate so they appear on the maps"))
            }
          >
            <label className={`opt-check ${fileReason || !mapsExport ? "disabled" : ""}`}>
              <input
                type="checkbox"
                checked={inferCoords}
                disabled={!!fileReason || !mapsExport}
                onChange={(e) => setInferCoords(e.target.checked)}
              />
              {t("Infer coordinates from address")}
            </label>
          </Tip>
          <Tip
            text={
              fileReason ||
              (!mapsExport
                ? t("Turn on “Include maps” to use this")
                : t("Restrict address geocoding to these countries (2-letter ISO codes, comma-separated)"))
            }
          >
            <label className={`opt-field ${fileReason || !mapsExport ? "disabled" : ""}`}>
              {t("Map countries")}
              <input
                type="text"
                className="opt-input"
                value={mapCountry}
                placeholder={t("e.g. FR, ES")}
                disabled={!!fileReason || !mapsExport}
                onChange={(e) => setMapCountry(e.target.value)}
              />
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
        <h2>{t("Calendar export")}</h2>
        <p className="opt-desc">{t("Export the trip as an .ics calendar file you can import into Google Calendar (activities, transport, car rentals and accommodation — timezone-aware).")}</p>
        <div className="opt-row">
          <Tip
            text={
              fileReason ||
              engineReason ||
              t("Download an .ics file with one event per activity, transport leg, car pick-up/drop-off and accommodation booking")
            }
          >
            <button
              className="btn"
              onClick={onExportIcs}
              disabled={!!fileReason || exportingIcs || !engineReady}
            >
              {exportingIcs ? t("Exporting…") : t("Export ICS (calendar)")}
            </button>
          </Tip>
        </div>
      </section>

      <section className="opt-group">
        <h2>{t("App")}</h2>
        <p className="opt-desc">{t("Install Odysseyra on this device and check for updates.")}</p>
        {isStandalone ? (
          <p className="opt-note">{t("Odysseyra is already installed on this device. ✓")}</p>
        ) : isIOS ? (
          // iOS Safari has no install API — guide the manual gesture instead of
          // showing a button that can never do anything. Installing also only
          // works from Safari itself (not an in-app browser), so offer a button
          // that re-opens the current page in Safari via the x-safari- scheme.
          <>
            <p className="opt-note">
              {t(
                "On iPhone/iPad you must use Safari: tap the Share button, then “Add to Home Screen” to install.",
              )}
            </p>
            <div className="opt-row">
              <a className="btn" href={`x-safari-${location.href}`}>
                {t("Open in Safari")}
              </a>
            </div>
          </>
        ) : null}
        <div className="opt-row">
          {!isIOS && !isStandalone && (
            <Tip text={installReason || t("Install Odysseyra TravelBook as an app on this device")}>
              <button className="btn" onClick={install} disabled={!canInstall}>
                {t("Install as an app")}
              </button>
            </Tip>
          )}
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
    </section>
  );
}
