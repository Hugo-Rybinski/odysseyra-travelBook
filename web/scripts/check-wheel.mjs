// Guard against shipping a stale in-browser wheel.
//
// The browser runs the `travelbook` *wheel* (built into public/py/), not the
// Python source — so if src/travelbook/ changes and the wheel isn't rebuilt,
// the app silently ships old Python (e.g. a missing constant → maps vanish).
// This fails the build loudly when the wheel is older than the source, telling
// you to run `npm run wheel`. Runs as a `prebuild`/`predev` step.
import { existsSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const srcDir = join(here, "..", "..", "src", "travelbook");
const pyDir = join(here, "..", "public", "py");

function newestMtime(dir) {
  let newest = 0;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "__pycache__") continue;
    const p = join(dir, entry.name);
    newest = Math.max(newest, entry.isDirectory() ? newestMtime(p) : statSync(p).mtimeMs);
  }
  return newest;
}

function newestWheelMtime() {
  if (!existsSync(pyDir)) return -1;
  const wheels = readdirSync(pyDir).filter((f) => f.startsWith("travelbook-") && f.endsWith(".whl"));
  return wheels.length ? Math.max(...wheels.map((f) => statSync(join(pyDir, f)).mtimeMs)) : -1;
}

const fail = (msg) => {
  console.error(`\n✖ ${msg}\n  Fix: run \`npm run wheel\`, then rebuild.\n`);
  process.exit(1);
};

if (!existsSync(srcDir)) {
  // No source tree to compare against (e.g. a wheel-only checkout) — skip.
  console.log("ℹ check-wheel: no src/travelbook to compare against, skipping.");
  process.exit(0);
}

const wheel = newestWheelMtime();
if (wheel < 0) fail("The in-browser travelbook wheel is missing.");
if (newestMtime(srcDir) > wheel) {
  fail("The in-browser travelbook wheel is STALE (src/travelbook changed after it was built).");
}
console.log("✓ check-wheel: wheel is up to date with src/travelbook.");
