import { useCallback, useEffect, useState } from "react";
import { boot, resolve, validate, type BootProgress } from "./pyodide/runtime";
import {
  loadLastHandle,
  openFile,
  rememberHandle,
  reopenHandle,
  type OpenedFile,
} from "./file/openFile";
import { FindingsPanel } from "./findings/FindingsPanel";
import { Book } from "./render/Book";
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

  const engineReady = progress.stage === "ready";

  // Warm the engine on mount, and see whether a previous file can be reopened.
  useEffect(() => {
    boot(setProgress).catch((e) => setError(String(e)));
    loadLastHandle().then((h) => setCanReopen(!!h));
  }, []);

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
        await rememberHandle(src.handle);
        setCanReopen(!!src.handle || canReopen);
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [lang, canReopen],
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
          {source?.name && <p className="filename">{source.name}</p>}
          <Book itinerary={itinerary} lang={lang} />
          <FindingsPanel findings={findings} />
        </section>
      )}
    </main>
  );
}
