import { Component, type ReactNode } from "react";

// Catches failures from the lazily-loaded interactive map — a rejected chunk
// import (offline, uncached) or a render error — and shows `fallback` (the
// static PNG) instead of crashing. `onError` lets the parent latch the failure
// so it keeps showing the static map until fresh geo arrives.
export class MapErrorBoundary extends Component<
  { fallback: ReactNode; onError?: () => void; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch() {
    this.props.onError?.();
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
