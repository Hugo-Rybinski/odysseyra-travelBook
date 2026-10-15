// The phone's compass, for the heading beam the interactive map draws round the
// "you are here" dot. Viewer-only, like the dot itself: paper has no heading.
//
// Two platforms, two dialects of the same event:
//   - iOS Safari gates it behind `DeviceOrientationEvent.requestPermission()`,
//     which must be called from inside a tap, and reports the heading ready-made
//     as `webkitCompassHeading` (degrees clockwise from north).
//   - Chrome on Android needs no prompt and fires `deviceorientationabsolute`,
//     whose `alpha` is counter-clockwise from north, hence `360 - alpha`.
// Both are measured off the device's top edge, so a phone held sideways adds
// the screen's own rotation. Anything else (desktop, Firefox's relative-only
// `deviceorientation`) yields no heading at all, and the caller draws no beam:
// a heading that might be relative to wherever the phone pointed at load would
// be worse than none.
//
// Magnetic declination (a few degrees across Europe and Central Asia) is
// ignored: it is well inside the ±10–20° a phone magnetometer manages anyway.

// Weight of each new reading in the running average. The raw stream is noisy
// and arrives up to 60 times a second; this settles a hand's tremor without
// lagging a deliberate turn by more than a few frames.
const SMOOTHING = 0.2;

interface OrientationWithCompass extends DeviceOrientationEvent {
  webkitCompassHeading?: number;
  webkitCompassAccuracy?: number;
}

type PermissionApi = { requestPermission?: () => Promise<"granted" | "denied"> };

function permissionApi(): PermissionApi | undefined {
  return (globalThis as { DeviceOrientationEvent?: PermissionApi }).DeviceOrientationEvent;
}

/** Whether reading the compass needs a permission prompt first (iOS). */
export function compassNeedsPrompt(): boolean {
  return typeof permissionApi()?.requestPermission === "function";
}

/**
 * Ask for the compass where the platform requires it (iOS). **Call it
 * synchronously from a tap handler** — WebKit refuses the prompt otherwise.
 * Resolves true where no permission is needed.
 */
export function requestCompass(): Promise<boolean> {
  const api = permissionApi();
  if (!api) return Promise.resolve(false);
  if (typeof api.requestPermission !== "function") return Promise.resolve(true);
  return api.requestPermission().then(
    (r) => r === "granted",
    (err) => {
      // A rejection (rather than "denied") means the request itself was
      // refused — no gesture, another prompt up — which is worth seeing in
      // Safari's Web Inspector, since the page otherwise just shows no beam.
      console.warn("compass permission request failed", err);
      return false;
    },
  );
}

function screenAngle(): number {
  const a = screen.orientation?.angle;
  if (typeof a === "number") return a;
  const legacy = (window as { orientation?: number }).orientation; // older iOS
  return typeof legacy === "number" ? legacy : 0;
}

/** The heading an event carries, in degrees clockwise from north, or null. */
function headingOf(e: OrientationWithCompass): number | null {
  let h: number | null = null;
  if (typeof e.webkitCompassHeading === "number" && !Number.isNaN(e.webkitCompassHeading)) {
    // iOS flags an uncalibrated compass with a negative accuracy.
    if (e.webkitCompassAccuracy != null && e.webkitCompassAccuracy < 0) return null;
    h = e.webkitCompassHeading;
  } else if (e.absolute && e.alpha != null) {
    h = 360 - e.alpha;
  }
  if (h == null) return null;
  return (((h + screenAngle()) % 360) + 360) % 360;
}

/**
 * Listen to the compass, calling `onHeading` at most once per frame with the
 * smoothed heading. Returns the function that stops it. Never calls back on a
 * device with no absolute compass.
 */
export function watchCompass(onHeading: (deg: number) => void): () => void {
  // Averaged as a unit vector, so 359° and 1° average to 0° rather than 180°.
  let x = 0;
  let y = 0;
  let primed = false;
  let frame = 0;

  const emit = () => {
    frame = 0;
    const deg = (Math.atan2(y, x) * 180) / Math.PI;
    onHeading((deg + 360) % 360);
  };
  const onEvent = (e: Event) => {
    const h = headingOf(e as OrientationWithCompass);
    if (h == null) return;
    const r = (h * Math.PI) / 180;
    if (!primed) {
      x = Math.cos(r);
      y = Math.sin(r);
      primed = true;
    } else {
      x += (Math.cos(r) - x) * SMOOTHING;
      y += (Math.sin(r) - y) * SMOOTHING;
    }
    if (!frame) frame = requestAnimationFrame(emit);
  };

  // Chrome fires both events; only the absolute one is north-referenced, so it
  // is taken alone where it exists. iOS has only the plain one.
  const type = "ondeviceorientationabsolute" in window ? "deviceorientationabsolute" : "deviceorientation";
  window.addEventListener(type, onEvent);
  return () => {
    window.removeEventListener(type, onEvent);
    if (frame) cancelAnimationFrame(frame);
  };
}
