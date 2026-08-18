import { useCallback, useEffect, useRef, useState } from "react";
import {
  boot,
  buildPdf,
  renderDayMap,
  resolve,
  validate,
  type BootProgress,
} from "./pyodide/runtime";
import {
  loadLastHandle,
  openFile,
  rememberHandle,
  reopenHandle,
  type OpenedFile,
} from "./file/openFile";
import { downloadBytes, slugify } from "./file/saveExport";
import { FindingsPanel } from "./findings/FindingsPanel";
import { Book } from "./render/Book";
import { PwaStatus } from "./pwa/PwaStatus";
import type { Finding, Itinerary } from "./types/resolved";

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

// A loaded source: its name, raw text, and (if opened via the FS Access API) a
// handle we can re-read later. `handle` shape is opaque here.
type Source = OpenedFile;

export function App() {
  const [progress, setProgress] = useState<BootProgress>({ stage: "idle" });
  const [lang, setLang] = useState<Lang>("en");
  const [source, setSource] = useState<Source | null>(null);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [canReopen, setCanReopen] = useState(false);
  const [inkSaver, setInkSaver] = useState(false);
  const [mapsExport, setMapsExport] = useState(false);
  const [exporting, setExporting] = useState(false);

  const engineReady = progress.stage === "ready";
  // Bumped on every new analysis so a superseded per-day map loop bails out.
  const mapRunRef = useRef(0);

  // Render the per-day maps progressively, after the book is already on screen:
  // yield to let the browser paint (the book + the pending days' loaders), then
  // fetch one day's map (a blocking tile fetch) and swap it in. A newer file
  // opening bumps the token, so a stale loop stops merging into the new view.
  const buildDayMaps = useCallback(async (text: string, dayCount: number) => {
    const token = ++mapRunRef.current;
    for (let i = 0; i < dayCount; i++) {
      await new Promise((r) => setTimeout(r, 0));
      if (mapRunRef.current !== token) return;
      try {
        const day = await renderDayMap(text, i);
        if (mapRunRef.current !== token) return;
        setItinerary((prev) => {
          if (!prev) return prev;
          const days = prev.days.slice();
          days[i] = day;
          return { ...prev, days };
        });
      } catch {
        // leave that day mapless and carry on with the rest
      }
    }
  }, []);

  // Warm the engine on mount, and see whether a previous file can be reopened.
  useEffect(() => {
    boot(setProgress).catch((e) => setError(String(e)));
    loadLastHandle().then((h) => setCanReopen(!!h));
  }, []);

  // Reflect the chosen language on <html lang> for assistive tech.
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // Default the PDF's map toggle to whatever the opened file asks for.
  useEffect(() => {
    if (itinerary) setMapsExport(itinerary.maps.include_in_render);
  }, [itinerary]);

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
    [lang, canReopen, buildDayMaps],
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
        <div className="actions">
          <button className="btn" onClick={onOpen} disabled={busy}>
            Open JSON…
          </button>
          {canReopen && (
            <button className="btn ghost" onClick={onReopen} disabled={busy}>
              Reopen last
            </button>
          )}
          <button className="btn ghost" onClick={onOpenSample} disabled={busy}>
            Sample
          </button>
          <div className="lang" role="group" aria-label="Language">
            {(["en", "fr"] as Lang[]).map((l) => (
              <button
                key={l}
                className={`lang-btn ${lang === l ? "active" : ""}`}
                onClick={() => onToggleLang(l)}
                aria-pressed={lang === l}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
          {itinerary && (
            <>
              <label
                className="ink"
                title="Outlines instead of solid accent fills — less colored ink when printing"
              >
                <input
                  type="checkbox"
                  checked={inkSaver}
                  onChange={(e) => setInkSaver(e.target.checked)}
                />
                Ink-saver
              </label>
              <label
                className="ink"
                title="Embed the per-day maps in the exported PDF (fetches map tiles; slower)"
              >
                <input
                  type="checkbox"
                  checked={mapsExport}
                  onChange={(e) => setMapsExport(e.target.checked)}
                />
                Maps
              </label>
              <button
                className="btn"
                onClick={onExport}
                disabled={exporting || !engineReady}
                title={mapsExport ? "Maps are embedded in the PDF" : "Maps are omitted from the PDF"}
              >
                {exporting ? "Exporting…" : "Export PDF"}
              </button>
            </>
          )}
        </div>
      </header>

      <p className={`engine ${engineReady ? "ok" : ""}`}>
        {engineReady ? "● Engine ready" : `◌ ${STAGE_LABEL[progress.stage]}`}
        {busy && " · working…"}
      </p>

      {error && <p className="banner error">⚠️ {error}</p>}

      {!itinerary && !error && (
        <section className="empty-state">
          <div className="book-mark" aria-hidden>
            📖
          </div>
          <h2>Open an itinerary</h2>
          <p>
            Choose a travelbook JSON file to render the travel book and see its
            validation findings. Everything stays on your device.
          </p>
          {!engineReady && <small>The engine is still warming up…</small>}
        </section>
      )}

      {itinerary && (
        <section className="report">
          <p className="report-caption">
            {source?.name && <span className="filename">{source.name}</span>}
          </p>
          <Book itinerary={itinerary} lang={lang} />
          <FindingsPanel findings={findings} />
        </section>
      )}
    </main>
  );
}
