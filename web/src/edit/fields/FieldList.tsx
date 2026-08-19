import { useMemo } from "react";
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

  // Findings anchored to several of THIS object's fields (start_time/end_time/
  // duration, …). Each field highlights, but the message is shown once here.
  const groupFindings = useMemo(() => {
    const seen = new Set<string>();
    const out: Finding[] = [];
    for (const spec of specs) {
      for (const f of byPath.get(`${path}.${spec.key}`) ?? []) {
        const k = findingKey(f);
        if (shared.has(k) && !seen.has(k)) {
          seen.add(k);
          out.push(f);
        }
      }
    }
    return out;
  }, [byPath, shared, specs, path]);

  return (
    <>
      <div className="edit-fields">
        {specs.map((spec) => (
          <FieldRow
            key={spec.key}
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
        ))}
      </div>
      {groupFindings.length > 0 && (
        <div className="group-findings">
          <FindingList findings={groupFindings} />
        </div>
      )}
    </>
  );
}
