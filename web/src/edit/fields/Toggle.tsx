// A boolean field's control: a switch, drawn *under* the field's label like
// every other control (a text input, a select) rather than beside it, and given
// the same height as a text input — the fields sit in a grid, so a bool laid out
// differently from its neighbours knocked the whole row out of alignment.
//
// The real checkbox stays in the DOM, visually hidden and immediately before the
// track it styles: keyboard focus, space-to-toggle, `htmlFor`/label clicks and
// screen-reader semantics are then the platform's, not ours. Used by FieldRow's
// `bool` kind and by CoordinateField's "hide on map".
export interface ToggleProps {
  id?: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  /** Accessible name, for the one caller whose label doesn't wrap the input. */
  label?: string;
}

export function Toggle({ id, checked, onChange, label }: ToggleProps) {
  return (
    <span className="edit-toggle-row">
      <input
        id={id}
        type="checkbox"
        className="edit-toggle-input"
        checked={checked}
        aria-label={label}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="edit-toggle" aria-hidden />
    </span>
  );
}
