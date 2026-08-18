import { FINDING_ICON, useFieldFindings } from "../findings";

// Renders the validation findings anchored to one field path (Option B), inline
// beneath the control. Returns null when there are none, so callers can drop it
// in unconditionally.
export function FieldFindings({ path }: { path: string }) {
  const findings = useFieldFindings(path);
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
