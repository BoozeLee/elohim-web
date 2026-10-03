# elohim-web

A single-page browser deployment of the **elohim** monorepo. Pyodide runs the
real Python stack — `elohim_summoning` (stdlib math+sigil) and `elohim_enhanced`
(numpy-powered creative shard) — entirely client-side, so the canonical sha256
contract is verifiable in the browser itself, not just on a backend.

Deployed via GitHub Pages on `BoozeLee/elohim-web`. No servers, no build step.

## What ships here

| Path | What it is |
|---|---|
| `index.html` | The single-page app. Bootstraps Pyodide, fetches the Python source, exposes the API as `window.elohim.*`. 6 tabs: **awaken**, **create**, **arena**, **codex**, **lab**, **webmcp** (+ boot screen). |
| `py/elohim_summoning/` | The stdlib-only math+sigil instrument, vendored from the monorepo verbatim (11 modules). |
| `py/elohim_enhanced/` | The numpy-powered creative shard, vendored from the monorepo verbatim (10 modules). |
| `assets/motion.css` | Vector animation system (Push 19) — 11 keyframes + 10 utility classes + reduced-motion override. Loaded after the inline `<style>` block per Jev decision D-J3. |
| `assets/motion-mesh.svg` | Animated SVG mesh layer — 6 nodes + 10×6 grid + 4 connecting paths (SMIL primary, CSS fallback per D-J5). Referenced from `index.html` via `<use href="…#mesh">`. |
| `assets/design-tokens.css` | Design tokens + light/dark theme (Push 20) — semantic color/spacing/radius/typography/shadow tokens + `[data-theme="light"]` palette. Loaded BEFORE motion.css per D-J12. |
| `py/elohim_webapp/bridge.py` | The Pyodide bridge module: pure-Python functions that JS invokes via `pyodide.runPython`. Includes the `alien_codex` Xenomath forge. |
| `py/elohim_webapp/__init__.py` | Package marker. |
| `smoke.py` | Local Playwright smoke test — opens the app in headless Chromium, verifies the seal, exercises every public endpoint. |
| `dist/` | (Empty placeholder — the deploy repo doesn't ship a wheel. See `BoozeLee/elohim` for the PyPI-style wheel.) |

## Canonical seal

```
5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596
```

The boot screen calls `bridge.verify_seal()` immediately after loading Pyodide
and refuses to enable the SPA if the in-browser seal differs from this value.
A green "seal recorded" badge in the header indicates the tripwire passed.

## Architecture

```
   ┌──────────────────────────────────────────────────┐
   │ Browser (Chromium / Firefox / Safari)            │
   │ ┌────────────────────────────────────────────┐   │
   │ │ index.html (the SPA)                       │   │
   │ │   │                                        │   │
   │ │   ▼                                        │   │
   │ │ window.elohim.* ──► pyodide.runPython()    │   │
   │ │                       │                    │   │
   │ │                       ▼                    │   │
   │ │ ┌──────────────────────────────────────┐   │   │
   │ │ │ elohim_webapp.bridge                 │   │   │
   │ │ │   version / awaken / list_shards /   │   │   │
   │ │ │   create_shard / interact /          │   │   │
   │ │ │   set_temperature / defy / delete     │   │   │
   │ │ └──────────────────────────────────────┘   │   │
   │ │   │                                        │   │
   │ │   ├─► elohim_summoning (stdlib math+sigil) │   │
   │ │   └─► elohim_enhanced  (numpy shard)       │   │
   │ │                                            │   │
   │ │   localStorage ◄──── shard persistence     │   │
   │ │   MEMFS (/tmp/elohim-out) ◄── artifacts   │   │
   │ └────────────────────────────────────────────┘   │
   │                                                  │
   │ Pyodide runtime (CDN)        numpy (CDN)         │
   └──────────────────────────────────────────────────┘
```

### Storage

- **Shards** — persisted in browser `localStorage` under `elohim.shard.<id>`,
  one JSON key per shard. Same wire format as the server-side `state.py`
  serialiser; can round-trip with the FastAPI webapp.
- **Awaken artifacts** — written to Pyodide's in-memory MEMFS at
  `/tmp/elohim-out/<ts>-<safe_inv>/`. The SVG is read back as a string and
  rendered inline; the user can download it.
- **Awaken history** — last 100 invocations appended to
  `localStorage["elohim.awaken.history"]`.

### JS↔Python bridge

Every call goes through `bridge._invoke(name, args, kwargs)`, a tiny Python
dispatch helper. JS builds a kwargs JSON string, parses it with
`json.loads(...)` inside Python, and reads back the JSON-encoded return value.
This avoids PyProxy reference cycles and lets the surface evolve without
forcing JS to keep a fixed import list.

### Lazy vs eager numpy

Numpy and the seven `elohim_enhanced` submodules are loaded eagerly at boot
(not lazily on first Create-tab click). Pyodide 0.27.x's first
`loadPackagesFromImports` call from inside an event handler can hang; pulling
it out into the boot flow keeps the SPA responsive. The boot progress bar
shows the numpy load explicitly.

## How to run locally

```bash
cd elohim-web
/usr/bin/python3 -m http.server 8780
# open http://127.0.0.1:8780/ in any modern browser
```

For a CI smoke test:

```bash
/usr/bin/python3 -m playwright install chromium
/usr/bin/python3 smoke.py
```

The smoke test takes ~60 seconds (Pyodide wasm + stdlib + numpy download).
It verifies:

1. Boot completes without errors.
2. The in-browser seal matches the canonical constant.
3. `awaken("ELOHIM:AWAKEN")` returns the canonical seal + a valid SVG.
4. The Create tab loads (numpy available).
5. `createShard` returns a shard with weights `[5, 5]`.
6. `interact` runs and produces a `den_expansion` event on the first call.
7. `setTemperature`, `defy`, `listShards`, `deleteShard` all round-trip.

## Design tokens + light/dark theme (Push 20)

The webapp surfaces every color, spacing, radius, typography, and
shadow value as a named semantic token in
[`assets/design-tokens.css`](/home/kilisan/elohim-web/assets/design-tokens.css).
A `[data-theme="light"]` selector ships a daylight-tuned palette. A
sun/moon toggle button in the header flips themes; the choice persists
to `localStorage["elohim.theme"]` and the default falls back to system
`prefers-color-scheme`.

### Token inventory

| Group | Tokens |
|---|---|
| Semantic backgrounds | `--color-bg-0`, `--color-bg-1`, `--color-bg-2`, `--color-bg-card`, `--color-border`, `--color-border-glow` |
| Semantic foregrounds | `--color-fg-0`, `--color-fg-1`, `--color-fg-2`, `--color-fg-mute` |
| Semantic accents | `--color-accent`, `--color-accent-soft`, `--color-accent-glow`, `--color-teal`, `--color-teal-soft`, `--color-green`, `--color-red`, `--color-purple` |
| Spacing scale | `--space-1` (4px) … `--space-8` (64px) |
| Radius scale | `--radius-sm` (2px), `--radius-md` (3px), `--radius-lg` (6px) |
| Typography scale | `--type-xs` (11px) … `--type-3xl` (56px) |
| Shadows | `--shadow-1`, `--shadow-2`, `--shadow-3` |

Existing tokens (`--bg`, `--fg`, `--accent`, `--serif`, `--mono`, etc.)
are kept for backward compatibility; the semantic tokens are aliases
that reference them. When `[data-theme="light"]` flips, the existing
tokens change first; the semantic tokens follow via cascade.

### FOUC prevention

An inline `<script>` at the top of `<head>` runs *before* any
stylesheet loads. It reads `localStorage["elohim.theme"]`, falls
back to `prefers-color-scheme`, and sets `document.documentElement.dataset.theme`
synchronously. No flash of unstyled content is possible.

### Cascade order

```
inline <script> sets data-theme   [Push 20]
  ↓
assets/design-tokens.css           [Push 20]
  ↓
assets/motion.css                  [Push 19]
  ↓
inline <style>...                  [existing]
```

### Jev decision record (light theme)

The light theme is a **parallel palette tuned for daylight
legibility**, NOT a dark-palette inversion. The brand identity is
preserved — warm-amber-on-dark → warm-sepia-on-paper. All 13
foreground/background pairs verified ≥ 4.5:1 contrast (WCAG AA).
Locked values committed in `design-tokens.css`.

## Motion system (Push 19)

The webapp applies an expressive, lively motion system to the existing
"Ghost in the Machine" tone. The implementation is purely CSS + SVG — no
JavaScript animation libraries, no third-party bundles.

| Layer | File | What it does |
|---|---|---|
| Tokens + keyframes + utilities | [`assets/motion.css`](/home/kilisan/elohim-web/assets/motion.css) | 11 `@keyframes`, 10 utility classes (`.motion-fade-rise`, `.motion-glow-pulse`, `.motion-sigil-breathe`, `.motion-badge-shimmer`, `.motion-mesh-bg`, `.motion-tab-reveal`, `.motion-card-lift`, `.motion-draw-stroke`, `.motion-active-glow`, `.motion-spin-slow`), motion duration + easing variables (`--motion-fast`, `--motion-base`, `--motion-slow`, `--ease-standard`, `--ease-emphasized`, `--ease-decel`), and a reduced-motion override (`@media (prefers-reduced-motion: reduce)`). Jev audit block at top of file documents the design decisions (D-J1…D-J10). |
| Mesh background | [`assets/motion-mesh.svg`](/home/kilisan/elohim-web/assets/motion-mesh.svg) | 6 animated `<circle>` nodes + 10×6 `<line>` grid + 4 connecting `<path>`s, all with SMIL `<animate>` for opacity / `stroke-dashoffset`. CSS fallback for nodes via `.mesh-node` keyframe (D-J5). Container `.motion-mesh-bg` in `motion.css` caps opacity at 0.04 (D-J1) and applies the `motion-mesh-drift` translate animation. |

### Where motion is applied

| Element | Animation | Source |
|---|---|---|
| `<header h1>` | `motion-fade-rise` (entrance, 320 ms) | Inline CSS rule in `index.html` |
| `<span class="seal-mini">` (header seal) | `motion-badge-shimmer` (background-position sweep, 2 s loop) | Inline CSS rule on `header .seal-mini` |
| `#awaken-sigil` (Penrose sigil card) | `motion-sigil-breathe` (4 s opacity + scale loop) | New CSS rule in `index.html`; existing `sigil-rotate` on the inner `<svg>` is preserved |
| `.tab.active` | `motion-active-glow` (1.6 s opacity loop, 0.55 → 0.85 per D-J2) | Inline CSS rule on `.tab.active` |
| `.tab.loading .ready-dot` | `motion-spin-slow` (24 s rotate) layered with the existing `pulse` (1.1 s) | Inline CSS rule on `.tab.loading .ready-dot` |
| All `.card` elements | `motion-card-lift` on hover (160 ms translate + shadow) | CSS rule in `motion.css` |
| Body scanlines | Opacity `0.025` → `0.015` (D-J4) | Inline CSS rule on `body::before` |

### Reduced motion

`@media (prefers-reduced-motion: reduce)` is honored at two levels:
1. The existing global guard in `index.html:59–65` zeros out durations
   and iteration counts.
2. The motion.css reduced-motion override (D-J7) explicitly sets
   `animation: none !important; transition: none !important; transform:
   none !important; opacity: 1 !important` on every new utility class
   and on `.card` / `.card:hover`. Belt-and-braces — future contributors
   deleting one guard must not silently disable the layer.

### Jev decision record

The file-split question (whether to extract `index.html` into smaller
artifacts as part of this push) was decided by Jev as **defer** — full
rationale in [`docs/adr/0001-file-split.md`](/home/kilisan/elohim-web/docs/adr/0001-file-split.md).
The mesh SVG is the only asset extracted (per R-E3 in the plan risk
table), kept as a single source of truth at `assets/motion-mesh.svg`.

## How to deploy

Push to `main`. GitHub Pages serves the repo root as-is — no build step:

```bash
git push origin main
# Then in the GitHub web UI: Settings → Pages → Source: Deploy from branch → main / root
```

The first deploy takes ~30 seconds; subsequent deploys are atomic.

## Xenomath Agent Framework

The fifth tab (`codex`) is the first build target of a broader project we
call the **Xenomath Agent Framework** — an experimental framework that
searches across unfamiliar mathematical formalisms and retains only those
that improve defined tasks under reproducible evaluation.

The framework is *not* a claim that extraterrestrial mathematics exists,
and not an appeal to mystery. It is a structural response to one open
question: if we want agents that reason across representations — vectors,
graphs, symbolic expressions, geometric objects, probabilistic models,
dynamical systems, categorical morphisms — how do we keep them honest when
they invent something new?

### Scientific reframe

| Claim | Scientific status | Productive alternative |
|---|---|---|
| "This mathematics was supplied by extraterrestrials" | Unsupported; no verifiable evidence | Treat as speculative fiction or an unverified hypothesis |
| "Alien intelligence would use radically different mathematics" | Unknown; plausible as a thought experiment | Explore multiple valid formalisms without assuming their origin |
| "Mathematics must be universal" | Partly motivated by physical regularities, but representation and notation can vary | Test invariants, symmetries, compression, and predictive utility across representations |
| "The framework is advanced because it is unfamiliar" | Not sufficient | Demand performance, calibration, interpretability, and safety improvements over baselines |

The framework adopts SETI's epistemic discipline: extraordinary inputs
require independent confirmation before they influence system behaviour.
No confirmed extraterrestrial signal has been detected; any purportedly
novel mathematical signal from any source — human, machine, or claimed
"alien" — is treated the same way: *untrusted data* until it earns
verification.

### Representation pluralism

The core principle is **representation pluralism**: each problem is
solved under several valid mathematical languages, then the candidates
are ranked by a single competence objective:

```
(k*, π*) = arg max_{k, π} [ Q(x; R_k, π) − λ_C·C − λ_T·T − λ_R·R ]
subject to:  Verified(x, R_k, π) = 1
```

where `Q` is task quality, `C` is compute/financial cost, `T` is latency,
`R` is safety/reliability risk, and `Verified` is whether the candidate
passes formal, empirical, or human evaluation. The `λ`s trade off
competing concerns; the hard gate is verification.

For task `x`, the framework chooses representation `k` and solver policy
`π` only after verification — novelty without verification earns no
credit.

### Eight mathematical layers

The framework reasons over eight layers. Each one is real, well-studied
mathematics; "alien" is shorthand for *unfamiliar at first encounter*,
not *supernatural*.

1. **Invariant-first reasoning** — for a transformation group `G`, an
   invariant feature map `f` satisfies `f(g·x) = f(x)` for all `g ∈ G`.
   The framework's first question is "which transformations preserve
   this task's essential structure?"
2. **Hypergraph knowledge structures** — ordinary graphs represent
   pairwise relations; hypergraphs admit `e ⊆ 2^V`, so a single claim
   `{claim, evidence, assumptions, tool_trace, verifier_result}` can be
   one edge with audit-ready provenance.
3. **Sheaf-style local-to-global consistency** — for agents observing
   regions `U_i` with local solutions `s_i ∈ F(U_i)`, require
   `s_i|_{U_i ∩ U_j} = s_j|_{U_i ∩ U_j}`. Conflicts become first-class
   objects, not averaged away.
4. **Non-Euclidean latent geometry** — Riemannian metric tensor
   `g_x`, geodesics, and path cost
   `L(γ) = ∫ γ̇ᵀ g_{γ(t)} γ̇ dt`. Hyperbolic space for hierarchies,
   curved regions for constraints.
5. **Category-theoretic interface design** — every agent or tool is a
   morphism `f : A → B` between typed artifacts. Two operations compose
   only if their types align; `UserRequest → TaskSpec → EvidenceLedger →
   ImplementationPlan → VerifiedArtifact` is the canonical pipeline.
6. **Information geometry and novelty detection** — KL divergence,
   Mahalanobis distance, and a multi-objective score:
   `α·PredictiveGain + β·CompressionGain + γ·Novelty − δ·ComputeCost − ε·VerificationFailure`.
7. **Algorithmic-information perspective** — minimum description length:
   `L(D, M) = L(M) + L(D | M)`. Novel representations earn value when
   they explain task data more compactly than the baselines.
8. **Constrained evolutionary search** — candidates live in a sandboxed
   population, scored by Pareto-optimal `Q − C − T − V`, and only enter
   the running system if they pass `Safety ≥ s_min`, `Groundedness ≥ g_min`,
   `Reliability ≥ r_min`.

The first build target is an *Advanced Mathematics Discovery Lab* —
exactly what the codex tab is. It takes a scientific, engineering, or
software-design problem, derives it in several representations, runs
each through approved methods, measures accuracy / validity / complexity /
robustness / calibration, identifies invariants and contradictions, and
emits the report contract below.

### Output contract

The codex tab returns:

```jsonc
{
  "problem_definition":          // what we're solving
  "assumptions":                 // what we're allowed to assume
  "candidate_formalisms":        // which representations we tried
  "methods":                     // how each was derived
  "results": {                   // the five representations + derivations
    "vector": [32 floats],         // R^vector  (L2-normalised)
    "negabinary_int": int,         // R^symbolic (Horner round-trip verified)
    "negabinary_digits": [32 bits],
    "gaussian": [μ, σ],            // R^geometric (Penrose colour source)
    "quaternion": [w, x, y, z],    // R^geometric (norm preserved)
    "lwe_A": [[4×4 mod 256]],      // R^probabilistic
    "lwe_secret": [4 ints], "lwe_error": [4 ints],
    "lwe_public_b": [4 ints], "lwe_residual_matches_error": bool,
    "categorical": {...}           // R^categorical (morphism)
  },
  "benchmark_comparison":       // each rep vs the others
  "verification_record": {      // what passed, what failed
    "codex_seal": "sha256(...)", // what we stand behind
    "encrypted_seal": "xor-pair", // symmetrical recovery proves integrity
    "xor_pair_check_ok": bool,
    ...
  },
  "limitations"                  // what the artifact cannot do
}
```

The boot tripwire `verify_seal_multi` runs `alien_codex("ELOHIM:AWAKEN")`
and asserts `overall_validity` ∧ `xor_pair_check_ok`. The header badge
shows `4/4 checks ✓` when all four instruments agree — three awaken
calls plus one codex.

### SETI-style validation ladder

The `validate_codex` checks mirror SETI's protocol for handling
suspected signals of unknown origin:

1. **Preserve the raw artifact.** `codex_seal = sha256(composite)` and
   `encrypted_seal = codex_seal ⊕ SHAKE256(codex_seal).digest(32)` are
   both reported; either can be re-derived from the other.
2. **Check mundane causes first.** The negabinary forward Horner recovery
   (not the obvious reversed variant), the LWE residual equality, the
   quaternion unit norm — these are the trivial consistency tests that
   catch transcription errors before exotic claims are entertained.
3. **Independent replication.** XOR-pair recovery proves the seal pair
   round-trips symmetrically: `codex_seal ⊕ encrypted_seal ⊕ SHAKE256(codex_seal)` returns
   to itself on any Python ≥ 3.10.
4. **Formal parsability.** Each representation parses back to its
   source field (negabinary recovers to the original int; quaternion
   norm is preserved; LWE residual equals the noise vector; Penrose
   SVG is well-formed XML).
5. **Internal consistency.** Quaternion unit norm check, LWE residual
   zero check, negabinary forward Horner recovery.
6. **External predictive power.** Out of scope here (would require a
   held-out task); deferred to a future lab target.
7. **Adversarial review.** The smoke suite fires 23 assertions against
   the public endpoint; failure here breaks CI.
8. **Sandbox integration.** The codex is a read-only experimental
   module — it never writes to disk or mutates a shard.
9. **Benchmark comparison.** The five representations are reported side
   by side; novelty without agreement earns no priority.

### Safety principle

The single rule the rest of the framework must respect:

```
Novel output  ⇏  trusted output
```

Instead:

```
Trusted output = novel or conventional output
                 + reproducible validation
                 + provenance
                 + independent checks
```

This is the bar the codex tab clears today: the artifact is reproducible
on any Python ≥ 3.10, the seal is recomputed in browser, and the
encrypted seal pair round-trips through `codex_seal ⊕ SHAKE256(codex_seal)`
to confirm integrity.

## Author

Kiliaan vanvoorder — `bakerstreetbandit@zohomail.eu`

Source: [`BoozeLee/elohim`](https://github.com/BoozeLee/elohim) (monorepo)