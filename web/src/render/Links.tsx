// A compact inline row of external links — Navigate (Google Maps), Website and
// Reservation — shared across the day timeline and the section cards. Renders
// nothing when there's nothing to link.
import { tr, type Lang } from "./format";

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
