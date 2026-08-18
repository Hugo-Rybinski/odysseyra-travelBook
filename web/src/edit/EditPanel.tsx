import type {
  SrcAccommodation,
  SrcCarRental,
  SrcDay,
  SrcItinerary,
  SrcTransport,
} from "../types/source";
import { newAccommodation, newCarRental, newDay, newTransport } from "./schema";
import { ArrayEditor } from "./fields/ArrayEditor";
import { AccommodationForm } from "./forms/AccommodationForm";
import { CarRentalForm } from "./forms/CarRentalForm";
import { DayForm } from "./forms/DayForm";
import { DefaultsForm, TravelDescriptionForm } from "./forms/ConfigForms";
import { TransportForm } from "./forms/TransportForm";

// The Edit tab: a structured form over the *input* itinerary JSON. Stacked,
// collapsible sections — two config groups (Trip, Defaults) and four content
// arrays (Days, Transport, Accommodations, Car rentals). Every edit produces a
// new draft via `onChange`; P1 has no preview/validation/save wiring yet, so
// edits stay in the draft until later phases connect Apply / Save.
export interface EditPanelProps {
  draft: SrcItinerary;
  onChange: (next: SrcItinerary) => void;
}

export function EditPanel({ draft, onChange }: EditPanelProps) {
  const days = draft.days ?? [];
  const transport = draft.transport ?? [];
  const accommodations = draft.accommodations ?? [];
  const carRentals = draft.car_rentals ?? [];

  return (
    <div className="edit-panel" role="region" aria-label="Edit itinerary">
      <details className="edit-section" open>
        <summary>Trip</summary>
        <div className="edit-section-body">
          <TravelDescriptionForm
            value={draft.travel_description ?? {}}
            onChange={(td) => onChange({ ...draft, travel_description: td })}
          />
        </div>
      </details>

      <details className="edit-section">
        <summary>Defaults</summary>
        <div className="edit-section-body">
          <DefaultsForm
            value={draft.defaults ?? {}}
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
            itemTitle={(d, i) => d.title || `Day ${i + 1}`}
            add={[{ label: "day", make: newDay }]}
            emptyLabel="No days yet — an itinerary needs at least one."
            renderItem={(d, _i, onItemChange) => <DayForm day={d} onChange={onItemChange} />}
          />
        </div>
      </details>

      <details className="edit-section">
        <summary>Transport ({transport.length})</summary>
        <div className="edit-section-body">
          <ArrayEditor<SrcTransport>
            items={transport}
            onChange={(next) => onChange({ ...draft, transport: next })}
            itemTitle={(t, i) =>
              t.start || t.end ? `${t.start || "?"} → ${t.end || "?"}` : `Transport ${i + 1}`
            }
            add={[{ label: "transport", make: newTransport }]}
            emptyLabel="No transport legs."
            renderItem={(t, _i, onItemChange) => <TransportForm value={t} onChange={onItemChange} />}
          />
        </div>
      </details>

      <details className="edit-section">
        <summary>Accommodations ({accommodations.length})</summary>
        <div className="edit-section-body">
          <ArrayEditor<SrcAccommodation>
            items={accommodations}
            onChange={(next) => onChange({ ...draft, accommodations: next })}
            itemTitle={(a, i) => a.name || a.city || `Accommodation ${i + 1}`}
            add={[{ label: "accommodation", make: newAccommodation }]}
            emptyLabel="No accommodations."
            renderItem={(a, _i, onItemChange) => (
              <AccommodationForm value={a} onChange={onItemChange} />
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
            itemTitle={(c, i) => c.company || c.pickup_location || `Car rental ${i + 1}`}
            add={[{ label: "car rental", make: newCarRental }]}
            emptyLabel="No car rentals."
            renderItem={(c, _i, onItemChange) => <CarRentalForm value={c} onChange={onItemChange} />}
          />
        </div>
      </details>
    </div>
  );
}
