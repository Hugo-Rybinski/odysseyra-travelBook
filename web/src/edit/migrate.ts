// Bring an input document written on an older shape onto the current one, as
// it is loaded. Every load path seeds the Edit tab through `jsonToDraft`
// (edit/serialize.ts), so that is the one seam this runs at: the draft the user
// then sees, edits and saves is already migrated, and the key is rewritten in
// place rather than silently ignored.
//
// The rule for adding a migration here: it must be a *mechanical* rewrite whose
// meaning is certain from the old value alone. Anything needing a judgement call
// belongs in the validator, which reports it and leaves the file to the user.
//
// Nothing here *reports*: `validate` already names the old key, anchored to a
// line number in the user's own file (validator.py's `_retired_show_on_map`),
// which is better than any path list this could hand back. And nothing here is
// a permanent alias — the model reads `show_on_map` too (models/geo.py) so an
// unmigrated file still renders correctly from the CLI, and this is what makes
// the warning go away.

// `show_on_map` (default true) became `hide_on_map` (default false): the same
// question asked the other way round, so the value is negated. A deep rename by
// key name is safe and needs no schema table — the name appears nowhere else in
// the format, at any depth, and every object that can carry a coordinate
// (activities and their nested ones, road and transport legs, waypoints,
// accommodations, car rentals) is reached the same way.
function renameShowOnMap(node: unknown): { value: unknown; changed: boolean } {
  if (Array.isArray(node)) {
    let changed = false;
    const items = node.map((item) => {
      const r = renameShowOnMap(item);
      changed = changed || r.changed;
      return r.value;
    });
    return changed ? { value: items, changed } : { value: node, changed };
  }
  if (node === null || typeof node !== "object") return { value: node, changed: false };

  const src = node as Record<string, unknown>;
  // Rebuild the object key by key so `hide_on_map` takes the retired key's
  // *position* rather than being appended: a coordinate then still reads
  // `{lat, long, hide_on_map}` after a round-trip through the editor.
  const out: Record<string, unknown> = {};
  let changed = false;
  for (const [k, v] of Object.entries(src)) {
    if (k === "show_on_map") {
      changed = true;
      // An explicit `show_on_map: true` said "plot it", which is now the
      // default, so it collapses to nothing rather than to
      // `hide_on_map: false` — the same pruning `SAFE_DEFAULTS` does on save.
      if (!truthy(v)) out.hide_on_map = true;
      continue;
    }
    const r = renameShowOnMap(v);
    changed = changed || r.changed;
    out[k] = r.value;
  }
  return changed ? { value: out, changed } : { value: node, changed };
}

// Matches the Python `_parse_bool` / validator `_truthy` reading of a value a
// user may have written as a string.
function truthy(v: unknown): boolean {
  if (typeof v === "string") return ["1", "true", "yes", "y"].includes(v.trim().toLowerCase());
  return !!v;
}

/**
 * Migrate a parsed input document onto the current shape. A document that is
 * already current is returned as-is (same object, no copy).
 */
export function migrateSource<T>(data: T): T {
  return renameShowOnMap(data).value as T;
}
