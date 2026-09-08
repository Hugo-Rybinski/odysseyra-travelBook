// The app's loader: a small floating card naming whatever the engine is busy
// with (warming up, resolving a file, building the PDF, drawing day 3's map).
//
// It is deliberately **non-blocking** — no backdrop, `pointer-events: none`, and
// the page stays scrollable and clickable underneath. That's the whole point of
// moving Pyodide into a worker (see pyodide/worker.ts): the work no longer
// freezes the UI, so the honest way to show it is an unobtrusive status, not a
// modal that pretends the app is unusable.
//
// It also carries transient *results* (`notice`) — the update check's answer —
// so a one-off message reads in the same place, and the same shape, as the
// running work it interrupts. That replaced a second floating strip of its own
// (the old `.toasts` / `<PwaStatus>`): two stacked cards saying different kinds
// of thing was one visual language too many for a status line.
//
// Renders nothing when idle, so the caller can mount it unconditionally.

export interface ActivityItem {
  /** Stable key — also lets a caller replace one line without remounting. */
  id: string;
  /** Already-localized label, e.g. "Building the PDF…". */
  label: string;
}

export interface ActivityNotice {
  /** Already-localized line, e.g. "Update found: a1b2c3d (2026-09-08 19:45)". */
  label: string;
  /** Leading glyph — it stands in for the spinner when nothing is in flight,
   * which is the usual case for a result. */
  glyph: string;
}

export function ActivityIndicator({
  items,
  notice,
}: {
  items: ActivityItem[];
  notice?: ActivityNotice | null;
}) {
  if (!items.length && !notice) return null;
  const working = items.length > 0;
  return (
    <div className="activity" role="status" aria-live="polite">
      {working ? (
        <span className="activity-spin" aria-hidden />
      ) : (
        <span className="activity-glyph" aria-hidden>
          {notice!.glyph}
        </span>
      )}
      <ul className="activity-list">
        {items.map((item) => (
          <li key={item.id}>{item.label}</li>
        ))}
        {/* Last, so the shared `li + li` rule mutes it while something is
            running — a result is secondary to the work you just asked for —
            and it reads at full weight when it's the only line. */}
        {notice && <li key="notice">{notice.label}</li>}
      </ul>
    </div>
  );
}
