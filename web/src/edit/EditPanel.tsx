import type { Finding } from "../types/resolved";
import type {
  SrcAccommodation,
  SrcCarRental,
  SrcDay,
  SrcItinerary,
  SrcTransport,
} from "../types/source";
import { FindingsPanel } from "../findings/FindingsPanel";
import { newAccommodation, newCarRental, newDay, newTransport } from "./schema";
import { EditFindingsContext } from "./findings";
import { EditGeocodeContext, type GeocodeApi } from "./geocodeContext";
import { ArrayEditor } from "./fields/ArrayEditor";
import { AccommodationForm } from "./forms/AccommodationForm";
import { CarRentalForm } from "./forms/CarRentalForm";
import { DayForm } from "./forms/DayForm";
import { DefaultsForm, TravelDescriptionForm } from "./forms/ConfigForms";
import { TransportForm } from "./forms/TransportForm";

// The Edit tab: a structured form over the *input* itinerary JSON. Stacked,
// collapsible sections — two config groups (Trip, Defaults) and four content
// arrays (Days, Transport, Accommodations, Car rentals). Every edit produces a
// new draft via `onChange`.
//
// P2: validation findings are anchored to fields inline (Option B) via
// `findingIndex` (a map of field-path → findings, provided through context and
// read by each FieldRow). Findings that don't map to a rendered field — mostly
// cross-object coherence warnings — surface in the rail at the top so nothing is
// silently dropped. Preview/save wiring still lands in later phases.
export interface EditPanelProps {
  draft: SrcItinerary;
  onChange: (next: SrcItinerary) => void;
  findingIndex: Map<string, Finding[]>;
  rail: Finding[];
  validating: boolean;
  validationError: string | null;
  // Apply (P3): push the draft into the viewer/findings/export.
  dirty: boolean;
  applying: boolean;
  engineReady: boolean;
  mapsInRender: boolean;
  onApply: () => void;
  onApplyRedraw: () => void;
  // Save (P4): write the draft to a file.
  unsaved: boolean;
  saving: boolean;
  canSaveInPlace: boolean;
  hasSavePicker: boolean;
  onSave: () => void;
  onSaveAs: () => void;
  onDownloadJson: () => void;
  // Undo/redo/revert (P6).
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onRevert: () => void;
  // Geocode (P5): fill a coordinate from an address; null when unavailable.
  geocode: GeocodeApi | null;
}

export function EditPanel({
  draft,
  onChange,
  findingIndex,
  rail,
  validating,
  validationError,
  dirty,
  applying,
  engineReady,
  mapsInRender,
  onApply,
  onApplyRedraw,
  unsaved,
  saving,
  canSaveInPlace,
  hasSavePicker,
  onSave,
  onSaveAs,
  onDownloadJson,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onRevert,
  geocode,
}: EditPanelProps) {
  const days = draft.days ?? [];
  const transport = draft.transport ?? [];
  const accommodations = draft.accommodations ?? [];
  const carRentals = draft.car_rentals ?? [];

  return (
    <EditFindingsContext.Provider value={findingIndex}>
      <EditGeocodeContext.Provider value={geocode}>
      <div className="edit-panel" role="region" aria-label="Edit itinerary">
        <div className="edit-actions">
          <button
            className="btn"
            onClick={onApply}
            disabled={!dirty || applying || !engineReady}
          >
            {applying ? "Applying…" : dirty ? "Apply changes" : "Applied ✓"}
          </button>
          {mapsInRender && (
            <button
              className="btn subtle"
              onClick={onApplyRedraw}
              disabled={applying || !engineReady}
              data-tip="Apply the draft and rebuild this itinerary's maps"
            >
              Apply &amp; redraw maps
            </button>
          )}

          <span className="edit-actions-sep" aria-hidden />

          <button
            type="button"
            className="btn subtle"
            onClick={onUndo}
            disabled={!canUndo}
            data-tip="Undo the last edit"
          >
            ↶ Undo
          </button>
          <button
            type="button"
            className="btn subtle"
            onClick={onRedo}
            disabled={!canRedo}
            data-tip="Redo"
          >
            ↷ Redo
          </button>
          <button
            type="button"
            className="btn subtle"
            onClick={onRevert}
            disabled={!unsaved}
            data-tip="Discard changes since the last save/open"
          >
            Revert
          </button>

          <span className="edit-actions-sep" aria-hidden />

          {canSaveInPlace && (
            <button
              className="btn subtle"
              onClick={onSave}
              disabled={!unsaved || saving}
              data-tip="Overwrite the opened file"
            >
              {saving ? "Saving…" : unsaved ? "Save" : "Saved ✓"}
            </button>
          )}
          {hasSavePicker && (
            <button className="btn subtle" onClick={onSaveAs} disabled={saving} data-tip="Save to a new file">
              Save as…
            </button>
          )}
          <button
            className="btn subtle"
            onClick={onDownloadJson}
            disabled={saving}
            data-tip="Download the itinerary as a .json file"
          >
            Download JSON
          </button>

          {dirty && (
            <span className="edit-dirty">
              Unapplied edits — the viewer and export still show the last applied version.
            </span>
          )}
          {unsaved && !dirty && <span className="edit-dirty">Unsaved changes.</span>}
        </div>

        <EditStatus rail={rail} validating={validating} validationError={validationError} />

        <details className="edit-section" open>
          <summary>Trip</summary>
          <div className="edit-section-body">
            <TravelDescriptionForm
              value={draft.travel_description ?? {}}
              path="travel_description"
              onChange={(td) => onChange({ ...draft, travel_description: td })}
            />
          </div>
        </details>

        <details className="edit-section">
          <summary>Defaults</summary>
          <div className="edit-section-body">
            <DefaultsForm
              value={draft.defaults ?? {}}
              path="defaults"
              onChange={(d) => onChange({ ...draft, defaults: d })}
            />
          </div>
        </details>

        <details className="edit-section" open>
          <summary>Days ({days.length})</summary>
          <div className="edit-section-body">
            <ArrayEditor<SrcDay>
              items={days}
              onChange={(next) => onChange({ ...draft, days: next })}
              basePath="days"
              itemTitle={(d, i) => d.title || `Day ${i + 1}`}
              add={[{ label: "day", make: newDay }]}
              emptyLabel="No days yet — an itinerary needs at least one."
              renderItem={(d, _i, onItemChange, itemPath) => (
                <DayForm day={d} path={itemPath} onChange={onItemChange} />
              )}
            />
          </div>
        </details>

        <details className="edit-section">
          <summary>Transport ({transport.length})</summary>
          <div className="edit-section-body">
            <ArrayEditor<SrcTransport>
              items={transport}
              onChange={(next) => onChange({ ...draft, transport: next })}
              basePath="transport"
              itemTitle={(t, i) =>
                t.start || t.end ? `${t.start || "?"} → ${t.end || "?"}` : `Transport ${i + 1}`
              }
              add={[{ label: "transport", make: newTransport }]}
              emptyLabel="No transport legs."
              renderItem={(t, _i, onItemChange, itemPath) => (
                <TransportForm value={t} path={itemPath} onChange={onItemChange} />
              )}
            />
          </div>
        </details>

        <details className="edit-section">
          <summary>Accommodations ({accommodations.length})</summary>
          <div className="edit-section-body">
            <ArrayEditor<SrcAccommodation>
              items={accommodations}
              onChange={(next) => onChange({ ...draft, accommodations: next })}
              basePath="accommodations"
              itemTitle={(a, i) => a.name || a.city || `Accommodation ${i + 1}`}
              add={[{ label: "accommodation", make: newAccommodation }]}
              emptyLabel="No accommodations."
              renderItem={(a, _i, onItemChange, itemPath) => (
                <AccommodationForm value={a} path={itemPath} onChange={onItemChange} />
              )}
            />
          </div>
        </details>

        <details className="edit-section">
          <summary>Car rentals ({carRentals.length})</summary>
          <div className="edit-section-body">
            <ArrayEditor<SrcCarRental>
              items={carRentals}
              onChange={(next) => onChange({ ...draft, car_rentals: next })}
              basePath="car_rentals"
              itemTitle={(c, i) => c.company || c.pickup_location || `Car rental ${i + 1}`}
              add={[{ label: "car rental", make: newCarRental }]}
              emptyLabel="No car rentals."
              renderItem={(c, _i, onItemChange, itemPath) => (
                <CarRentalForm value={c} path={itemPath} onChange={onItemChange} />
              )}
            />
          </div>
        </details>
      </div>
      </EditGeocodeContext.Provider>
    </EditFindingsContext.Provider>
  );
}

// The header strip: a live "validating…" note, a parse/validation error (if the
// draft couldn't be checked), and the rail of findings not anchored to a field
// (mostly cross-object coherence warnings and "optional missing" info notes).
// The rail reuses FindingsPanel so it inherits the level filter that tames the
// info flood.
function EditStatus({
  rail,
  validating,
  validationError,
}: {
  rail: Finding[];
  validating: boolean;
  validationError: string | null;
}) {
  return (
    <div className="edit-status">
      {validating && <p className="edit-validating">◌ Validating…</p>}
      {validationError && <p className="banner error">⚠️ {validationError}</p>}
      {rail.length > 0 && <FindingsPanel findings={rail} title="Other findings" />}
    </div>
  );
}
