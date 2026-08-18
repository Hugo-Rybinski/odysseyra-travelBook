import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  boot,
  buildPdf,
  geocode,
  renderDayMap,
  resolve,
  validate,
  type BootProgress,
} from "./pyodide/runtime";
import {
  canWriteHandle,
  hasSavePicker,
  loadLastHandle,
  openFile,
  rememberHandle,
  reopenHandle,
  saveAsJson,
  writeHandle,
  type OpenedFile,
} from "./file/openFile";
import { downloadBytes, downloadText, slugify } from "./file/saveExport";
import {
  docHash,
  getCachedDay,
  invalidateDoc,
  purgeExpired,
  putCachedDay,
} from "./maps/mapCache";
import { FindingsPanel } from "./findings/FindingsPanel";
import { Book } from "./render/Book";
import { Options } from "./Options";
import { EditPanel } from "./edit/EditPanel";
import { jsonToDraft, serializeForSave, serializeWithPaths } from "./edit/serialize";
import { buildFindingIndex, collectFieldPaths } from "./edit/findings";
import { useDraftHistory } from "./edit/useDraftHistory";
import {
  clearAutosave,
  loadAutosave,
  saveAutosave,
  type AutosaveRecord,
} from "./edit/autosave";
import { PwaStatus } from "./pwa/PwaStatus";
import { usePwa } from "./pwa/PwaProvider";
import type { Day, Finding, Itinerary } from "./types/resolved";
import type { SrcItinerary } from "./types/source";

const SAMPLE = `${import.meta.env.BASE_URL}samples/pyrenees.json`;

const STAGE_LABEL: Record<BootProgress["stage"], string> = {
  idle: "Starting…",
  "loading-runtime": "Loading Python runtime…",
  "installing-packages": "Installing packages…",
  "installing-travelbook": "Installing travelbook…",
  ready: "Ready",
  error: "Engine failed to start",
};

type Lang = "en" | "fr";
type View = "options" | "viewer" | "findings" | "edit";

// A loaded source: its name, raw text, and (if opened via the FS Access API) a
// handle we can re-read later. `handle` shape is opaque here.
type Source = OpenedFile;

export function App() {
  const [progress, setProgress] = useState<BootProgress>({ stage: "idle" });
  const [lang, setLang] = useState<Lang>("en");
  const [source, setSource] = useState<Source | null>(null);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  // The editable input-JSON draft (Edit tab), with an undo/redo stack (P6).
  // Seeded from the opened file, pushed into the viewer/findings/export via the
  // Apply button (P3), and written to a file via Save (P4).
  const { draft, set: setDraftHist, reset: resetDraft, undo, redo, canUndo, canRedo } =
    useDraftHistory<SrcItinerary>(null);
  const [applying, setApplying] = useState(false);
  const [saving, setSaving] = useState(false);
  // The serialized text backing the current preview (set on Apply/load) and the
  // last-saved/loaded text (set on Save/load). `dirty` (unapplied) and `unsaved`
  // are derived from these by comparison, so undo/redo/revert stay correct.
  const [appliedText, setAppliedText] = useState<string | null>(null);
  const [savedText, setSavedText] = useState<string | null>(null);
  // Online/offline, for gating geocoding (Nominatim needs the network).
  const [online, setOnline] = useState(() =>
    typeof navigator === "undefined" ? true : navigator.onLine,
  );
  // After a plain Apply we carry the previously-rendered day maps over rather
  // than refetching (editing changes the doc hash → every day misses the cache);
  // this suppresses the per-day map loaders for days without one, so "Apply"
  // shows a text-only preview and maps only rebuild via "Apply & redraw maps".
  const [mapsStale, setMapsStale] = useState(false);
  // Live validation of the draft (P2): findings anchored to fields by path, plus
  // a "rail" of the rest. Recomputed, debounced, whenever the draft changes.
  const [editIndex, setEditIndex] = useState<Map<string, Finding[]>>(new Map());
  const [editRail, setEditRail] = useState<Finding[]>([]);
  const [editValidating, setEditValidating] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [canReopen, setCanReopen] = useState(false);
  const [inkSaver, setInkSaver] = useState(false);
  const [mapsExport, setMapsExport] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [redrawing, setRedrawing] = useState(false);
  const [interactiveMaps, setInteractiveMaps] = useState(true);
  // Which top-level view is showing. Starts on "options" (so a first-run user
  // can reach "Open JSON…") and switches to "viewer" once a file is loaded.
  const [view, setView] = useState<View>("options");
  // A restorable autosaved draft found at startup (P6), offered on the empty
  // state until the user restores or discards it.
  const [restorable, setRestorable] = useState<AutosaveRecord | null>(null);

  // Serialize the draft once per change; both the live validation and the
  // dirty/unsaved comparisons read it.
  const draftSer = useMemo(() => (draft ? serializeWithPaths(draft) : null), [draft]);
  const dirty = !!draftSer && draftSer.text !== appliedText; // edits not yet applied to the preview
  const unsaved = !!draftSer && draftSer.text !== savedText; // edits not yet written to a file

  const engineReady = progress.stage === "ready";
  const { checkForUpdate, checking, updating, canInstall, install } = usePwa();
  // Bumped on every new analysis so a superseded per-day map loop bails out.
  const mapRunRef = useRef(0);

  // Render the per-day maps progressively, after the book is already on screen.
  // Each day is hydrated instantly from the 30-day IndexedDB cache when present;
  // otherwise we yield (so the browser paints the book + pending loaders), fetch
  // that day's map (a blocking tile fetch), swap it in and cache it. `force`
  // skips the cache read (used by "Redraw maps"). A newer file/redraw bumps the
  // token, so a stale loop stops merging into the current view.
  const buildDayMaps = useCallback(
    async (text: string, dayCount: number, force = false) => {
      const token = ++mapRunRef.current;
      const hash = await docHash(text);
      if (mapRunRef.current !== token) return;

      const swapIn = (i: number, day: Day) =>
        setItinerary((prev) => {
          if (!prev) return prev;
          const days = prev.days.slice();
          days[i] = day;
          return { ...prev, days };
        });

      for (let i = 0; i < dayCount; i++) {
        if (!force) {
          const cached = await getCachedDay(hash, i);
          if (mapRunRef.current !== token) return;
          if (cached) {
            swapIn(i, cached);
            continue;
          }
        }
        await new Promise((r) => setTimeout(r, 0));
        if (mapRunRef.current !== token) return;
        try {
          const day = await renderDayMap(text, i);
          if (mapRunRef.current !== token) return;
          swapIn(i, day);
          await putCachedDay(hash, i, day);
        } catch {
          // leave that day mapless and carry on with the rest
        }
      }
    },
    [],
  );

  // Warm the engine on mount, and see whether a previous file can be reopened.
  useEffect(() => {
    boot(setProgress).catch((e) => setError(String(e)));
    loadLastHandle().then((h) => setCanReopen(!!h));
    loadAutosave().then(setRestorable); // offer to restore unsaved edits (P6)
    void purgeExpired(); // drop map images older than 30 days
  }, []);

  // Reflect the chosen language on <html lang> for assistive tech.
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // Track connectivity (gates the Edit tab's geocode-from-address action).
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  // Default the PDF's map toggle to whatever the opened file asks for.
  useEffect(() => {
    if (itinerary) setMapsExport(itinerary.maps.include_in_render);
  }, [itinerary]);

  // Live-validate the draft (debounced): serialize with a line→path map, run the
  // validator over that exact text, then split findings into field-anchored
  // (by path) and rail. Skips until the engine is ready; a validate failure
  // surfaces as an error banner in the Edit tab rather than breaking it.
  useEffect(() => {
    if (!draft || !draftSer || !engineReady) return;
    let cancelled = false;
    setEditValidating(true);
    const timer = setTimeout(async () => {
      try {
        const found = await validate(draftSer.text, lang);
        if (cancelled) return;
        const { byPath, rail } = buildFindingIndex(found, draftSer.pathByLine, collectFieldPaths(draft));
        setEditIndex(byPath);
        setEditRail(rail);
        setEditError(null);
      } catch (e) {
        if (!cancelled) setEditError(String(e));
      } finally {
        if (!cancelled) setEditValidating(false);
      }
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [draft, draftSer, lang, engineReady]);

  // Autosave the draft to IndexedDB while it has unsaved edits (P6); clear it
  // once saved. Guarded on a draft existing so it never wipes a stashed record
  // before the startup restore prompt reads it.
  useEffect(() => {
    if (!draft || !draftSer) return;
    const timer = setTimeout(() => {
      if (unsaved) {
        void saveAutosave({ name: source?.name ?? "untitled.json", text: draftSer.text, at: Date.now() });
      } else {
        void clearAutosave();
      }
    }, 800);
    return () => clearTimeout(timer);
  }, [draft, draftSer, unsaved, source]);

  // Resolve + validate a freshly opened source.
  const analyze = useCallback(
    async (src: Source) => {
      setBusy(true);
      setError(null);
      try {
        await boot(setProgress);
        const [model, found] = await Promise.all([
          resolve(src.text),
          validate(src.text, lang),
        ]);
        setSource(src);
        setItinerary(model);
        setFindings(found);
        try {
          const seed = jsonToDraft(src.text); // seed the Edit tab with the raw input JSON
          resetDraft(seed);
          const seedText = serializeWithPaths(seed).text;
          setAppliedText(seedText); // the viewer shows this content (dirty = false)
          setSavedText(seedText); // it matches the file on disk (unsaved = false)
        } catch {
          resetDraft(null); // unparseable-but-resolvable shouldn't happen, but don't break the load
          setAppliedText(null);
          setSavedText(null);
        }
        setMapsStale(false);
        setView("viewer"); // switch to the book once it's on screen
        // Text is on screen now; fetch the per-day maps in the background.
        if (model.maps.include_in_render) void buildDayMaps(src.text, model.days.length);
        else mapRunRef.current++; // cancel any in-flight loop from a prior file
        await rememberHandle(src.handle);
        setCanReopen(!!src.handle || canReopen);
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [lang, canReopen, buildDayMaps, resetDraft],
  );

  const onOpen = useCallback(async () => {
    try {
      const opened = await openFile();
      if (opened) await analyze(opened);
    } catch (e) {
      setError(String(e));
    }
  }, [analyze]);

  const onOpenSample = useCallback(async () => {
    try {
      const text = await (await fetch(SAMPLE)).text();
      await analyze({ name: "pyrenees.json", text, handle: null });
    } catch (e) {
      setError(String(e));
    }
  }, [analyze]);

  const onReopen = useCallback(async () => {
    try {
      const h = await loadLastHandle();
      if (!h) return setCanReopen(false);
      const opened = await reopenHandle(h);
      if (opened) await analyze(opened);
    } catch (e) {
      setError(String(e));
    }
  }, [analyze]);

  // Export the PDF and download it, without losing the view. Maps are embedded
  // when the toggle is on (fetching tiles/routes in-browser; slower).
  const onExport = useCallback(async () => {
    if (!source) return;
    setExporting(true);
    setError(null);
    try {
      const bytes = await buildPdf(source.text, { lang, inkSaver, maps: mapsExport });
      const base = itinerary?.title || source.name || "travelbook";
      downloadBytes(bytes, `${slugify(base)}.pdf`);
    } catch (e) {
      setError(String(e));
    } finally {
      setExporting(false);
    }
  }, [source, lang, inkSaver, mapsExport, itinerary]);

  // Redraw this file's maps: drop its cached images, clear them on screen (so
  // the per-day loaders reappear) and re-render every day, bypassing the cache.
  const onRedraw = useCallback(async () => {
    if (!source || !itinerary?.maps.include_in_render) return;
    setRedrawing(true);
    setError(null);
    try {
      const hash = await docHash(source.text);
      await invalidateDoc(hash);
      setMapsStale(false);
      setItinerary((prev) =>
        prev ? { ...prev, days: prev.days.map((d) => ({ ...d, map: undefined })) } : prev,
      );
      await buildDayMaps(source.text, itinerary.days.length, true);
    } catch (e) {
      setError(String(e));
    } finally {
      setRedrawing(false);
    }
  }, [source, itinerary, buildDayMaps]);

  // A sensible filename for saving/downloading the draft.
  const draftFilename = useCallback(
    () => `${slugify(draft?.travel_description?.title || source?.name || "travelbook")}.json`,
    [draft, source],
  );

  // Save the draft (P4/P6): normalize (prune empties + safe defaults) and either
  // overwrite the opened file in place when we hold a writable handle, or fall
  // back to a download. `savedText` tracks the *unpruned* serialization so the
  // unsaved indicator compares like-for-like against the live draft.
  const onSave = useCallback(async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      const handle = source?.handle ?? null;
      if (canWriteHandle(handle)) await writeHandle(handle, serializeForSave(draft));
      else downloadText(serializeForSave(draft), draftFilename());
      setSavedText(serializeWithPaths(draft).text);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }, [draft, source, draftFilename]);

  // Save the draft to a new file (Chromium's Save-as picker); the new file
  // becomes the backing source so later in-place saves and "Reopen last" use it.
  const onSaveAs = useCallback(async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      const opened = await saveAsJson(draftFilename(), serializeForSave(draft));
      if (opened) {
        setSource(opened);
        await rememberHandle(opened.handle);
        setCanReopen((prev) => !!opened.handle || prev);
        setSavedText(serializeWithPaths(draft).text);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }, [draft, draftFilename]);

  // Download the draft as a .json file (always available; the only route where
  // the FS Access API is absent, e.g. iOS Safari).
  const onDownloadJson = useCallback(() => {
    if (!draft) return;
    setError(null);
    downloadText(serializeForSave(draft), draftFilename());
    setSavedText(serializeWithPaths(draft).text);
  }, [draft, draftFilename]);

  // Revert the draft to the last saved/loaded baseline (P6). Recorded on the
  // undo stack, so a revert can itself be undone.
  const onRevert = useCallback(() => {
    if (savedText === null) return;
    try {
      setDraftHist(jsonToDraft(savedText));
    } catch (e) {
      setError(String(e));
    }
  }, [savedText, setDraftHist]);

  // Restore the autosaved draft from a previous session (P6): load it as if
  // opening a handle-less file, then jump to the Edit tab.
  const onRestore = useCallback(async () => {
    if (!restorable) return;
    const rec = restorable;
    setRestorable(null);
    await analyze({ name: rec.name, text: rec.text, handle: null });
    setView("edit");
  }, [restorable, analyze]);

  const onDiscardRestore = useCallback(() => {
    setRestorable(null);
    void clearAutosave();
  }, []);

  // Geocode a coordinate field's address (P5), narrowed to the trip's
  // inference_countries. Reuses the maps geocode seam through the bridge.
  const onGeocode = useCallback(
    (query: string) => geocode(query, draft?.defaults?.inference_countries ?? []),
    [draft],
  );

  // Apply the draft to the rendered viewer + findings + export source (P3). The
  // preview refreshes only here, never live-on-keystroke. `redrawMaps` also
  // rebuilds the per-day maps for the edited document; a plain apply carries the
  // previously-rendered maps over untouched (see `mapsStale`).
  const onApply = useCallback(
    async (redrawMaps: boolean) => {
      if (!draft) return;
      setApplying(true);
      setError(null);
      try {
        const { text } = serializeWithPaths(draft);
        const [model, found] = await Promise.all([resolve(text), validate(text, lang)]);
        const carried = itinerary
          ? { ...model, days: model.days.map((d, i) => ({ ...d, map: itinerary.days[i]?.map })) }
          : model;
        setItinerary(redrawMaps ? model : carried);
        setFindings(found);
        setSource((prev) => (prev ? { ...prev, text } : { name: "edited.json", text, handle: null }));
        setAppliedText(text); // preview now reflects the draft (dirty = false)
        if (model.maps.include_in_render && redrawMaps) {
          setMapsStale(false);
          await buildDayMaps(text, model.days.length, true);
        } else {
          // Plain apply (or maps off): don't refetch. Carried maps stay on
          // screen; suppress loaders for any day without one.
          setMapsStale(model.maps.include_in_render);
          mapRunRef.current++; // cancel any in-flight map loop from a prior state
        }
      } catch (e) {
        setError(String(e));
      } finally {
        setApplying(false);
      }
    },
    [draft, lang, itinerary, buildDayMaps],
  );

  // Re-validate (in the chosen language) when the language changes.
  const onToggleLang = useCallback(
    async (next: Lang) => {
      setLang(next);
      if (!source) return;
      try {
        setFindings(await validate(source.text, next));
      } catch (e) {
        setError(String(e));
      }
    },
    [source],
  );

  return (
    <main className="shell">
      <PwaStatus />
      <header className="topbar" style={{ background: itinerary?.cover_color }}>
        <h1>Travelbook Viewer</h1>
        <div className="actions" role="tablist" aria-label="View">
          <button
            className={`btn ghost ${view === "options" ? "active" : ""}`}
            onClick={() => setView("options")}
            role="tab"
            aria-selected={view === "options"}
          >
            ⚙️ Options
          </button>
          <button
            className={`btn ghost ${view === "viewer" ? "active" : ""}`}
            onClick={() => setView("viewer")}
            role="tab"
            aria-selected={view === "viewer"}
          >
            📖 Travel viewer
          </button>
          <button
            className={`btn ghost ${view === "findings" ? "active" : ""}`}
            onClick={() => itinerary && setView("findings")}
            role="tab"
            aria-selected={view === "findings"}
            aria-disabled={!itinerary}
            data-tip={itinerary ? undefined : "Open an itinerary first"}
          >
            🔎 Findings
          </button>
          <button
            className={`btn ghost ${view === "edit" ? "active" : ""}`}
            onClick={() => draft && setView("edit")}
            role="tab"
            aria-selected={view === "edit"}
            aria-disabled={!draft}
            data-tip={draft ? undefined : "Open an itinerary first"}
          >
            ✏️ Edit
            {dirty && (
              <span className="dirty-dot" aria-label="unapplied edits" title="Unapplied edits">
                {" "}
                ●
              </span>
            )}
          </button>
        </div>
      </header>

      <p className={`engine ${engineReady ? "ok" : ""}`}>
        {engineReady ? "● Engine ready" : `◌ ${STAGE_LABEL[progress.stage]}`}
        {busy && " · working…"}
      </p>

      {error && <p className="banner error">⚠️ {error}</p>}

      {view === "options" ? (
        <Options
          onOpen={onOpen}
          onReopen={onReopen}
          onOpenSample={onOpenSample}
          canReopen={canReopen}
          busy={busy}
          lang={lang}
          onToggleLang={onToggleLang}
          hasItinerary={!!itinerary}
          mapsInRender={!!itinerary?.maps.include_in_render}
          engineReady={engineReady}
          interactiveMaps={interactiveMaps}
          setInteractiveMaps={setInteractiveMaps}
          onRedraw={onRedraw}
          redrawing={redrawing}
          inkSaver={inkSaver}
          setInkSaver={setInkSaver}
          mapsExport={mapsExport}
          setMapsExport={setMapsExport}
          onExport={onExport}
          exporting={exporting}
          checkForUpdate={checkForUpdate}
          checking={checking}
          updating={updating}
          canInstall={canInstall}
          install={install}
        />
      ) : view === "findings" && itinerary ? (
        <FindingsPanel findings={findings} />
      ) : view === "edit" && draft ? (
        <EditPanel
          draft={draft}
          onChange={setDraftHist}
          findingIndex={editIndex}
          rail={editRail}
          validating={editValidating}
          validationError={editError}
          dirty={dirty}
          applying={applying}
          engineReady={engineReady}
          mapsInRender={!!draft.defaults?.include_maps_in_render}
          onApply={() => onApply(false)}
          onApplyRedraw={() => onApply(true)}
          unsaved={unsaved}
          saving={saving}
          canSaveInPlace={canWriteHandle(source?.handle)}
          hasSavePicker={hasSavePicker()}
          onSave={onSave}
          onSaveAs={onSaveAs}
          onDownloadJson={onDownloadJson}
          canUndo={canUndo}
          canRedo={canRedo}
          onUndo={undo}
          onRedo={redo}
          onRevert={onRevert}
          geocode={{ geocode: onGeocode, ready: engineReady && online }}
        />
      ) : itinerary ? (
        <section className="report">
          <p className="report-caption">
            {source?.name && <span className="filename">{source.name}</span>}
          </p>
          <Book
            itinerary={itinerary}
            lang={lang}
            interactiveMaps={interactiveMaps}
            showMapLoaders={!mapsStale}
          />
        </section>
      ) : (
        !error && (
          <section className="empty-state">
            <div className="book-mark" aria-hidden>
              📖
            </div>
            <h2>Open an itinerary</h2>
            <p>
              Choose a travelbook JSON file in <strong>⚙️ Options</strong> to render the
              travel book and see its validation findings. Everything stays on your device.
            </p>
            {restorable && (
              <div className="restore-banner" role="status">
                <span>
                  Unsaved edits from a previous session
                  {restorable.name ? ` (${restorable.name})` : ""} were found.
                </span>
                <span className="restore-actions">
                  <button className="btn" onClick={onRestore}>
                    Restore
                  </button>
                  <button className="btn subtle" onClick={onDiscardRestore}>
                    Discard
                  </button>
                </span>
              </div>
            )}
            {!engineReady && <small>The engine is still warming up…</small>}
          </section>
        )
      )}
    </main>
  );
}
