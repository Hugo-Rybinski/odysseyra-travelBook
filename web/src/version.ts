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

/** The commit timestamp as "YYYY-MM-DD HH:MM" (local time), or "" if unknown. */
export function commitDateLabel(): string {
  if (!COMMIT_DATE) return "";
  const d = new Date(COMMIT_DATE);
  if (Number.isNaN(d.getTime())) return COMMIT_DATE;
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
