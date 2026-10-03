# ADR 0001 — Keep `index.html` monolithic through the Push 19–22 cycle

| Field | Value |
|---|---|
| Status | Accepted (Jev-confirmed, Phase 19) — re-evaluated end of Push 22, still Accepted |
| Date | 2026-10-03 |
| Decider | Jev (UX/code-review persona) |
| Trigger | Push 19 modernization kickoff |
| Supersedes | — |

## Context

`elohim-web/index.html` is 4,397 lines / 166 KB post-Push 18bc. The user's
modernization brief (Push 19–22) calls for a vector animation system, design
tokens, layout grid, and onboarding copy. The user asked Jev whether to split
`index.html` into smaller files (`index.html` + `assets/styles.css` + `app.js`
+ `<template>` partials) as part of this cycle.

## Options considered

**Option A — Keep monolith, extract `assets/*` only.**
Add `<link rel="stylesheet" href="assets/motion.css">` (and a future
`assets/design-tokens.css`, `assets/components.css`) to the head. Embed the
SVG mesh in a `<div class="motion-mesh-bg">` layer. Smoke tests still hit one
URL; Pyodide boot path remains byte-identical.

**Option B — Push 23 also splits `index.html`.**
Split into `index.html` + `assets/styles.css` + `app.js` + `<template>`
partials. Adds a separate audit + smoke pass. Smaller files but introduces a
new failure mode (cold-cache fetch of `app.js` before Pyodide boot).

## Decision

**Option A.** Defer the file split to a future push that lands after the
visual modernization has settled (likely Push 23 or later).

## Rationale

1. **Pyodide boot path byte-stability.** The inline `<script>` boot sequence
   has been hardened over 18 pushes. Splitting it into a separate `app.js`
   introduces a fetch-on-boot step that could regress cold-cache load. No
   public bug report says the current boot is slow (smoke #1 covers it).
2. **Jev historical pattern.** Pushes 11, 12.1, 12.2, and 18bc-polish all
   deferred optional refactors in favour of incremental ones. The user
   approved that judgment repeatedly. Continuing the pattern preserves the
   Jev style.
3. **Visual modernization is the stated priority.** A file split is invisible
   to the user; the motion system is highly visible. Prioritize visible work.
4. **Reversibility.** A future push can still split the file once the motion
   layer's structure is settled. Splitting early means re-splitting later.
5. **Threshold for re-evaluation.** `index.html` past ~5,500 lines OR a
   second bug report about cold-cache boot time → re-open this decision.

## Tradeoffs accepted

- `index.html` will grow to ~5,000 lines by end of Push 22. That remains
  within "monolith but readable" range.
- The `:root` design tokens stay inline in `index.html` until the eventual
  file split — even after Push 19's motion tokens get extracted to
  `assets/motion.css`. The `:root` block becomes a thin alias layer over
  the extracted tokens.
- `<style>` block in `index.html` grows from ~100 KB to ~110 KB as motion
  classes are inlined for first paint. Once the file split lands, this
  inlined block drops to ~5 KB.

## Follow-ups

- Push 19 motion tokens go to `assets/motion.css`, not `index.html`.
- Push 22 (or later) re-evaluates this ADR if `index.html` exceeds 5,500 lines
  or boot regression is reported.
- When the split eventually happens, Jev reviews the boot path change as a
  separate concern (this ADR does not pre-approve it).

## Re-evaluation — end of Push 22

The Push 22 modernization cycle closed without crossing the trigger.

| Signal | Threshold | Actual | Verdict |
|---|---|---|---|
| `index.html` line count | 5,500 | **5,024** | below — split stays deferred |
| Cold-cache boot regression | reported | none reported | below |

The plan projected ~4,748 lines; the real figure is 5,024. The gap is the
first-run card, status pill, help-tooltip CSS and JS, and the `HELP_TEXT`
dict — more than the ~200 lines originally budgeted, but still 476 lines of
headroom before the trigger. Growth rate is now ~240 lines per push
(4,490 → 5,024 across Pushes 20–22), so the next push or two could reach
5,500.

**ADR 0001 remains Accepted.** When the split does happen it will be
ADR 0002, targeting exactly two extracted files (`assets/styles.css` +
`app.js`) rather than a finer module split, and it must show a cold-cache
boot under 8 s.

## Decision record provenance

- Confirmed in conversation 2026-10-03 (post-Push 18bc-polish).
- User asked: "research jev docs and jev engineering to let it construct
  missing infrastructure and create a much moderner and vector animated web
  design with a more well designed layout and easy to understand web
  application." Refactor question routed to Jev via the modernization
  questionnaire (`ask jev` response, 2026-10-03 04:11 CEST).