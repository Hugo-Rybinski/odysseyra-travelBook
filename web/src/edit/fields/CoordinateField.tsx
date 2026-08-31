import { useId, useState } from "react";
import type { SrcCoordinate } from "../../types/source";
import { useGeocode } from "../geocodeContext";
import { useT } from "../../i18n";
import { FieldFindings } from "./FieldFindings";
import { Toggle } from "./Toggle";

// A grouped editor for an optional coordinate ({lat, long, show_on_map}). Empty
// lat & long collapse the whole coordinate to undefined so it's pruned from the
// draft. `show_on_map` defaults to true when a coordinate is set, so we only
// store it when explicitly turned off.
//
// `path` is this coordinate's dot-path (e.g. "days.0.activities.1.coordinate");
// each sub-field anchors findings at `${path}.lat` / `.long` / `.show_on_map`.
//
// Two helpers (P5): paste a "lat, long" pair to fill both at once, and — when a
// `geocodeQuery` (the object's address/name) and the geocode context are present
// — a "Geocode from address" button that fills the coordinate from Nominatim.
export interface CoordinateFieldProps {
  label?: string;
  path: string;
  value: SrcCoordinate | undefined;
  geocodeQuery?: string;
  onChange: (next: SrcCoordinate | undefined) => void;
}

// Parse a pasted "43.0974, -0.0583" (comma, semicolon or whitespace separated).
function parsePair(text: string): { lat: number; long: number } | null {
  const nums = text.trim().split(/[\s,;]+/).map(Number);
  if (nums.length === 2 && nums.every((n) => Number.isFinite(n))) {
    return { lat: nums[0], long: nums[1] };
  }
  return null;
}

export function CoordinateField({
  label = "Coordinate",
  path,
  value,
  geocodeQuery,
  onChange,
}: CoordinateFieldProps) {
  const t = useT();
  const latId = useId();
  const longId = useId();
  const geo = useGeocode();
  const [paste, setPaste] = useState("");
  const [geocoding, setGeocoding] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const emit = (next: SrcCoordinate) => {
    const cleared = next.lat === undefined && next.long === undefined && next.show_on_map === undefined;
    onChange(cleared ? undefined : next);
  };

  const num = (v: string): number | undefined => {
    if (v === "") return undefined;
    const n = Number(v);
    return Number.isNaN(n) ? undefined : n;
  };

  const applyPair = (text: string) => {
    setPaste(text);
    const pair = parsePair(text);
    if (pair) {
      emit({ ...value, lat: pair.lat, long: pair.long });
      setPaste("");
      setNote(null);
    }
  };

  const query = geocodeQuery?.trim();
  const runGeocode = async () => {
    if (!geo || !query) return;
    setGeocoding(true);
    setNote(null);
    try {
      const hit = await geo.geocode(query);
      if (hit) emit({ ...value, lat: hit.lat, long: hit.long });
      else setNote(t("No match for “{query}”.", { query }));
    } catch (e) {
      setNote(String(e));
    } finally {
      setGeocoding(false);
    }
  };

  const lat = value?.lat;
  const long = value?.long;
  const hidden = value?.show_on_map === false;

  return (
    <fieldset className="edit-coord">
      <legend>{t(label)}</legend>
      <FieldFindings path={path} />

      <div className="edit-coord-helpers">
        <input
          className="edit-input edit-coord-paste"
          type="text"
          aria-label={t("{label}: paste latitude, longitude", { label: t(label) })}
          placeholder={t("paste: 43.0974, -0.0583")}
          value={paste}
          onChange={(e) => applyPair(e.target.value)}
        />
        {geo && query && (
          <button
            type="button"
            className="btn subtle"
            onClick={runGeocode}
            disabled={!geo.ready || geocoding}
            data-tip={
              geo.ready
                ? t("Look up “{query}” and fill the coordinate", { query })
                : t("Geocoding needs the engine ready and a network connection")
            }
          >
            {geocoding ? t("Geocoding…") : t("Geocode from address")}
          </button>
        )}
      </div>
      {note && <p className="edit-coord-note">{note}</p>}

      <div className="edit-coord-row">
        <div className="edit-field-wrap">
          <label className="edit-field" htmlFor={latId}>
            <span className="edit-field-label">
              {t("Lat")}
              <span className="edit-help" data-tip={t("Latitude, −90 to 90. Leave both lat & long empty to omit the coordinate.")} tabIndex={0} role="img" aria-label={t("Latitude, −90 to 90.")}>
                ?
              </span>
            </span>
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
            <span className="edit-field-label">
              {t("Long")}
              <span className="edit-help" data-tip={t("Longitude, −180 to 180. Leave both lat & long empty to omit the coordinate.")} tabIndex={0} role="img" aria-label={t("Longitude, −180 to 180.")}>
                ?
              </span>
            </span>
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
          <span className="edit-field-label">
            {t("Hide on map")}
            <span className="edit-help" data-tip={t("Plot this point on the map. Shown by default when a coordinate is set; switch this on to hide it while keeping the coordinate.")} tabIndex={0} role="img" aria-label={t("Hide this point on the map.")}>
              ?
            </span>
          </span>
          <Toggle
            checked={hidden}
            label={t("Hide on map")}
            onChange={(next) => emit({ ...value, show_on_map: next ? false : undefined })}
          />
        </label>
      </div>
      <FieldFindings path={`${path}.show_on_map`} />
    </fieldset>
  );
}
