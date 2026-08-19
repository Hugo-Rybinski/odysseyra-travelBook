import type { Finding } from "../../types/resolved";
import { FINDING_ICON, findingKey, useFindingIndex } from "../findings";

// Presentational list of findings (icon + message), red/yellow-tinted by level.
export function FindingList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) return null;
  return (
    <ul className="field-findings">
      {findings.map((f, i) => (
        <li key={i} className={`ff ${f.level}`}>
          <span aria-hidden>{FINDING_ICON[f.level]}</span> {f.message}
        </li>
      ))}
    </ul>
  );
}

// The findings anchored to one field path (Option B), inline beneath the
// control — but only those unique to this field. A finding anchored to several
// fields (its key is in `shared`) still highlights each field's border, yet its
// message is shown once by the field group instead of repeated here.
export function FieldFindings({ path }: { path: string }) {
  const { byPath, shared } = useFindingIndex();
  const own = (byPath.get(path) ?? []).filter((f) => !shared.has(findingKey(f)));
  return <FindingList findings={own} />;
}
