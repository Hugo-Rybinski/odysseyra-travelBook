import type { ReactNode } from "react";

// A generic editor for an array of objects: each item is a card with a header
// (its title + move up/down + remove) and a body rendered by the caller. New
// items are added from one or more "Add" options (a single option → one button;
// several → a button per option, e.g. the six activity types).
export interface AddOption<T> {
  label: string;
  make: () => T;
}

export interface ArrayEditorProps<T> {
  items: T[];
  onChange: (next: T[]) => void;
  itemTitle: (item: T, index: number) => string;
  renderItem: (item: T, index: number, onItemChange: (next: T) => void) => ReactNode;
  add: AddOption<T>[];
  emptyLabel?: string;
  className?: string;
}

export function ArrayEditor<T>({
  items,
  onChange,
  itemTitle,
  renderItem,
  add,
  emptyLabel = "None yet.",
  className = "",
}: ArrayEditorProps<T>) {
  const replaceAt = (i: number, next: T) => {
    const copy = items.slice();
    copy[i] = next;
    onChange(copy);
  };
  const removeAt = (i: number) => {
    const copy = items.slice();
    copy.splice(i, 1);
    onChange(copy);
  };
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= items.length) return;
    const copy = items.slice();
    [copy[i], copy[j]] = [copy[j], copy[i]];
    onChange(copy);
  };

  return (
    <div className={`array-editor ${className}`}>
      {items.length === 0 && <p className="array-empty">{emptyLabel}</p>}

      {items.map((item, i) => (
        // <details> so a long list (many days/activities) can be collapsed. The
        // header controls live in <summary>; each stops propagation so clicking
        // move/remove doesn't also toggle the disclosure.
        <details className="array-item" key={i} open>
          <summary className="array-item-head">
            <span className="array-item-title">{itemTitle(item, i)}</span>
            <span className="array-item-controls">
              <button
                type="button"
                className="icon-btn"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  move(i, -1);
                }}
                disabled={i === 0}
                aria-label="Move up"
                data-tip="Move up"
              >
                ↑
              </button>
              <button
                type="button"
                className="icon-btn"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  move(i, 1);
                }}
                disabled={i === items.length - 1}
                aria-label="Move down"
                data-tip="Move down"
              >
                ↓
              </button>
              <button
                type="button"
                className="icon-btn danger"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  removeAt(i);
                }}
                aria-label="Remove"
                data-tip="Remove"
              >
                ✕
              </button>
            </span>
          </summary>
          <div className="array-item-body">{renderItem(item, i, (next) => replaceAt(i, next))}</div>
        </details>
      ))}

      <div className="array-add">
        {add.map((opt) => (
          <button
            key={opt.label}
            type="button"
            className="btn subtle"
            onClick={() => onChange([...items, opt.make()])}
          >
            + {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
