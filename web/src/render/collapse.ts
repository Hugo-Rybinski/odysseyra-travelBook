// Shared "how does a list start collapsed" logic, used by the day timeline and
// the transport / accommodation card lists. Each entry has a date span; the
// view decides which entries begin collapsed.
export type CollapseView = "collapse-all" | "collapse-past" | "current-only" | "expand-all";

export function todayISO(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export type DateSpan = { start: string | null; end: string | null };

// The set of item indices that start collapsed for `view`, given each item's
// date span (ISO YYYY-MM-DD, either end nullable).
export function collapsedForItems(view: CollapseView, items: DateSpan[]): Set<number> {
  if (view === "expand-all") return new Set();
  const idx = items.map((_, i) => i);
  if (view === "collapse-all") return new Set(idx);

  const today = todayISO();
  if (view === "collapse-past") {
    // collapse entries entirely in the past (their end is before today); keep
    // current, future, and undated ones open
    return new Set(
      idx.filter((i) => {
        const end = items[i].end ?? items[i].start;
        return end != null && end < today;
      }),
    );
  }

  // current-only: keep the entry whose span covers today open (else the first),
  // collapse the rest
  const current = idx.find((i) => {
    const start = items[i].start;
    const end = items[i].end ?? items[i].start;
    return start != null && end != null && start <= today && today <= end;
  });
  const keep = current ?? idx[0];
  return new Set(idx.filter((i) => i !== keep));
}
