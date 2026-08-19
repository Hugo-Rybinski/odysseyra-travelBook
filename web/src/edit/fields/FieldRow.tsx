import { useId } from "react";
import type { FieldSpec } from "../schema";
import { useEditDefaults } from "../defaultsContext";
import { useFieldFindings, worstLevel } from "../findings";
import { FieldFindings } from "./FieldFindings";

// Renders one registry field as a labelled control. The value is whatever the
// draft holds for that key (string | number | boolean | string[] | undefined);
// `onChange(undefined)` means "clear this key" (the parent then prunes it), so
// an empty field, an unchecked default-false box and an unset enum all round-trip
// to an absent key — keeping saved JSON clean (the agreed pruning decision).
//
// `coordinate` is intentionally NOT handled here — forms render CoordinateField
// directly for those, since a coordinate is a nested object, not a scalar.
export interface FieldRowProps {
  spec: FieldSpec;
  value: unknown;
  path: string; // this field's dot-path, for anchoring validation findings
  onChange: (v: string | number | boolean | string[] | undefined) => void;
}

export function FieldRow({ spec, value, path, onChange }: FieldRowProps) {
  const id = useId();
  const findings = useFieldFindings(path);
  const level = worstLevel(findings);
  const defaults = useEditDefaults();
  // For a field that inherits an unset value from defaults.<key>, show the
  // effective value + its source in the empty placeholder, e.g.
  // "EUR (from defaults.currency)". Otherwise use the static placeholder.
  const placeholder = spec.inheritsFrom
    ? `${defaults[spec.inheritsFrom] ?? ""} (from defaults.${spec.inheritsFrom})`.trim()
    : spec.placeholder;
  const label = (
    <span className="edit-field-label">
      {spec.label}
      {spec.required && <em className="req" aria-hidden> *</em>}
      {spec.help && (
        <span className="edit-help" data-tip={spec.help} tabIndex={0} role="img" aria-label={spec.help}>
          ?
        </span>
      )}
    </span>
  );

  const levelClass = level ? `has-${level}` : "";

  // Checkboxes read best with the label to the right of the box.
  if (spec.kind === "bool") {
    return (
      <div className={`edit-field-wrap ${levelClass}`}>
        <label className="edit-field edit-field-bool" htmlFor={id}>
          <input
            id={id}
            type="checkbox"
            checked={value === true}
            onChange={(e) => onChange(e.target.checked ? true : undefined)}
          />
          {label}
        </label>
        <FieldFindings path={path} />
      </div>
    );
  }

  return (
    <div className={`edit-field-wrap ${levelClass}`}>
      <label className="edit-field" htmlFor={id}>
        {label}
        {renderControl(id, spec, placeholder, value, onChange)}
      </label>
      <FieldFindings path={path} />
    </div>
  );
}

function renderControl(
  id: string,
  spec: FieldSpec,
  placeholder: string | undefined,
  value: unknown,
  onChange: FieldRowProps["onChange"],
) {
  const str = value === undefined || value === null ? "" : String(value);

  switch (spec.kind) {
    case "textarea":
      return (
        <textarea
          id={id}
          className="edit-input"
          rows={3}
          placeholder={placeholder}
          value={str}
          onChange={(e) => onChange(e.target.value || undefined)}
        />
      );

    case "number":
    case "integer":
      return (
        <input
          id={id}
          className="edit-input"
          type="number"
          step={spec.kind === "integer" ? 1 : "any"}
          placeholder={placeholder}
          value={str}
          onChange={(e) => {
            const v = e.target.value;
            if (v === "") return onChange(undefined);
            const n = Number(v);
            onChange(Number.isNaN(n) ? undefined : spec.kind === "integer" ? Math.trunc(n) : n);
          }}
        />
      );

    case "date":
      return (
        <input
          id={id}
          className="edit-input"
          type="date"
          value={str}
          onChange={(e) => onChange(e.target.value || undefined)}
        />
      );

    case "time":
      return (
        <input
          id={id}
          className="edit-input"
          type="time"
          value={str}
          onChange={(e) => onChange(e.target.value || undefined)}
        />
      );

    case "enum":
      return (
        <select
          id={id}
          className="edit-input"
          value={str}
          onChange={(e) => onChange(e.target.value || undefined)}
        >
          <option value="">{placeholder ? `— ${placeholder} —` : "—"}</option>
          {(spec.enum ?? []).map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      );

    case "paid":
      return (
        <select
          id={id}
          className="edit-input"
          value={value === true ? "paid" : value === false ? "to pay" : str}
          onChange={(e) => onChange(e.target.value || undefined)}
        >
          <option value="">— unset —</option>
          <option value="paid">paid</option>
          <option value="to pay">to pay</option>
        </select>
      );

    case "color":
      return (
        <span className="edit-color">
          <input
            type="color"
            aria-label={`${spec.label} swatch`}
            value={/^#[0-9a-fA-F]{6}$/.test(str) ? str : "#1f4e5f"}
            onChange={(e) => onChange(e.target.value)}
          />
          <input
            id={id}
            className="edit-input"
            type="text"
            placeholder={placeholder}
            value={str}
            onChange={(e) => onChange(e.target.value || undefined)}
          />
        </span>
      );

    case "csv":
      return (
        <input
          id={id}
          className="edit-input"
          type="text"
          placeholder={placeholder}
          value={Array.isArray(value) ? value.join(", ") : str}
          onChange={(e) => {
            const parts = e.target.value
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean);
            onChange(parts.length ? parts : undefined);
          }}
        />
      );

    // text, duration, tz — plain text with a format hint
    default:
      return (
        <input
          id={id}
          className="edit-input"
          type="text"
          placeholder={placeholder}
          value={str}
          onChange={(e) => onChange(e.target.value || undefined)}
        />
      );
  }
}
