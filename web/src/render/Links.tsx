// A compact inline row of external links — Navigate (Google Maps), Website and
// Reservation — shared across the day timeline and the section cards. Renders
// nothing when there's nothing to link.
import { Fragment, type ReactNode } from "react";

import { tr, type Lang } from "./format";
import { navUrl, useMapProvider } from "./nav";

export function Links({
  lang,
  website,
  reservation,
  className = "link-row",
}: {
  lang: Lang;
  website?: string;
  reservation?: string;
  className?: string;
}) {
  const items = [
    website ? { label: tr(lang, "website"), href: website } : null,
    reservation ? { label: tr(lang, "reservation"), href: reservation } : null,
  ].filter((x): x is { label: string; href: string } => x !== null);

  if (!items.length) return null;
  return (
    <p className={className}>
      {items.map((l) => (
        <a key={l.label} className="link" href={l.href} target="_blank" rel="noreferrer">
          {l.label}
        </a>
      ))}
    </p>
  );
}

// A row's action links — `(Navigate)` and a GPX download / build — as **one**
// inline-block, so a line break falls *before* the pair rather than between its
// members. They answer the same question about the same place, and split across
// two lines they read as two unrelated links. The PDF has the same rule where it
// can: its VIA row measures the whole tail (figures, off-road pill, Navigate)
// and moves it to a second line as a unit.
//
// Grouping also settles their vertical alignment. Inside a flex row (the VIA
// list) each link is otherwise a flex item of its own — and a `<button>` centres
// its content in the stretched item's box where an `<a>` does not, so the two
// labels sat a few pixels apart whenever the row was taller than its text (which
// a pinned leg's discs make it). As one item they lay out as ordinary inline
// text on a shared baseline, and the group aligns as a whole.
export function LinkGroup({
  children,
  sep = "  ·  ",
  className = "",
}: {
  children: ReactNode[];
  // The text between two links. The chips line dot-separates like its other
  // parts; the VIA row passes "" and spaces them in CSS, matching its own gap.
  sep?: string;
  className?: string;
}) {
  const items = children.filter(Boolean);
  if (!items.length) return null;
  return (
    <span className={["link-group", className].filter(Boolean).join(" ")}>
      {items.map((c, i) => (
        <Fragment key={i}>
          {i > 0 ? sep : ""}
          {c}
        </Fragment>
      ))}
    </span>
  );
}

// An inline "Navigate" link, appended to a detail/meta line (or a title), the
// way the PDF places it — distinct from the Website/Reservation row.
export function NavLink({ lang, href }: { lang: Lang; href?: string }) {
  if (!href) return null;
  return (
    <a className="link nav-inline" href={href} target="_blank" rel="noreferrer">
      ({tr(lang, "navigate")})
    </a>
  );
}

// The address text itself, made clickable — it navigates by the *address string*
// (never coordinates). This complements the coordinate-based Navigate link: when
// an object has both a coordinate and an address, Navigate goes to the exact
// point while the address stays clickable as a search by name. Plain text when
// no maps URL can be built.
export function AddressLink({ address }: { address?: string | null }) {
  const provider = useMapProvider();
  const text = (address ?? "").trim();
  if (!text) return null;
  const href = navUrl(provider, null, text);
  if (!href) return <>{text}</>;
  return (
    <a className="link addr-link" href={href} target="_blank" rel="noreferrer">
      {text}
    </a>
  );
}
