import { useId } from "react";
import type { FieldSpec } from "../schema";
import { useEditDefaults } from "../defaultsContext";
import { useFieldFindings, worstLevel } from "../findings";
import { useT, type TFn } from "../../i18n";
import { FieldFindings } from "./FieldFindings";
import { GpxField } from "./GpxField";
import { Toggle } from "./Toggle";

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
  const t = useT();
  const findings = useFieldFindings(path);
  const level = worstLevel(findings);
  const defaults = useEditDefaults();
  // For a field that inherits an unset value from defaults.<key>, show the
  // effective value + its source in the empty placeholder, e.g.
  // "EUR (from defaults.currency)". Otherwise use the static placeholder.
  const placeholder = spec.inheritsFrom
    ? t("{value} (from defaults.{key})", {
        value: defaults[spec.inheritsFrom] ?? "",
        key: spec.inheritsFrom,
      })
    : spec.placeholder
      ? t(spec.placeholder)
      : undefined;
  const help = spec.help ? t(spec.help) : undefined;
  const label = (
    <span className="edit-field-label">
      {t(spec.label)}
      {spec.required && <em className="req" aria-hidden> *</em>}
      {help && (
        <span className="edit-help" data-tip={help} tabIndex={0} role="img" aria-label={help}>
          ?
        </span>
      )}
    </span>
  );

  const levelClass = level ? `has-${level}` : "";

  // A bool is a switch under its label — same shape and height as the controls
  // around it, so a row of fields stays aligned whatever kinds it mixes.
  if (spec.kind === "bool") {
    // A default-on flag is ON while its key is absent, so the switch reflects
    // "anything but an explicit false". Either way the key is cleared when the
    // switch matches the field's default, keeping the saved JSON free of no-ops.
    const on = spec.defaultOn ? value !== false : value === true;
    return (
      <div className={`edit-field-wrap ${levelClass}`}>
        <label className="edit-field edit-field-bool" htmlFor={id}>
          {label}
          <Toggle
            id={id}
            checked={on}
            onChange={(next) => onChange(next === !!spec.defaultOn ? undefined : next)}
          />
        </label>
        <FieldFindings path={path} />
      </div>
    );
  }

  return (
    <div
      className={`edit-field-wrap ${levelClass} ${
        spec.kind === "textarea" || spec.kind === "gpx" ? "full" : ""
      }`}
    >
      <label className="edit-field" htmlFor={id}>
        {label}
        {renderControl(id, spec, placeholder, value, onChange, t)}
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
  t: TFn,
) {
  const str = value === undefined || value === null ? "" : String(value);

  switch (spec.kind) {
    // A hike's trail file: a file picker that base64-encodes into the draft.
    case "gpx":
      return <GpxField id={id} value={value} onChange={onChange} />;

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
              {t(opt)}
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
          <option value="">{t("— unset —")}</option>
          <option value="paid">{t("paid")}</option>
          <option value="to pay">{t("to pay")}</option>
        </select>
      );

    case "color":
      return (
        <span className="edit-color">
          <input
            type="color"
            aria-label={t("{label} swatch", { label: t(spec.label) })}
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
