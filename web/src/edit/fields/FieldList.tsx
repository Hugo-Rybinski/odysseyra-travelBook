import { Fragment, useMemo } from "react";
import type { Finding } from "../../types/resolved";
import type { FieldSpec } from "../schema";
import { findingKey, useFindingIndex } from "../findings";
import { FindingList } from "./FieldFindings";
import { FieldRow } from "./FieldRow";

// Renders a list of registry fields against a plain record and reports each edit
// as a whole-object replacement. A field that clears (onChange(undefined)) drops
// its key from the object, so defaults/empties never linger in the draft.
//
// `path` is the dot-path of the object being edited; each field's own path is
// `${path}.${key}`, used to anchor validation findings inline (Option B).
export interface FieldListProps {
  specs: FieldSpec[];
  value: Record<string, unknown>;
  path: string;
  onChange: (next: Record<string, unknown>) => void;
}

export function FieldList({ specs, value, path, onChange }: FieldListProps) {
  const { byPath, shared } = useFindingIndex();

  // A finding anchored to several of this object's fields (e.g. start_time /
  // end_time / duration) highlights each field's border, but its message is
  // shown once — placed right after the LAST field it involves, so it sits next
  // to those inputs rather than repeated under each or dumped at the very end.
  const groupAfter = useMemo(() => {
    const involved = new Map<string, { f: Finding; lastIdx: number }>();
    specs.forEach((spec, idx) => {
      for (const f of byPath.get(`${path}.${spec.key}`) ?? []) {
        const k = findingKey(f);
        if (!shared.has(k)) continue;
        const cur = involved.get(k);
        if (!cur || idx > cur.lastIdx) involved.set(k, { f, lastIdx: idx });
      }
    });
    const bySpecKey = new Map<string, Finding[]>();
    for (const { f, lastIdx } of involved.values()) {
      const specKey = specs[lastIdx].key;
      const list = bySpecKey.get(specKey);
      if (list) list.push(f);
      else bySpecKey.set(specKey, [f]);
    }
    return bySpecKey;
  }, [byPath, shared, specs, path]);

  return (
    <div className="edit-fields">
      {specs.map((spec) => {
        const after = groupAfter.get(spec.key);
        return (
          <Fragment key={spec.key}>
            <FieldRow
              spec={spec}
              value={value[spec.key]}
              path={`${path}.${spec.key}`}
              onChange={(v) => {
                const next = { ...value };
                if (v === undefined) delete next[spec.key];
                else next[spec.key] = v;
                onChange(next);
              }}
            />
            {after && after.length > 0 && (
              <div className="group-findings">
                <FindingList findings={after} />
              </div>
            )}
          </Fragment>
        );
      })}
    </div>
  );
}
