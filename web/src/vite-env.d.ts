/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />
/// <reference types="vite-plugin-pwa/react" />

// Python glue loaded as a raw string and executed inside Pyodide.
declare module "*.py?raw" {
  const source: string;
  export default source;
}
