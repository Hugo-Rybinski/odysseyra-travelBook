import { useMemo, useState } from "react";
import type { Finding, FindingLevel } from "../types/resolved";

const LEVEL_ICON: Record<FindingLevel, string> = {
  error: "❌",
  warning: "⚠️",
  info: "ℹ️",
};

const LEVEL_ORDER: FindingLevel[] = ["error", "warning", "info"];

type Filter = "all" | FindingLevel;

export function FindingsPanel({
  findings,
  title = "Validation",
}: {
  findings: Finding[];
  title?: string;
}) {
  const [filter, setFilter] = useState<Filter>("all");

  const counts = useMemo(() => {
    const c: Record<FindingLevel, number> = { error: 0, warning: 0, info: 0 };
    for (const f of findings) c[f.level]++;
    return c;
  }, [findings]);

  // Errors first, then warnings, then info; a stable order within each level.
  const shown = useMemo(() => {
    const filtered =
      filter === "all" ? findings : findings.filter((f) => f.level === filter);
    return [...filtered].sort(
      (a, b) => LEVEL_ORDER.indexOf(a.level) - LEVEL_ORDER.indexOf(b.level),
    );
  }, [findings, filter]);

  const chips: { key: Filter; label: string }[] = [
    { key: "all", label: `All ${findings.length}` },
    { key: "error", label: `${LEVEL_ICON.error} ${counts.error}` },
    { key: "warning", label: `${LEVEL_ICON.warning} ${counts.warning}` },
    { key: "info", label: `${LEVEL_ICON.info} ${counts.info}` },
  ];

  return (
    <section className="findings" aria-label="Validation findings">
      <div className="findings-head">
        <h3>{title}</h3>
        <div className="chips" role="tablist">
          {chips.map((c) => (
            <button
              key={c.key}
              role="tab"
              aria-selected={filter === c.key}
              className={`chip ${filter === c.key ? "active" : ""} ${c.key}`}
              onClick={() => setFilter(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <ul>
        {shown.map((f, i) => (
          <li key={i} className={f.level}>
            <span className="icon" aria-hidden>
              {LEVEL_ICON[f.level]}
            </span>
            <span className="line">line {f.line ?? "?"}</span>
            <span className="msg">{f.message}</span>
          </li>
        ))}
        {shown.length === 0 && (
          <li className="empty">
            {findings.length === 0
              ? "No findings — this itinerary validates clean 🎉"
              : "Nothing at this level."}
          </li>
        )}
      </ul>
    </section>
  );
}
