/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />
/// <reference types="vite-plugin-pwa/react" />

// Commit identity injected at build time (see vite.config.ts `define`).
declare const __COMMIT_HASH__: string;
declare const __COMMIT_DATE__: string;
declare const __REPO_URL__: string;

// Python glue loaded as a raw string and executed inside Pyodide.
declare module "*.py?raw" {
  const source: string;
  export default source;
}
