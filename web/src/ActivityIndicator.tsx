// The app's loader: a small floating card naming whatever the engine is busy
// with (warming up, resolving a file, building the PDF, drawing day 3's map).
//
// It is deliberately **non-blocking** — no backdrop, `pointer-events: none`, and
// the page stays scrollable and clickable underneath. That's the whole point of
// moving Pyodide into a worker (see pyodide/worker.ts): the work no longer
// freezes the UI, so the honest way to show it is an unobtrusive status, not a
// modal that pretends the app is unusable.
//
// Renders nothing when idle, so the caller can mount it unconditionally.

export interface ActivityItem {
  /** Stable key — also lets a caller replace one line without remounting. */
  id: string;
  /** Already-localized label, e.g. "Building the PDF…". */
  label: string;
}

export function ActivityIndicator({ items }: { items: ActivityItem[] }) {
  if (!items.length) return null;
  return (
    <div className="activity" role="status" aria-live="polite">
      <span className="activity-spin" aria-hidden />
      <ul className="activity-list">
        {items.map((item) => (
          <li key={item.id}>{item.label}</li>
        ))}
      </ul>
    </div>
  );
}
