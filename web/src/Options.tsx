import type { ReactNode } from "react";
import { fmtDate, type Lang } from "./render/format";
import type { DayView } from "./render/Book";
import { MAP_PROVIDERS, type MapProvider } from "./render/nav";
import { COMMIT_HASH, commitDateLabel, commitUrl } from "./version";
import { useT, useTx } from "./i18n";
import type { CachedDay } from "./maps/mapCache";
import type { Day } from "./types/resolved";

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
  // Any hike carries an embedded GPX — those draw an interactive trail map of
  // their own, whatever `include_maps_in_render` says.
  hasHikeTracks: boolean;
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
  // The map cache, listed day by day (see `CacheList`). `days` is the open
  // trip's resolved days — the listing is a view of *them*, not of the store, so
  // a day that has no cached map still gets a row and a button.
  days: Day[];
  docKey: string | null; // the open document's cache key ("which rows are mine")
  cacheEntries: CachedDay[];
  cacheError: string | null;
  storage: { usage: number; quota: number } | null;
  onRedrawDay: (index: number) => void;
  redrawingDay: number | null;
  onClearOthers: () => void;
  // Display
  clampDescriptions: boolean;
  setClampDescriptions: (v: boolean) => void;
  showForecast: boolean;
  setShowForecast: (v: boolean) => void;
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

/** Bytes as a short human figure. One decimal below 10 units, whole above, so a
 * column of them reads at one width without a thousands separator. */
function fmtBytes(n: number): string {
  const units = ["B", "KB", "MB", "GB"];
  let v = n;
  let u = 0;
  while (v >= 1024 && u < units.length - 1) {
    v /= 1024;
    u++;
  }
  return `${v < 10 && u > 0 ? v.toFixed(1) : Math.round(v)} ${units[u]}`;
}

// The per-day map cache, listed beside "Redraw all maps".
//
// It is a view of the **trip's days**, not of the store: every day gets a row,
// carrying its size when its maps are cached and "not cached" when they aren't,
// with a button either way. That's the reading that answers the question the
// list is for — *which* of my maps are being redrawn every time — where a list
// of only what's present would show a short list and leave the gaps to be
// inferred.
//
// Entries belonging to other documents are summed into a single line rather than
// enumerated: they can't be redrawn from here (the file isn't open, so there's
// nothing to render from), and what matters about them is only how much room
// they are holding. Which is worth showing, because at ~20 MB a trip they are
// the reason the store fills up.
function CacheList({
  days,
  docKey,
  entries,
  error,
  storage,
  onRedrawDay,
  redrawingDay,
  onClearOthers,
  disabledReason,
  lang,
}: {
  days: Day[];
  docKey: string | null;
  entries: CachedDay[];
  error: string | null;
  storage: { usage: number; quota: number } | null;
  onRedrawDay: (index: number) => void;
  redrawingDay: number | null;
  onClearOthers: () => void;
  disabledReason: string;
  lang: Lang;
}) {
  const t = useT();
  const mine = new Map(entries.filter((e) => e.hash === docKey).map((e) => [e.index, e]));
  const others = entries.filter((e) => e.hash !== docKey);
  const otherFiles = new Set(others.map((e) => e.file || "?"));
  const otherBytes = others.reduce((n, e) => n + (e.bytes || 0), 0);
  const myBytes = [...mine.values()].reduce((n, e) => n + (e.bytes || 0), 0);

  return (
    <div className="cache-block">
      <h3>{t("Cached map images")}</h3>
      <p className="opt-desc">
        {t(
          "Each day's maps are drawn once and kept on this device, keyed by the itinerary's contents — so editing a value redraws, but reopening the same file doesn't.",
        )}
      </p>
      <p className="cache-summary">
        {t("{cached} of {total} days cached · {size}", {
          cached: mine.size,
          total: days.length,
          size: fmtBytes(myBytes),
        })}
        {storage && storage.quota > 0 && (
          // Headroom, not usage. The origin's *usage* is within a megabyte or
          // two of the trip total right beside it, so the line read as the same
          // figure printed twice; how much room is left is the different
          // question, and the one that says whether the next trip will fit.
          <span className="cache-room">
            {" · "}
            {t("{free} still free on this device", {
              free: fmtBytes(Math.max(0, storage.quota - storage.usage)),
            })}
          </span>
        )}
      </p>
      {error && (
        <p className="cache-warn">
          ⚠️{" "}
          {error === "quota"
            ? t(
                "The last map couldn't be stored — this device is out of room. Clear the cached maps below, then redraw.",
              )
            : t("The last map couldn't be stored ({error}), so it will be redrawn every time.", {
                error,
              })}
        </p>
      )}
      {days.length > 0 && (
        <ul className="cache-list">
          {days.map((d, i) => {
            const hit = mine.get(i);
            return (
              <li key={i} className={`cache-row ${hit ? "" : "miss"}`}>
                <span className="cache-day">
                  {t("Day {n}", { n: d.day_number || i + 1 })}
                  {d.date && <span className="cache-date">{fmtDate(d.date, lang)}</span>}
                </span>
                <span className="cache-name">{d.title || t("(untitled)")}</span>
                <span className="cache-size">{hit ? fmtBytes(hit.bytes) : t("not cached")}</span>
                <Tip
                  text={
                    disabledReason ||
                    (hit
                      ? t("Discard this day's cached maps and draw them again")
                      : t("Draw this day's maps now"))
                  }
                >
                  <button
                    className="btn subtle tiny"
                    onClick={() => onRedrawDay(i)}
                    disabled={!!disabledReason || redrawingDay !== null}
                  >
                    {redrawingDay === i ? t("Redrawing…") : hit ? t("Redraw") : t("Draw")}
                  </button>
                </Tip>
              </li>
            );
          })}
        </ul>
      )}
      {others.length > 0 && (
        <p className="cache-others">
          {/* Two templates rather than one, because this i18n layer has no
              plural rules and "1 other itineraries" is the commonest case. */}
          {otherFiles.size === 1
            ? t("One other itinerary is holding {size}.", { size: fmtBytes(otherBytes) })
            : t("{files} other itineraries are holding {size}.", {
                files: otherFiles.size,
                size: fmtBytes(otherBytes),
              })}{" "}
          <button className="btn subtle tiny" onClick={onClearOthers}>
            {t("Clear those")}
          </button>
        </p>
      )}
      {!days.length && !others.length && (
        <p className="opt-note">{t("Nothing is cached yet.")}</p>
      )}
    </div>
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
    hasHikeTracks,
    engineReady,
    engineStageLabel,
    currentFile,
    interactiveMaps,
    setInteractiveMaps,
    clampDescriptions,
    setClampDescriptions,
    showForecast,
    setShowForecast,
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
    days,
    docKey,
    cacheEntries,
    cacheError,
    storage,
    onRedrawDay,
    redrawingDay,
    onClearOthers,
    inkSaver,
    setInkSaver,
    mapsExport,
    setMapsExport,
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
  const tx = useTx();

  // Why a control is unavailable (empty string = available). Transient states
  // (busy / exporting / a check in flight) just disable without an explanation.
  const noFile = t("Open an itinerary first");
  const engineReason = engineReady ? "" : t("The engine is still starting…");
  const fileReason = hasItinerary ? "" : noFile;
  // One question, asked of both the interactive toggle and the redraw buttons:
  // is there any per-day map to draw at all? Two independent reasons there can
  // be — the trip opts into maps, or a hike carries a GPX, whose trail map is
  // drawn independently of that switch (`App`'s `wantsDayRender`, mirroring
  // bridge.py's `render_day`).
  //
  // The redraw buttons used to gate on `include_maps_in_render` alone, which
  // left them dead for a maps-off trip with a hike track — a trip whose days
  // really are rendered, and whose trail PNGs really are cached, so the one
  // control for rebuilding them was unavailable exactly where the cache was in
  // use.
  const mapsReason = !hasItinerary
    ? noFile
    : !mapsInRender && !hasHikeTracks
      ? t("This itinerary doesn't enable maps (include_maps_in_render is off)")
      : "";
  const interactiveReason = mapsReason;
  const installReason = canInstall
    ? ""
    : t(
        "Your browser hasn't offered to install the app (it may already be installed, or your browser doesn't support this)",
      );

  const versionDate = commitDateLabel();
  // Link the commit hash to its GitHub page when we know the repo URL; otherwise
  // it's plain text. The rich `tx` swaps the {hash} token for the link node.
  const versionHref = commitUrl();
  const hashNode = versionHref ? {
    hash: (
      <a
        className="version-link"
        href={versionHref}
        target="_blank"
        rel="noopener noreferrer"
        title={t("View this commit on GitHub")}
      >
        {COMMIT_HASH}
      </a>
    ),
  } : {};
  const versionTemplate = versionDate
    ? "Current version: {hash} ({date})"
    : "Current version: {hash}";
  const versionLine = tx(versionTemplate, hashNode, {
    hash: COMMIT_HASH,
    date: versionDate,
  });

  return (
    <section className="options-page" role="region" aria-label={t("Options")}>
      <h1 className="options-title">{t("Options")}</h1>
      {/* Engine / connectivity / build version — one row when there's room,
          wrapping to stacked lines on a narrow screen. */}
      <div className="options-status">
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
        <p className="app-version">{versionLine}</p>
      </div>
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
              interactiveReason ||
              t(
                "Interactive (pan/zoom) maps; each day's area is prefetched for offline use, and falls back to the static image if it can't load",
              )
            }
          >
            <label className={`opt-check ${interactiveReason ? "disabled" : ""}`}>
              <input
                type="checkbox"
                checked={interactiveMaps}
                disabled={!!interactiveReason}
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
              {redrawing ? t("Redrawing…") : t("Redraw all maps")}
            </button>
          </Tip>
        </div>
        <CacheList
          days={days}
          docKey={docKey}
          entries={cacheEntries}
          error={cacheError}
          storage={storage}
          onRedrawDay={onRedrawDay}
          redrawingDay={redrawingDay}
          onClearOthers={onClearOthers}
          disabledReason={
            mapsReason || engineReason || (redrawing ? t("A redraw is already running") : "")
          }
          lang={lang}
        />
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
        <div className="opt-row">
          <Tip
            text={t(
              "Fetch a weather forecast (from Open-Meteo) for each located activity in the next 7 days, shown as a small chip on its title; needs a connection",
            )}
          >
            <label className="opt-check">
              <input
                type="checkbox"
                checked={showForecast}
                onChange={(e) => setShowForecast(e.target.checked)}
              />
              {t("Show weather forecast")}
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
          {/* Address inference and its country scope are trip data, not print
              options: they live in the file's `defaults` (Edit → Defaults), so
              the exported PDF matches what the file says. */}
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
