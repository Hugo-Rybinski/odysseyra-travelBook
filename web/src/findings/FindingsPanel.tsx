import { useMemo, useState } from "react";
import type { Finding, FindingLevel } from "../types/resolved";
import { useT } from "../i18n";

const LEVEL_ICON: Record<FindingLevel, string> = {
  error: "❌",
  warning: "⚠️",
  info: "ℹ️",
};

const LEVEL_ORDER: FindingLevel[] = ["error", "warning", "info"];

export function FindingsPanel({
  findings,
  title = "Validation",
}: {
  findings: Finding[];
  title?: string;
}) {
  const t = useT();
  // Multi-select level toggles (combined additively): a finding shows when its
  // level is selected. Errors + warnings are on by default so the "optional
  // missing" info flood stays hidden until asked for.
  const [selected, setSelected] = useState<Set<FindingLevel>>(
    () => new Set<FindingLevel>(["error", "warning"]),
  );

  const toggle = (level: FindingLevel) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(level) ? next.delete(level) : next.add(level);
      return next;
    });

  const counts = useMemo(() => {
    const c: Record<FindingLevel, number> = { error: 0, warning: 0, info: 0 };
    for (const f of findings) c[f.level]++;
    return c;
  }, [findings]);

  // Errors first, then warnings, then info; a stable order within each level.
  const shown = useMemo(() => {
    return [...findings]
      .filter((f) => selected.has(f.level))
      .sort((a, b) => LEVEL_ORDER.indexOf(a.level) - LEVEL_ORDER.indexOf(b.level));
  }, [findings, selected]);

  return (
    <section className="findings" aria-label={t("Validation findings")}>
      <div className="findings-head">
        <h3>{t(title)}</h3>
        <div className="chips" role="group" aria-label={t("Filter by level")}>
          {LEVEL_ORDER.map((level) => (
            <button
              key={level}
              aria-pressed={selected.has(level)}
              className={`chip ${selected.has(level) ? "active" : ""} ${level}`}
              onClick={() => toggle(level)}
            >
              {LEVEL_ICON[level]} {counts[level]}
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
            <span className="line">{t("line {line}", { line: f.line ?? "?" })}</span>
            <span className="msg">{f.message}</span>
          </li>
        ))}
        {shown.length === 0 && (
          <li className="empty">
            {findings.length === 0
              ? t("No findings — this itinerary validates clean 🎉")
              : selected.size === 0
                ? t("Select a level above to show findings.")
                : t("Nothing at the selected levels.")}
          </li>
        )}
      </ul>
    </section>
  );
}
