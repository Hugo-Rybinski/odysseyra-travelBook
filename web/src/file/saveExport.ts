// Save exported bytes to a file the user downloads — entirely client-side.

/** A filesystem-friendly slug from a trip title (fallback "travelbook"). */
export function slugify(name: string): string {
  const slug = name
    .normalize("NFKD") // decompose accents so the next pass drops the marks
    .replace(/\.json$/i, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "travelbook";
}

/** Trigger a download of `text` as `filename` (default MIME: JSON). */
export function downloadText(
  text: string,
  filename: string,
  mime = "application/json",
): void {
  downloadBytes(new TextEncoder().encode(text), filename, mime);
}

/** Trigger a download of `bytes` as `filename` (default MIME: PDF). */
export function downloadBytes(
  bytes: Uint8Array,
  filename: string,
  mime = "application/pdf",
): void {
  // Copy into a plain ArrayBuffer so the Blob type is unambiguous (a Uint8Array
  // may be typed as SharedArrayBuffer-backed, which Blob rejects).
  const buffer = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(buffer).set(bytes);
  const blob = new Blob([buffer], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoke on the next tick so the download has a chance to start.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
