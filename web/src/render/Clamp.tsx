import {
  createContext,
  useContext,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useT } from "../i18n";
import { linkifyProse } from "./contact";

// Whether long descriptions are truncated (with a "Show more" toggle) or shown
// in full. Provided by <Book> from the app-level display option; defaults to
// truncated. Kept in context so every description renders the same way without
// threading the flag through the whole day/activity tree.
const ClampContext = createContext(true);
export const ClampProvider = ClampContext.Provider;

// A description paragraph. When truncation is on it clamps to LINES lines and
// offers a "Show more" / "Show less" toggle — but only when the text actually
// overflows those lines. `className` carries the original styling hook
// (cover-summary / day-intro / desc), so the look is unchanged.
//
// `trailing` is inline content appended **inside** the text flow, after the last
// word — the guidebook pill. It therefore sits at the end of the final visible
// line, and is clipped along with the text when the paragraph is clamped (the
// "Show more" toggle brings it back).
//
// This is also the one seam every piece of prose the book prints goes through —
// the cover summary, a day's intro, an activity's description, a booking's note,
// the stay bar's — so it is where a phone number or an email address written
// *inside* the text becomes tappable (`contact.tsx`'s `linkifyProse`). Doing it
// here rather than at each of the eleven call sites is what keeps the rule
// single, and it composes with the clamp for free: the truncation is CSS
// (`-webkit-line-clamp`), so the full text is always in the DOM and a link in
// the clipped tail simply comes back with "Show more".
export function Clamp({
  text,
  className,
  trailing,
}: {
  text: string;
  className?: string;
  trailing?: ReactNode;
}) {
  const clamp = useContext(ClampContext);
  const t = useT();
  const ref = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [overflowing, setOverflowing] = useState(false);

  const clamped = clamp && !expanded;

  useLayoutEffect(() => {
    if (!clamp) {
      // option turned off (or never on): show full text, no toggle
      setExpanded(false);
      setOverflowing(false);
      return;
    }
    if (expanded) return; // keep the toggle visible so it can collapse again
    const el = ref.current;
    if (el) setOverflowing(el.scrollHeight - el.clientHeight > 1);
  }, [text, clamp, expanded]);

  return (
    <div className={className}>
      <div ref={ref} className={`clamp-text${clamped ? " clamped" : ""}`}>
        {linkifyProse(text)}
        {trailing}
      </div>
      {clamp && (overflowing || expanded) && (
        <button type="button" className="clamp-toggle" onClick={() => setExpanded((e) => !e)}>
          {expanded ? t("Show less") : t("Show more")}
        </button>
      )}
    </div>
  );
}
