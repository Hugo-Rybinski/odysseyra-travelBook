import { useEffect, useMemo, useState } from "react";
import { boot, resolve, validate, type BootProgress } from "./pyodide/runtime";
import type { Finding, FindingLevel, Itinerary } from "./types/resolved";

// Phase 1 smoke: boot Pyodide, then validate + resolve a bundled sample and show
// that the whole toolchain works end-to-end (title, day count, date range, and
// the findings the validator reports). The real file-open flow and findings
// panel arrive in Phase 2; full rendering in Phase 3.
const SAMPLE = `${import.meta.env.BASE_URL}samples/pyrenees.json`;

const STAGE_LABEL: Record<BootProgress["stage"], string> = {
  idle: "Starting…",
  "loading-runtime": "Loading Python runtime (Pyodide)…",
  "installing-packages": "Installing packages…",
  "installing-travelbook": "Installing travelbook…",
  ready: "Ready",
  error: "Failed to start",
};

const LEVEL_ICON: Record<FindingLevel, string> = {
  error: "❌",
  warning: "⚠️",
  info: "ℹ️",
};

export function App() {
  const [progress, setProgress] = useState<BootProgress>({ stage: "idle" });
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await boot((p) => !cancelled && setProgress(p));
        const text = await (await fetch(SAMPLE)).text();
        const [model, found] = await Promise.all([resolve(text), validate(text)]);
        if (cancelled) return;
        setItinerary(model);
        setFindings(found);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const counts = useMemo(() => {
    const c: Record<FindingLevel, number> = { error: 0, warning: 0, info: 0 };
    for (const f of findings) c[f.level]++;
    return c;
  }, [findings]);

  const ready = progress.stage === "ready" && itinerary;

  return (
    <main className="shell">
      <header className="topbar" style={{ background: itinerary?.cover_color }}>
        <h1>Travelbook Viewer</h1>
        <span className="tag">Phase 1 · smoke</span>
      </header>

      {error && <p className="banner error">⚠️ {error}</p>}

      {!ready && !error && (
        <section className="boot">
          <div className="spinner" aria-hidden />
          <p>{STAGE_LABEL[progress.stage]}</p>
          {progress.detail && <small>{progress.detail}</small>}
        </section>
      )}

      {ready && itinerary && (
        <section className="report">
          <div className="cover-preview">
            <h2>{itinerary.title}</h2>
            {itinerary.subtitle && <p className="subtitle">{itinerary.subtitle}</p>}
            <p className="meta">
              {itinerary.date_range || "no dates"} · {itinerary.day_count} days ·{" "}
              {itinerary.default_currency}
            </p>
            {itinerary.summary && <p className="summary">{itinerary.summary}</p>}
          </div>

          <div className="findings">
            <h3>
              Findings — {LEVEL_ICON.error} {counts.error} · {LEVEL_ICON.warning}{" "}
              {counts.warning} · {LEVEL_ICON.info} {counts.info}
            </h3>
            <ul>
              {findings.map((f, i) => (
                <li key={i} className={f.level}>
                  <span className="icon">{LEVEL_ICON[f.level]}</span>
                  <span className="line">line {f.line ?? "?"}</span>
                  <span className="msg">{f.message}</span>
                </li>
              ))}
              {findings.length === 0 && <li className="info">No findings 🎉</li>}
            </ul>
          </div>
        </section>
      )}
    </main>
  );
}
