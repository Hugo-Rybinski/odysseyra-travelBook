import { useId } from "react";
import type { SrcCoordinate } from "../../types/source";
import { FieldFindings } from "./FieldFindings";

// A grouped editor for an optional coordinate ({lat, long, show_on_map}). Empty
// lat & long collapse the whole coordinate to undefined so it's pruned from the
// draft. `show_on_map` defaults to true when a coordinate is set, so we only
// store it when explicitly turned off.
//
// `path` is this coordinate's dot-path (e.g. "days.0.activities.1.coordinate");
// each sub-field anchors findings at `${path}.lat` / `.long` / `.show_on_map`.
export interface CoordinateFieldProps {
  label?: string;
  path: string;
  value: SrcCoordinate | undefined;
  onChange: (next: SrcCoordinate | undefined) => void;
}

export function CoordinateField({ label = "Coordinate", path, value, onChange }: CoordinateFieldProps) {
  const latId = useId();
  const longId = useId();

  const emit = (next: SrcCoordinate) => {
    const cleared = next.lat === undefined && next.long === undefined && next.show_on_map === undefined;
    onChange(cleared ? undefined : next);
  };

  const num = (v: string): number | undefined => {
    if (v === "") return undefined;
    const n = Number(v);
    return Number.isNaN(n) ? undefined : n;
  };

  const lat = value?.lat;
  const long = value?.long;
  const hidden = value?.show_on_map === false;

  return (
    <fieldset className="edit-coord">
      <legend>{label}</legend>
      <FieldFindings path={path} />
      <div className="edit-coord-row">
        <div className="edit-field-wrap">
          <label className="edit-field" htmlFor={latId}>
            <span className="edit-field-label">Lat</span>
            <input
              id={latId}
              className="edit-input"
              type="number"
              step="any"
              placeholder="43.0974"
              value={lat === undefined ? "" : String(lat)}
              onChange={(e) => emit({ ...value, lat: num(e.target.value) })}
            />
          </label>
          <FieldFindings path={`${path}.lat`} />
        </div>
        <div className="edit-field-wrap">
          <label className="edit-field" htmlFor={longId}>
            <span className="edit-field-label">Long</span>
            <input
              id={longId}
              className="edit-input"
              type="number"
              step="any"
              placeholder="-0.0583"
              value={long === undefined ? "" : String(long)}
              onChange={(e) => emit({ ...value, long: num(e.target.value) })}
            />
          </label>
          <FieldFindings path={`${path}.long`} />
        </div>
        <label className="edit-field edit-field-bool">
          <input
            type="checkbox"
            checked={hidden}
            onChange={(e) =>
              emit({ ...value, show_on_map: e.target.checked ? false : undefined })
            }
          />
          <span className="edit-field-label">Hide on map</span>
        </label>
      </div>
      <FieldFindings path={`${path}.show_on_map`} />
    </fieldset>
  );
}
