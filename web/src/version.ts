// The build's commit identity, baked in at build time (see vite.config.ts
// `define`) and shown in Options as "Current version". It auto-refreshes on every
// push to main: the GitHub Pages workflow rebuilds from the pushed commit, and
// the local pre-push hook stamps web/.commit-info.json (see .githooks/pre-push).

export const COMMIT_HASH: string = __COMMIT_HASH__;
export const COMMIT_DATE: string = __COMMIT_DATE__;
export const REPO_URL: string = __REPO_URL__;

/** GitHub URL of the commit this build was made from, or "" when unavailable
 * (no repo URL, or a local "dev" build) — in which case the hash isn't linked. */
export function commitUrl(): string {
  if (!REPO_URL || !COMMIT_HASH || COMMIT_HASH === "dev") return "";
  return `${REPO_URL}/commit/${COMMIT_HASH}`;
}

/** An ISO commit timestamp as "YYYY-MM-DD HH:MM" (local time), or "" if unknown.
 * Shared so the Options "Current version" line and the update-check notice date
 * a build the same way — they sit a click apart and are compared by eye. */
export function commitDateLabel(iso: string = COMMIT_DATE): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** The identity of the build currently **deployed**, as `version.json` states it. */
export interface DeployedVersion {
  hash: string;
  date: string;
}

/**
 * Ask the server which build is deployed (see `versionManifest()` in
 * vite.config.ts). `null` when the question can't be answered — offline, or a
 * host that doesn't serve the file — which is a third outcome the caller must
 * report as such rather than fold into "up to date".
 *
 * `no-store` **plus** a cache-busting query: the first defeats the HTTP cache,
 * the second any intermediary that ignores it. The file is kept out of the
 * service-worker precache for the same reason.
 */
export async function fetchDeployedVersion(): Promise<DeployedVersion | null> {
  try {
    // `BASE_URL` is the app's one deployment knob (GitHub Pages serves it from
    // a subpath), so build the URL from it like every other bundled asset.
    const url = `${import.meta.env.BASE_URL}version.json?t=${Date.now()}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    const j = (await res.json()) as { hash?: unknown; date?: unknown };
    if (typeof j.hash !== "string" || !j.hash) return null;
    return { hash: j.hash, date: typeof j.date === "string" ? j.date : "" };
  } catch {
    return null;
  }
}
