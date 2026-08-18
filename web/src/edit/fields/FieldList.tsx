import type { FieldSpec } from "../schema";
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
  return (
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
  );
}
