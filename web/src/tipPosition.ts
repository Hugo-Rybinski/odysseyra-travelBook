// Edge-aware positioning for the CSS `[data-tip]` hover tooltips. The bubble is
// a left-anchored `::after`; a trigger near the right edge of a narrow screen
// would push it off-screen. On pointer-over / focus we measure the trigger and
// toggle `tip-flip` — which right-anchors the bubble in CSS — whenever a
// left-anchored bubble wouldn't have room. (The bubble also wraps to multiple
// lines, capped to the viewport width, via its CSS max-width.)
const TIP_MAX = 260; // keep in sync with the tooltip max-width in index.css
const EDGE = 12; // keep this much clear of the viewport's right edge

function place(target: EventTarget | null): void {
  const el = (target as Element | null)?.closest?.("[data-tip]") as HTMLElement | null;
  if (!el) return;
  const rect = el.getBoundingClientRect();
  const roomRight = window.innerWidth - EDGE - rect.left;
  el.classList.toggle("tip-flip", roomRight < TIP_MAX);
}

// Capture phase so we still see events that inner controls stop bubbling.
document.addEventListener("pointerover", (e) => place(e.target), true);
document.addEventListener("focusin", (e) => place(e.target), true);
