import { useCallback, useState } from "react";

// A tiny undo/redo stack for the edit draft (P6). `set` records the previous
// state on the past stack and clears the redo (future) stack; `reset` replaces
// the draft and clears all history (used when a new file is loaded). The past
// stack is capped so a long editing session can't grow memory unbounded.
const CAP = 100;

interface HistoryState<T> {
  present: T | null;
  past: T[];
  future: T[];
}

export interface DraftHistory<T> {
  draft: T | null;
  set: (next: T) => void;
  reset: (next: T | null) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

export function useDraftHistory<T>(initial: T | null): DraftHistory<T> {
  const [state, setState] = useState<HistoryState<T>>({
    present: initial,
    past: [],
    future: [],
  });

  const set = useCallback((next: T) => {
    setState((s) => {
      if (s.present === null) return { present: next, past: [], future: [] };
      const past = [...s.past, s.present];
      if (past.length > CAP) past.splice(0, past.length - CAP);
      return { present: next, past, future: [] };
    });
  }, []);

  const reset = useCallback((next: T | null) => {
    setState({ present: next, past: [], future: [] });
  }, []);

  const undo = useCallback(() => {
    setState((s) => {
      if (s.past.length === 0) return s;
      const present = s.past[s.past.length - 1];
      const future = s.present === null ? s.future : [s.present, ...s.future];
      return { present, past: s.past.slice(0, -1), future };
    });
  }, []);

  const redo = useCallback(() => {
    setState((s) => {
      if (s.future.length === 0) return s;
      const present = s.future[0];
      const past = s.present === null ? s.past : [...s.past, s.present];
      return { present, past, future: s.future.slice(1) };
    });
  }, []);

  return {
    draft: state.present,
    set,
    reset,
    undo,
    redo,
    canUndo: state.past.length > 0,
    canRedo: state.future.length > 0,
  };
}
