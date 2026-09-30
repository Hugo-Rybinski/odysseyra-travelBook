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

/** Is this span entirely behind us? An undated one never is — "unknown" is not
 * "over". Same rule `collapse-past` collapses on, so the two can't drift. */
function isPast(span: DateSpan, today: string): boolean {
  const end = span.end ?? span.start;
  return end != null && end < today;
}

// The entries a view folds **away** — rendered not at all, behind one line that
// puts them back (see `PastFold`) — rather than merely collapsing to a header.
// A run of rows for days already travelled, flights already taken and hotels
// already slept in is what stands between the reader and the part of the trip
// that hasn't happened yet, and collapsing them only makes each row shorter.
//
// It is `past ∩ collapsed`, not the past entries outright, so **an entry the
// view leaves expanded is never folded away**: `current-only` falls back to the
// first entry when nothing covers today, and that entry can itself be past —
// hiding it would fold away the one card the view exists to show. Deriving it
// from `collapsedForItems` is also what keeps the two in step by construction.
export function foldedForItems(view: CollapseView, items: DateSpan[]): Set<number> {
  if (view === "expand-all") return new Set();
  const collapsed = collapsedForItems(view, items);
  const today = todayISO();
  return new Set(items.map((_, i) => i).filter((i) => collapsed.has(i) && isPast(items[i], today)));
}

/** Is every entry behind us — a list already lived through? Then the fold would
 * leave nothing on screen at all, so callers start it revealed. Measured on the
 * whole list rather than on the fold set, so `current-only`'s kept entry doesn't
 * stop it counting; an undated entry (never past) keeps it false. */
export function allItemsPast(items: DateSpan[]): boolean {
  if (!items.length) return false;
  const today = todayISO();
  return items.every((it) => isPast(it, today));
}

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
