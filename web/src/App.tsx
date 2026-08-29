import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  boot,
  buildIcs,
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
import { Book, type DayView } from "./render/Book";
import { MapProviderContext, type MapProvider } from "./render/nav";
import { Options } from "./Options";
import { PromptsPanel } from "./prompts/PromptsPanel";
import { GuidePanel } from "./prompts/GuidePanel";
import { EditPanel } from "./edit/EditPanel";
import { jsonToDraft, serializeForSave, serializeWithPaths } from "./edit/serialize";
import {
  buildFindingIndex,
  collectContainerPaths,
  collectFieldPaths,
  EMPTY_FINDING_INDEX,
  type FindingIndex,
} from "./edit/findings";
import { useDraftHistory } from "./edit/useDraftHistory";
import {
  clearAutosave,
  loadAutosave,
  saveAutosave,
  type AutosaveRecord,
} from "./edit/autosave";
import { PwaStatus } from "./pwa/PwaStatus";
import { usePwa } from "./pwa/PwaProvider";
import { I18nProvider, translate } from "./i18n";
import type { Day, Finding, Itinerary } from "./types/resolved";
import type { SrcItinerary } from "./types/source";

const SAMPLE = `${import.meta.env.BASE_URL}samples/france.json`;

// A minimal, valid starting point for "Create new blank itinerary": a titled
// trip with one placeholder day, so the viewer renders something the moment it
// opens (rather than a blank page). It lands in the Edit tab for the user to
// replace the placeholders and build the trip from scratch.
const BLANK_ITINERARY = JSON.stringify(
  {
    travel_description: { title: "My trip" },
    days: [
      {
        title: "Your first day",
        description: "Your first day description",
        activities: [
          { type: "place", name: "Your first place", description: "Your first place description" },
        ],
      },
    ],
  },
  null,
  2,
);

const STAGE_LABEL: Record<BootProgress["stage"], string> = {
  idle: "Starting…",
  "loading-runtime": "Loading Python runtime…",
  "installing-packages": "Installing packages…",
  "installing-odysseyra": "Installing Odysseyra TravelBook…",
  ready: "Ready",
  error: "Engine failed to start",
};

type Lang = "en" | "fr";
type View =
  | "options"
  | "viewer"
  | "transport"
  | "accommodations"
  | "findings"
  | "edit"
  | "guide"
  | "prompts";

// A loaded source: its name, raw text, and (if opened via the FS Access API) a
// handle we can re-read later. `handle` shape is opaque here.
type Source = OpenedFile;

export function App() {
  const [progress, setProgress] = useState<BootProgress>({ stage: "idle" });
  const [lang, setLang] = useState<Lang>("en");
  const [source, setSource] = useState<Source | null>(null);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  // Why the itinerary couldn't be rendered (e.g. missing title) while the file
  // is still open for editing/investigation; shown in the Travel viewer.
  const [renderError, setRenderError] = useState<string | null>(null);
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
  const [editIndex, setEditIndex] = useState<FindingIndex>(EMPTY_FINDING_INDEX);
  const [editRail, setEditRail] = useState<Finding[]>([]);
  const [editValidating, setEditValidating] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [canReopen, setCanReopen] = useState(false);
  const [inkSaver, setInkSaver] = useState(false);
  const [mapsExport, setMapsExport] = useState(false);
  const [inferCoords, setInferCoords] = useState(false);
  const [mapCountry, setMapCountry] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportingIcs, setExportingIcs] = useState(false);
  const [redrawing, setRedrawing] = useState(false);
  const [interactiveMaps, setInteractiveMaps] = useState(true);
  // Truncate long descriptions to a few lines (with a "Show more" toggle) in the
  // viewer; off shows them in full. Default on.
  const [clampDescriptions, setClampDescriptions] = useState(true);
  // Which days / transport cards / accommodation cards start open (see DayView).
  // Default: past ones collapsed.
  const [daysView, setDaysView] = useState<DayView>("collapse-past");
  const [transportView, setTransportView] = useState<DayView>("collapse-past");
  const [accommodationView, setAccommodationView] = useState<DayView>("collapse-past");
  // Which mapping app the viewer's "Navigate" links open. Default Google Maps.
  const [mapProvider, setMapProvider] = useState<MapProvider>("google");
  // Which top-level view is showing. Starts on "viewer": with no file open its
  // empty state carries the File box (Open JSON… / Reopen / Sample) inline, so a
  // first-run user can open a file without visiting Options.
  const [view, setView] = useState<View>("viewer");
  // A prompt card the LLM-prompts tab should scroll to on open (set when a
  // Usage-guide "Open this prompt" link is followed). Cleared once handled.
  const [promptAnchor, setPromptAnchor] = useState<string | null>(null);
  // The top-bar burger menu (holds the view switcher).
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  // A restorable autosaved draft found at startup (P6), offered on the empty
  // state until the user restores or discards it.
  const [restorable, setRestorable] = useState<AutosaveRecord | null>(null);

  // Close the burger menu on an outside click or Escape.
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  // Serialize the draft once per change; both the live validation and the
  // dirty/unsaved comparisons read it.
  const draftSer = useMemo(() => (draft ? serializeWithPaths(draft) : null), [draft]);
  const dirty = !!draftSer && draftSer.text !== appliedText; // edits not yet applied to the preview
  const unsaved = !!draftSer && draftSer.text !== savedText; // edits not yet written to a file

  const engineReady = progress.stage === "ready";

  // App renders the i18n provider, so it sits *above* that context and can't use
  // useT()/useTx(); it translates directly against its own `lang` state instead.
  const t = useCallback(
    (text: string, vars?: Record<string, string | number>) => translate(lang, text, vars),
    [lang],
  );
  const tx = useCallback(
    (text: string, nodes: Record<string, ReactNode>) =>
      translate(lang, text)
        .split(/(\{\w+\})/g)
        .map((part, i) => {
          const m = /^\{(\w+)\}$/.exec(part);
          return <Fragment key={i}>{m && m[1] in nodes ? nodes[m[1]] : part}</Fragment>;
        }),
    [lang],
  );

  const { checkForUpdate, checking, updating, canInstall, install, isIOS, isStandalone, offlineReady } =
    usePwa();
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

  // Default the PDF's map toggles to whatever the opened file asks for.
  useEffect(() => {
    if (itinerary) {
      setMapsExport(itinerary.maps.include_in_render);
      setInferCoords(itinerary.maps.infer_from_address);
      setMapCountry(itinerary.maps.inference_countries.join(", "));
    }
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
        const { byPath, rail, shared } = buildFindingIndex(
          found,
          draftSer.pathByLine,
          collectFieldPaths(draft),
          collectContainerPaths(draft),
        );
        setEditIndex({ byPath, shared });
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

  // Resolve + validate a freshly opened source. Resilient to a model that won't
  // build (e.g. missing title): we still load the draft + findings so the file
  // can be edited/investigated, and the Travel viewer explains why it can't render.
  const analyze = useCallback(
    async (src: Source) => {
      setBusy(true);
      setError(null);
      try {
        await boot(setProgress);
        // Findings first — validate parses independently and reports problems
        // even when the render model can't be built.
        let found: Finding[] = [];
        try {
          found = await validate(src.text, lang);
        } catch {
          /* a bridge/validate failure still shouldn't block opening */
        }
        // Try to build the render model; capture (don't throw) if it can't.
        let model: Itinerary | null = null;
        let renderErr: string | null = null;
        try {
          model = await resolve(src.text);
        } catch (e) {
          renderErr = String(e);
        }

        setSource(src);
        setItinerary(model);
        setRenderError(renderErr);
        setFindings(found);

        let seeded = false;
        try {
          const seed = jsonToDraft(src.text); // seed the Edit tab with the raw input JSON
          resetDraft(seed);
          const seedText = serializeWithPaths(seed).text;
          setAppliedText(seedText);
          setSavedText(seedText);
          seeded = true;
        } catch {
          resetDraft(null); // not even valid JSON — nothing to edit
          setAppliedText(null);
          setSavedText(null);
        }
        setMapsStale(false);

        // Land on the book when it renders; otherwise on Edit (to fix it) or
        // Findings (to see why) so the user isn't stuck on a blank viewer.
        setView(model ? "viewer" : seeded ? "edit" : "findings");

        if (model?.maps.include_in_render) void buildDayMaps(src.text, model.days.length);
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
      await analyze({ name: "france.json", text, handle: null });
    } catch (e) {
      setError(String(e));
    }
  }, [analyze]);

  // Start a brand-new itinerary from a blank scaffold, landing in the Edit tab.
  const onCreateBlank = useCallback(async () => {
    try {
      await analyze({ name: "new-itinerary.json", text: BLANK_ITINERARY, handle: null });
      setView("edit");
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
      const bytes = await buildPdf(source.text, {
        lang,
        inkSaver,
        maps: mapsExport,
        mapProvider,
        // The country scope / address-inference only bite when maps are on.
        mapCountry: mapsExport ? mapCountry : "",
        inferCoords: mapsExport ? inferCoords : undefined,
      });
      const base = itinerary?.title || source.name || "odysseyra";
      downloadBytes(bytes, `${slugify(base)}.pdf`);
    } catch (e) {
      setError(String(e));
    } finally {
      setExporting(false);
    }
  }, [source, lang, inkSaver, mapsExport, inferCoords, mapCountry, mapProvider, itinerary]);

  // Export an iCalendar (.ics) of the trip and download it. Pure transform (no
  // maps / no network), so it never touches the export map options.
  const onExportIcs = useCallback(async () => {
    if (!source) return;
    setExportingIcs(true);
    setError(null);
    try {
      const text = await buildIcs(source.text, lang);
      const base = itinerary?.title || source.name || "odysseyra";
      downloadText(text, `${slugify(base)}.ics`, "text/calendar");
    } catch (e) {
      setError(String(e));
    } finally {
      setExportingIcs(false);
    }
  }, [source, lang, itinerary]);

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
    () => `${slugify(draft?.travel_description?.title || source?.name || "odysseyra")}.json`,
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
        const found = await validate(text, lang);
        // Build the model, but don't let a still-invalid draft throw away the
        // apply — findings/export update and the viewer explains it can't render.
        let model: Itinerary | null = null;
        let renderErr: string | null = null;
        try {
          model = await resolve(text);
        } catch (e) {
          renderErr = String(e);
        }
        const carried =
          model && itinerary
            ? { ...model, days: model.days.map((d, i) => ({ ...d, map: itinerary.days[i]?.map })) }
            : model;
        setItinerary(redrawMaps ? model : carried);
        setRenderError(renderErr);
        setFindings(found);
        setSource((prev) => (prev ? { ...prev, text } : { name: "edited.json", text, handle: null }));
        setAppliedText(text); // preview now reflects the draft (dirty = false)
        if (model?.maps.include_in_render && redrawMaps) {
          setMapsStale(false);
          await buildDayMaps(text, model.days.length, true);
        } else {
          // Plain apply (or maps off / unrenderable): don't refetch. Carried maps
          // stay on screen; suppress loaders for any day without one.
          setMapsStale(!!model?.maps.include_in_render);
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

  // Follow a Usage-guide "Open this prompt" link: switch to the LLM-prompts tab
  // and remember which card to scroll to (PromptsPanel does the scrolling).
  const openPrompt = useCallback((file: string) => {
    setPromptAnchor(file);
    setView("prompts");
    setMenuOpen(false);
  }, []);

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
    <I18nProvider lang={lang}>
    <main className="shell">
      <PwaStatus />
      <header className="topbar">
        <button
          className="logo-btn"
          onClick={() => {
            setView("viewer");
            setMenuOpen(false);
          }}
          aria-label={t("🧭 Travel")}
        >
          <img
            className="logo"
            src={`${import.meta.env.BASE_URL}img/odysseyra-white-no-bg.svg`}
            alt=""
            aria-hidden="true"
          />
        </button>
        <h1>{t("Odysseyra TravelBook")}</h1>
        <div className="menu" ref={menuRef}>
          <button
            className="btn ghost burger"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-label={t("Menu")}
            onClick={() => setMenuOpen((o) => !o)}
          >
            ☰
            {dirty && (
              <span className="dirty-dot" aria-label={t("unapplied edits")} title={t("Unapplied edits")}>
                {" "}
                ●
              </span>
            )}
          </button>
          {menuOpen && (
            <div className="menu-list" role="menu" aria-label={t("View")}>
              {[
                { id: "viewer" as View, label: t("🧭 Travel"), disabled: false, dot: false, divider: false },
                { id: "transport" as View, label: t("✈️ Transports"), disabled: !itinerary, dot: false, divider: false },
                { id: "accommodations" as View, label: t("🏠 Accommodations"), disabled: !itinerary, dot: false, divider: true },
                { id: "findings" as View, label: t("🔎 Findings"), disabled: !source, dot: false, divider: false },
                { id: "edit" as View, label: t("✏️ Edit"), disabled: !draft, dot: dirty, divider: true },
                { id: "guide" as View, label: t("📘 Usage guide"), disabled: false, dot: false, divider: false },
                { id: "prompts" as View, label: t("🤖 LLM prompts"), disabled: false, dot: false, divider: false },
                { id: "options" as View, label: t("⚙️ Options"), disabled: false, dot: false, divider: false },
              ].map((item) => (
                <Fragment key={item.id}>
                  <button
                    className={`menu-item ${view === item.id ? "active" : ""}`}
                    role="menuitem"
                    aria-current={view === item.id}
                    disabled={item.disabled}
                    data-tip={item.disabled ? t("Open an itinerary first") : undefined}
                    onClick={() => {
                      setView(item.id);
                      setMenuOpen(false);
                    }}
                  >
                    {item.label}
                    {item.dot && (
                      <span
                        className="dirty-dot"
                        aria-label={t("unapplied edits")}
                        title={t("Unapplied edits")}
                      >
                        {" "}
                        ●
                      </span>
                    )}
                  </button>
                  {item.divider && <span className="menu-sep" role="separator" aria-hidden />}
                </Fragment>
              ))}
              <button
                className="menu-item"
                role="menuitem"
                disabled={checking || updating}
                onClick={() => {
                  checkForUpdate();
                  setMenuOpen(false);
                }}
              >
                {updating ? t("🔄 Updating…") : checking ? t("🔄 Checking…") : t("🔄 Update app")}
              </button>
            </div>
          )}
        </div>
      </header>

      {error && <p className="banner error">⚠️ {error}</p>}

      {view === "guide" ? (
        <GuidePanel onOpenPrompt={openPrompt} />
      ) : view === "prompts" ? (
        <PromptsPanel
          scrollTo={promptAnchor}
          onScrolled={() => setPromptAnchor(null)}
          onOpenGuide={() => setView("guide")}
        />
      ) : view === "options" ? (
        <Options
          onOpen={onOpen}
          onReopen={onReopen}
          onOpenSample={onOpenSample}
          onCreateBlank={onCreateBlank}
          canReopen={canReopen}
          busy={busy}
          lang={lang}
          onToggleLang={onToggleLang}
          hasItinerary={!!itinerary}
          mapsInRender={!!itinerary?.maps.include_in_render}
          engineReady={engineReady}
          engineStageLabel={t(STAGE_LABEL[progress.stage])}
          currentFile={source?.name}
          interactiveMaps={interactiveMaps}
          setInteractiveMaps={setInteractiveMaps}
          clampDescriptions={clampDescriptions}
          setClampDescriptions={setClampDescriptions}
          daysView={daysView}
          setDaysView={setDaysView}
          transportView={transportView}
          setTransportView={setTransportView}
          accommodationView={accommodationView}
          setAccommodationView={setAccommodationView}
          mapProvider={mapProvider}
          setMapProvider={setMapProvider}
          onRedraw={onRedraw}
          redrawing={redrawing}
          inkSaver={inkSaver}
          setInkSaver={setInkSaver}
          mapsExport={mapsExport}
          setMapsExport={setMapsExport}
          inferCoords={inferCoords}
          setInferCoords={setInferCoords}
          mapCountry={mapCountry}
          setMapCountry={setMapCountry}
          onExport={onExport}
          exporting={exporting}
          onExportIcs={onExportIcs}
          exportingIcs={exportingIcs}
          checkForUpdate={checkForUpdate}
          checking={checking}
          updating={updating}
          canInstall={canInstall}
          install={install}
          isIOS={isIOS}
          isStandalone={isStandalone}
          online={online}
          offlineReady={offlineReady}
        />
      ) : view === "findings" && source ? (
        <FindingsPanel findings={findings} />
      ) : view === "edit" && draft ? (
        <MapProviderContext.Provider value={mapProvider}>
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
        </MapProviderContext.Provider>
      ) : view === "transport" && itinerary ? (
        <section className="report">
          <Book
            itinerary={itinerary}
            lang={lang}
            show="transport"
            transportView={transportView}
            mapProvider={mapProvider}
          />
        </section>
      ) : view === "accommodations" && itinerary ? (
        <section className="report">
          <Book
            itinerary={itinerary}
            lang={lang}
            show="accommodations"
            accommodationView={accommodationView}
            mapProvider={mapProvider}
          />
        </section>
      ) : itinerary ? (
        <section className="report">
          <Book
            itinerary={itinerary}
            lang={lang}
            interactiveMaps={interactiveMaps}
            showMapLoaders={!mapsStale}
            clampDescriptions={clampDescriptions}
            daysView={daysView}
            mapProvider={mapProvider}
          />
        </section>
      ) : source ? (
        // A file is open but the model can't be built yet (e.g. missing title).
        <section className="empty-state">
          <div className="book-mark" aria-hidden>
            🚧
          </div>
          <h2>{t("Can't render this itinerary yet")}</h2>
          <p>
            {renderError ? renderError.replace(/^Error:\s*/, "") : t("The itinerary couldn't be built.")}
          </p>
          <p>
            {tx("Fix the errors in {findings} or {edit}, then {apply} to render it here.", {
              findings: <strong>{t("🔎 Findings")}</strong>,
              edit: <strong>{t("✏️ Edit")}</strong>,
              apply: <strong>{t("Apply changes")}</strong>,
            })}
          </p>
        </section>
      ) : (
        !error && (
          <section className="empty-state">
            <div className="book-mark" aria-hidden>
              📖
            </div>
            <h2>{t("Open an itinerary")}</h2>
            <p>
              {t(
                "Render your travel book and see its validation findings. Everything stays on your device.",
              )}
            </p>
            <div className="empty-actions">
              <p className="empty-actions-text">
                {t(
                  "Create a blank itinerary, open an existing JSON file, or just try the app with our demo — and if you're new, check the usage guide.",
                )}
              </p>
              <div className="empty-action-buttons">
                <button className="btn" onClick={onCreateBlank} disabled={busy}>
                  {t("➕ Create blank")}
                </button>
                <button className="btn" onClick={onOpen} disabled={busy}>
                  {t("📂 Open JSON…")}
                </button>
                <button
                  className="btn"
                  onClick={() => {
                    setView("guide");
                    setMenuOpen(false);
                  }}
                >
                  {t("📘 Usage guide")}
                </button>
                <button className="btn" onClick={onOpenSample} disabled={busy}>
                  {t("🚀 Demo")}
                </button>
              </div>
            </div>
            {restorable && (
              <div className="restore-banner" role="status">
                <span>
                  {t("Unsaved edits from a previous session{name} were found.", {
                    name: restorable.name ? ` (${restorable.name})` : "",
                  })}
                </span>
                <span className="restore-actions">
                  <button className="btn" onClick={onRestore}>
                    {t("Restore")}
                  </button>
                  <button className="btn subtle" onClick={onDiscardRestore}>
                    {t("Discard")}
                  </button>
                </span>
              </div>
            )}
            {!engineReady && <small>{t("The engine is still warming up…")}</small>}
          </section>
        )
      )}
    </main>
    </I18nProvider>
  );
}
