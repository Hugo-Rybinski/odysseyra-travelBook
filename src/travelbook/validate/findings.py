"""Findings (error / warning / info) and their rendering."""

from __future__ import annotations

from dataclasses import dataclass

from ..lang import DEFAULT_LANGUAGE, tr

CROSS = "❌"  # error
WARN = "⚠️"  # important warning
INFO = "ℹ️"  # low-priority note (e.g. an optional field defaulting)
CHECK = "✅"  # all good


_ICONS = {"error": CROSS, "warning": WARN, "info": INFO}


@dataclass
class Finding:
    level: str  # "error" | "warning" | "info"
    line: int | None
    message: str

    def render(self) -> str:
        where = f"line {self.line}" if self.line else "line ?"
        return f"{_ICONS.get(self.level, WARN)}  {where}: {self.message}"




def format_findings(findings: list[Finding], verbose: int = 2,
                    lang: str = DEFAULT_LANGUAGE) -> str:
    """Render findings, filtered by ``verbose``:

    * 1 — errors only
    * 2 — errors + warnings (default)
    * 3 — everything, including low-priority info notes
    """
    if not findings:
        return f"{CHECK}  " + tr("No problems found.", lang)
    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]
    infos = [f for f in findings if f.level == "info"]

    allowed = {"error"}
    if verbose >= 2:
        allowed.add("warning")
    if verbose >= 3:
        allowed.add("info")
    rank = {"error": 0, "warning": 1, "info": 2}
    shown = sorted((f for f in findings if f.level in allowed),
                   key=lambda f: (f.line or 0, rank[f.level]))

    summary = tr("{errors} error(s), {warnings} warning(s), {infos} info", lang).format(
        errors=len(errors), warnings=len(warnings), infos=len(infos))
    hidden = []
    if verbose < 2 and warnings:
        hidden.append(tr("{count} warning(s)", lang).format(count=len(warnings)))
    if verbose < 3 and infos:
        hidden.append(tr("{count} info", lang).format(count=len(infos)))
    if hidden:
        summary += tr(" — {hidden} hidden (raise --verbose)", lang).format(
            hidden=", ".join(hidden))
    summary += "."

    body = "\n".join(f.render() for f in shown)
    return f"{body}\n\n{summary}" if body else summary
