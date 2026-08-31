import { useState } from "react";
import { useT } from "../../i18n";

// The `gpx` control: a hike's trail file, stored in the JSON as a base64 string.
//
// Nobody types base64, so this is a file picker rather than a text box — pick a
// .gpx and it is encoded into the draft, with a Clear button to drop it again.
// The file is gzipped first where the browser can (`CompressionStream`), which
// takes a recorded track from a few hundred KB down to a few tens; the Python
// decoder accepts either form (models/gpx.py), so a browser without it simply
// stores the plain encoding.
const MAX_BYTES = 8 * 1024 * 1024; // a sane ceiling: a day's track is ~1 MB

async function gzip(bytes: Uint8Array): Promise<Uint8Array> {
  const CS = (globalThis as { CompressionStream?: typeof CompressionStream }).CompressionStream;
  if (!CS) return bytes; // older browser — store the plain encoding
  const stream = new Blob([bytes as BlobPart]).stream().pipeThrough(new CS("gzip"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

/** Base64 of `bytes`, chunked — `String.fromCharCode(...all)` blows the stack
 *  on anything bigger than a few tens of thousands of arguments. */
function toBase64(bytes: Uint8Array): string {
  let binary = "";
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  return btoa(binary);
}

export function GpxField({
  id,
  value,
  onChange,
}: {
  id: string;
  value: unknown;
  onChange: (v: string | undefined) => void;
}) {
  const t = useT();
  const [error, setError] = useState("");
  const current = typeof value === "string" ? value : "";
  // The encoded length is what lands in the file, so that's the honest figure.
  const kb = Math.max(1, Math.round(current.length / 1024));

  const load = async (file: File | undefined) => {
    setError("");
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setError(t("That file is too large (over {mb} MB).", { mb: MAX_BYTES / 1024 / 1024 }));
      return;
    }
    try {
      const raw = new Uint8Array(await file.arrayBuffer());
      onChange(toBase64(await gzip(raw)));
    } catch {
      setError(t("That file could not be read."));
    }
  };

  return (
    <span className="edit-gpx">
      <input
        id={id}
        className="edit-gpx-file"
        type="file"
        accept=".gpx,application/gpx+xml,text/xml"
        onChange={(e) => {
          void load(e.target.files?.[0]);
          e.target.value = ""; // so picking the same file twice still fires
        }}
      />
      {current ? (
        <span className="edit-gpx-state">
          {t("GPX attached ({kb} KB encoded)", { kb })}
          <button type="button" className="edit-gpx-clear" onClick={() => onChange(undefined)}>
            {t("Clear")}
          </button>
        </span>
      ) : (
        <span className="edit-gpx-state muted">{t("No GPX attached")}</span>
      )}
      {error && <span className="edit-gpx-error">{error}</span>}
    </span>
  );
}
