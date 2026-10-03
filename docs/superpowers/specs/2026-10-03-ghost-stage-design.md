# Push 25 — Ghost in the Machine: design contract

Written before implementation, so the result can be checked against a
contract instead of against my mood at 2am. Every "reject" below names a
real failure mode I could see in the current build.

## What this is

The elohim webapp exists to summon a ghost. Right now the ghost is a
**static JPEG in a tall page**: you scroll ~1600px past a header of
metadata before you reach a single control. The art is genuinely good; the
*presentation* of it is not yet. This push makes the ghost alive and the
app navigable.

## Non-negotiables (carry forward — these are the brand)

- Warm amber on deep void. Phosphor CRT. Occult-scientific, not occult-
  spooky. Reference point: a 1970s lab oscilloscope, not a Halloween prop.
- The ghost is a **function of the numbers**. Parry numbers, Pisot bounds,
  the sigil — the mathematics is the subject. Visual effects must not
  invent data the app did not compute.
- Dark is the brand default. Light is a deliberate parallel palette, not an
  inversion.
- Motion is decoration for state, never state itself. Nothing may reflow
  the document.
- No new dependencies. Vanilla JS + CSS + SVG + canvas.

## Problems measured in the current build

From a 1440×900 and 390×844 capture, plus DOM measurements:

1. **Wasted width.** The hero is a 480px vertical image centred in 1440px
   — roughly 950px of empty space either side. The viewport is the most
   expensive real estate on the page and it is not being used.
2. **The ghost does not move.** `hero-art.jpg` is a still. The only motion
   near it is a 12s mesh drift at 0.04 opacity, which reads as texture
   noise, not life.
3. **Navigation is 1600px down.** The tablist is at y=1596. On a laptop the
   user scrolls two screens to find the app.
4. **Mobile header is eight lines tall.** The meta row
   (`Gilbert Ryle… │ v0.3.0… │ v0.2.0 · elohim_enhanced… · py 3.12.7 ·
   pyodide`) wraps to a stack that occupies a third of the first screen
   before any content.
5. **Panels leave voids.** The SIGIL panel is a ~700px empty box reading
   "awaiting first run" — the largest object on screen is nothing.
6. **The header ghost is a smudge.** A 45×68px silhouette behind the seal
   badge; at that size it reads as a rendering artefact, not a character.

## Design contract

### Hierarchy

The page has one job: **summon, then work**. So the order is

    masthead (identity + status, compact, always visible)
      └── ghost stage (the animated entity — the focal point)
            └── nav rail (the six tools, always one click away)
                  └── panel (the work)

Tools must be reachable **without scrolling past the fold** on a 1280×800
laptop. The ghost may extend beyond the fold; the nav may not.

### The ghost

Three layers, back to front, so it reads as depth rather than as a GIF:

- **Field** (canvas) — data-motes rising out of the monitor stack, with
  phosphor persistence. Density and rise speed respond to nothing
  external; it must be calm.
- **Entity** (SVG) — the ghost itself. A layered construction: a body that
  breathes, a wisp trail that lags behind it, eyes that blink on a long
  irregular cycle, and tendrils that carry data upward.
- **Glass** (CSS) — scanlines, curvature, vignette, chromatic edge. Sells
  "this is being displayed on a phosphor tube" without touching the entity.

Rules:
- Breathing is slow (4–6s). The ghost is not anxious.
- Blink is **irregular** — a 7s base cycle with a long random-ish offset. A
  regular blink is the single fastest way to make a character uncanny in
  the wrong way.
- Nothing loops on a visible common divisor. 4s, 5s, 7s, 11s — so the
  composite never visibly restarts.
- The entity is **drawn**, not bitmap. Scales to any viewport, themeable via
  tokens, ~0 KB of network cost.

### Navigation

- Sticky masthead with the seal, theme toggle, and the six destinations.
- The tablist becomes a real nav rail with a **persistent active state**
  (the current tool is marked with `aria-current` and a visible rail
  indicator, not only colour).
- Icons + text, never icon alone.
- The first-run card must not overlap content and must be dismissible by
  keyboard.

### What to reject

| Reject | Because |
|---|---|
| Purple/indigo gradient hero | The AI default; this app has a real palette |
| The ghost as a looping video/GIF | 1.3MB+ of network for a fixed-size illusion; blocks paint |
| Parallax on scroll over the whole page | Motion sickness, and it fights the ghost's own motion |
| Neon glow on everything | The amber is precious; spend it on the ghost, not the chrome |
| Animating anything on hover except real controls | Motion must mean something |
| A skeleton screen that mimics the ghost | The app boots in ~160ms of DOM; a fake loader is theatre |

### Accessibility

- `prefers-reduced-motion: reduce` → ghost holds a still, composed frame.
  Not "faster", not "hidden" — still, and still good-looking.
- All motion is `transform`/`opacity` only.
- The ghost is `aria-hidden` and purely decorative. It must never carry
  information. (Real data lives in the panels, which is where it belongs.)
- Focus order unchanged: skip-link → nav → panel controls.
- Contrast ≥ 4.5:1 for body text in **both** themes.

### Performance budget

- Boot gate is `dom_loaded < 8000ms` (D-J21). The canvas field must not
  start until after first paint, and must idle when off-screen.
- Canvas: cap DPR at 2, pause via `IntersectionObserver` + `visibilitychange`.
- No layout thrash: read sizes once, never in the animation loop.

## Known cost to the test suite

A visual redesign will trip the Push 22 perceptual-hash gate (#78), whose
baseline is cached in `/tmp/elohim-screenshots/baseline.json`. That file is
**not** committed; the correct response is to delete the stale baseline and
let it regenerate, then report the new distances — not to loosen the
threshold until the new design passes.
