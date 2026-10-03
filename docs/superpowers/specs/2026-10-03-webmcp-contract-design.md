# WebMCP contract hardening + full tool coverage — design spec

| Field | Value |
|---|---|
| Status | Draft for review |
| Date | 2026-10-03 |
| Author | Jev (audit/code-review) + implementation design |
| Repo | `elohim-web` |
| Supersedes | nothing |
| Related | ADR 0001 (file split), ADR 0002 (file split) |

## 1. Goal

Make `elohim-web` **agent-ready** rather than merely agent-*exposed*: ensure the
tools an external AI agent discovers are real, correctly shaped, honestly
annotated, input-validated, and covering the capabilities the UI already has.

Success is measurable, not rhetorical:

1. An agent loading the page in a WebMCP-capable browser discovers **25** tools
   via `modelContext.getTools()` — today it discovers **0**.
2. Every discovered tool is invocable and returns a real result.
3. No tool accepts a field outside its declared schema.
4. Every tool carries an honest `readOnlyHint`.
5. The suite **fails on today's code** and passes only when the above hold.

## 2. Non-goals

- Replacing the existing `window.elohimMcp` polyfill. It stays as a
  non-agent fallback for the in-page inspector and the smoke harness.
- Adding a hosted proxy, a server, or any third-party runtime dependency.
- Declaring WebMCP form-associated custom elements (`WebMCPFormAssociatedCustomElements`
  exists in the binary but is unused — out of scope).
- Changing the canonical seal or any Python bridge semantics.

## 3. Measured findings (evidence, not inference)

All findings below were produced by running the shipped app in real Chromium
1243. Numbers are reproducible; see §9.

### 3.1 The native path registers zero tools

```
FLAGS: ['--enable-features=WebMCPTesting']
  navigator.modelContext  = object   (class ModelContext)
  document.modelContext   = undefined
  window.modelContext     = undefined
  app-registered tools    = 0        ← getTools() returns []
```

`app.js:1854` guards on `window.modelContext`. That object is `undefined` in
every configuration tested, so the entire registration block is skipped. The
failure is **silent** — no console warning is emitted, because the `catch` that
would log is inside the block that never runs.

Consequence: all 13 tools are reachable only through the `window.elohimMcp`
polyfill, which no external agent runtime reads. The app advertises an agent
surface that does not exist.

### 3.2 The registration shape is wrong independently of the accessor

Registering with the member the app uses (`handler`) throws:

```
TypeError: Failed to execute 'registerTool' on 'ModelContext':
  Failed to read the 'execute' property from 'ModelContextTool':
  Required member is undefined.
```

The required member is **`execute`**. `app.js` passes `handler` in exactly one
place. Fixing only the accessor would move the failure from "silently nothing"
to "loud exception", not to working tools.

### 3.3 The published API guidance is inverted

The `browserbase-add-webmcp` skill states: *"current Chrome exposes
`document.modelContext` as a native `ModelContext` while
`navigator.modelContext` is `undefined`."*

Measurement contradicts this — `navigator.modelContext` is the live accessor and
`document.modelContext` is `undefined`. The correct fix is therefore to try
**all three**, ordered by observed reality, rather than to adopt any single
documented answer.

### 3.4 Schemas are not enforced at runtime

A tool registered with `additionalProperties: false` was invoked with
`{x:'hi', evil:'payload'}` and the call was **ACCEPTED**. Chromium does not
validate agent-supplied arguments. A closed discovery schema with a permissive
handler is not a closed contract — rejection must be implemented by us.

### 3.5 Risk hints do not round-trip

`getTools()` returns only `name`, `description`, `inputSchema`, `origin`,
`window`. `readOnlyHint` and `untrustedContentHint` are accepted on registration
but are **not readable back**. Annotation tests must therefore assert against
the application's own declared tool table, never against the browser's view.

### 3.6 Side effects cross the JS/Python boundary

`elohim_soul_import` is described as loading an envelope *"into localStorage.
Replaces the mirror arrays atomically"*, yet its JS `invoke` body contains no
`localStorage` reference — the write happens inside the Pyodide bridge.

A static scan of JS invoke bodies therefore reports **all 13 tools as pure**,
which is wrong for at least `soul_import` and `soul_keygen`. Risk class cannot
be established by reading the JavaScript; it has to be **measured** by
observing state across an invocation.

## 4. Design

### 4.1 Accessor resolution (fixes §3.1, §3.3)

One resolver, used everywhere, that records which accessor answered:

```js
// Order reflects measured reality (2026-10-03, Chromium 1243), not docs.
// The spec has moved between window/document/navigator across builds, so we
// try all three rather than trusting any single published answer.
function resolveModelContext() {
  const candidates = [
    ["navigator.modelContext", () => navigator.modelContext],
    ["document.modelContext",  () => document.modelContext],
    ["window.modelContext",    () => window.modelContext],
  ];
  for (const [label, get] of candidates) {
    try {
      const mc = get();
      if (mc && typeof mc.registerTool === "function") {
        return { mc, via: label };
      }
    } catch (_) { /* accessor may throw in exotic contexts */ }
  }
  return { mc: null, via: null };
}
```

The status line reports `via` — the accessor actually used — instead of a
hardcoded string. A truthful status line is the field-debugging tool here: when
a user's browser registers zero tools, the line tells us which accessor was
tried and which one answered.

### 4.2 Correct registration shape (fixes §3.2)

`handler:` → `execute:`, and the tool definition becomes the single source of
truth:

```js
const registered = WEBMCP_TOOLS.map((t) => {
  const derived = deriveAnnotations(t);            // §4.3
  mc.registerTool({
    name: t.name,
    description: t.description,
    inputSchema: { ...t.inputSchema, additionalProperties: false },  // §4.4
    ...derived.annotations,
    execute: async (args) => runTool(t, args),
  });
  return t.name;
});
```

`registerTool` is idempotent by name, so re-registration on hot reload replaces
rather than duplicates; no teardown handle is needed.

### 4.3 Risk classification, declared once and derived

Each tool declares a `risk` and whether its output carries untrusted content.
Annotations are **derived**, so a new tool cannot ship unannotated.

| `risk` | `readOnlyHint` | Meaning |
|---|---|---|
| `pure` | `true` | No application state change |
| `mutating` | `false` | Reversible state change |
| `consequential` | `false` | Irreversible, externally visible, or spends money — requires explicit commit |

`untrustedContentHint: true` whenever output includes user-controlled text
(invocations, plaintext, soul payloads, dataset strings).

**`elohim_marketplace_forge_commit` is the only `consequential` tool.** It spends
$0.02 through x402, so it is split from a non-charging preview (§4.5).

### 4.4 Closed schemas, closed twice

1. `additionalProperties: false` on every schema at registration.
2. A shared `assertKnownArgs(tool, args)` that rejects unknown keys **before**
   dispatch, because §3.4 proves the browser will not.

Rejection returns a structured error naming the offending field. This is the
control that makes "closed schema" true rather than decorative.

### 4.5 New tools (12), risk-tiered

Target total: **13 existing + 12 new = 25 tools.** This number is pinned here so
assertion #81 has a fixed expected value rather than a moving one.

| Tool | risk | Notes |
|---|---|---|
| `elohim_list_shards` | pure | lets an agent discover IDs before mutating |
| `elohim_create_shard` | mutating | |
| `elohim_shard_defy` | mutating | injects ghost-side perturbation |
| `elohim_shard_interact` | mutating | |
| `elohim_arena_run` | mutating | both shards, returns coherence verdict |
| `elohim_forge_vision` | mutating | **external** — pollinations.ai; slow, non-deterministic, rate-limited |
| `elohim_vault_tiers` | pure | |
| `elohim_vault_lookup` | pure | |
| `elohim_vault_list_public` | pure | |
| `elohim_vault_store` | mutating | writes to a **public** hosted list |
| `elohim_marketplace_forge_preview` | pure | cost estimate, no charge |
| `elohim_marketplace_forge_commit` | **consequential** | spends $0.02 |

`elohim_forge_vision` is registered but its description states the external
dependency plainly, so an agent can decide not to call it. We do not pretend a
non-deterministic third-party image API is a deterministic tool.

### 4.5.1 Verification tiers — the honest answer to "half of these are untestable"

The 12 new tools do **not** share a verification level, and presenting them as
one uniform batch would overstate what the suite proves. Each tool therefore
carries a `verification` level, recorded in the generated manifest and
**reported as three separate counts** by the suite:

| Tier | Tools | What is actually proven |
|---|---|---|
| `in-browser` | `list_shards`, `create_shard`, `shard_defy`, `shard_interact`, `arena_run` | Real end-to-end. These run in Pyodide with no backend. |
| `external` | `forge_vision` | Registered and schema-valid only. Non-deterministic third-party API, so invocation is opt-in and never asserted for output. |
| `stub` | `vault_tiers`, `vault_lookup`, `vault_list_public`, `vault_store`, `marketplace_forge_preview`, `marketplace_forge_commit` | Wiring, request shape, response parsing, and error paths — against a stub **we wrote**. The real service contract is not verified. |

**Ruling: adopt all 12, with tiers enforced and reported.** A green suite must
print `5 in-browser / 1 external / 6 stub` and never collapse them to "25/25
verified". The stub is a test double for *our* code, not a conformance claim
about Apify, x402, or the FastAPI vault — and the manifest says so in
`verification`, so an agent reading it is not misled.

This is the same discipline as the pHash threshold in Push 22: state what the
measurement covers, and refuse to let a green run imply more than it earned.

### 4.6 Risk class is measured, not asserted

Because §3.6 shows side effects hide behind the bridge, the test harness
classifies empirically: snapshot `localStorage` immediately before and after a
**single** invocation and assert no delta for tools declared `pure`.

This is the design's most important consequence. A tool declared `pure` that
turns out to write state **fails the suite** and must be re-declared. The
declaration is a hypothesis; the state delta is the measurement.

**Two conditions make the measurement valid**, both found the hard way during
investigation:

1. **Per-call isolation.** One tool per snapshot pair. Batching several calls
   between snapshots attributes the write to the wrong tool.
2. **Success must be asserted before the delta is interpreted.** A call the
   tool *rejects* performs no write, so a naive delta reads as "pure" — a
   false negative that would certify a tool as safe precisely when it never ran.
   The polyfill envelope signals success as
   `result.resultType === "complete"`, with the payload JSON inside
   `result.content[0].text`; it carries no `ok` key, so a test keying on
   `result.ok` silently reads every call as failed.

Measured baseline (isolated, one call each):

| Tool | Success | `localStorage` delta |
|---|---|---|
| `elohim_version` | complete | none — pure |
| `elohim_soul_keygen` | complete | none — pure (does not persist) |
| `elohim_lab_simplify` | complete | none — pure |

`elohim_soul_keygen` returning a secret key without persisting it is worth
noting: it is genuinely pure, and an earlier reading that implied otherwise
was an artefact of batching several calls into one measurement.

### 4.7 Agent-facing documentation

- `llms.txt` — plain-text orientation for an agent landing on the site.
- `tools.manifest.json` — **generated** from `WEBMCP_TOOLS` at build time by a
  small script, so it can never drift from the running table. No hand-maintained
  duplicate.
- `webmcp.e2e.json` — expected tool inventory for the validator.

### 4.8 Stub backends for the network-dependent tools

`vaultCall` and the marketplace call both read their base URL from a DOM input,
so a local stub server can stand in for both. This is what makes
`vault_store` and `marketplace_forge_commit` testable in CI rather than
permanently unverifiable — the concern raised during planning, now resolved by
construction rather than accepted.

## 5. Validation strategy

### 5.1 Two tiers, so the permanent gate carries no flag coupling

**Tier 1 — permanent gate: an injected spec-shaped `ModelContext`.** No
Chromium flag. Before page scripts run, the harness installs a fake
`navigator.modelContext` via `Object.defineProperty` on `Navigator.prototype`,
implementing `registerTool` / `getTools` / `executeTool`.

The fake is faithful, not a rubber stamp: it **throws the same error real
Chromium throws** when `execute` is missing —

> `Failed to execute 'registerTool' on 'ModelContext': Failed to read the
> 'execute' property from 'ModelContextTool': Required member is undefined.`

— so a tool using `handler` fails here exactly as it would in a real browser. A
permissive fake would accept the bug and certify it as fixed.

This tier tests everything under our control permanently: registration shape,
annotation derivation, schema closure, unknown-field rejection, and the
per-call `localStorage` risk measurement. It is immune to the flag being renamed.

Verified during design: with the fake installed and **no** Chromium flag, the
shipped app registers **0 tools** — the fake reproduces the production bug
exactly, which is what makes it a valid instrument.

**Tier 2 — opt-in conformance: the real runtime.** Run with
`--enable-features=WebMCPTesting`, assert the real browser agrees (real
`getTools()` returns all 25, a real invocation succeeds). Runs behind a harness
flag, not on every invocation.

### 5.2 Why this resolves the flag coupling

The original concern was that gating the whole suite on a Chromium internal
flag is fragile. It is — but only if the *permanent* gate depends on it. Under
two-tier testing the flag governs only the opt-in conformance check, so a
rename upstream turns Tier 2 red loudly while the suite that guards our own code
keeps running. The coupling is confined to the test that exists to detect
exactly that coupling.

### 5.3 Assertions

Tier 1 must:

1. Assert the fake was installed and the app registered against it.
2. Assert `getTools()` returns exactly the expected 25 names.
3. Assert annotations and schema closure against the app's declared table
   (§3.5 — the browser cannot echo them).
4. Assert unknown fields are rejected at the handler (§3.4).
5. Assert per-call `localStorage` deltas match declared risk (§4.6), asserting
   call success first.

Tier 2 additionally asserts real-runtime agreement.

Stagehand is **not** adopted. It adds a heavy toolchain dependency, and in this
Chromium build `page.tools()` would surface the same limited
`name/description/inputSchema/origin/window` shape. The §3 bugs were found by a
~20-line Playwright probe against real Chromium; no validator was needed.

This mirrors the discipline that caught the Push 22 blind regression gate: a
check that cannot fail guards nothing.

## 6. Test plan

| # | Assertion | Fails today? |
|---|---|---|
| #80 | `navigator.modelContext` present with the flag | ✅ fails |
| #81 | `getTools()` returns exactly 25 tools (13 + 12) | ✅ fails (0 today) |
| #82 | Every tool has `additionalProperties: false` | ✅ fails |
| #83 | Every tool declares a `risk`; annotations derive correctly | ✅ fails |
| #84 | Unknown field rejected by the handler | ✅ fails |
| #85 | `localStorage` delta matches declared risk for all tools | ⚠️ may fail (`soul_import`) |
| #86 | Each `pure` tool invokes and returns a real result | — |
| #87 | Stub-backed `vault_tiers` / `vault_store` round-trip | — |
| #88 | `marketplace_forge_preview` does not charge; `commit` does | — |
| #89 | `tools.manifest.json` matches the runtime table exactly | ✅ fails |
| #90 | Suite reports `5 in-browser / 1 external / 6 stub`, never a flat total | ✅ fails |

Ten assertions; seven of them fail against current code, which is the honest
measure of remaining work. #90 exists specifically to stop a future run from
collapsing three verification tiers into one reassuring number.

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `WebMCPTesting` flag renamed/removed upstream | 🟢 | Resolved by §5: the permanent gate (Tier 1) does not use the flag. Only the opt-in conformance test does, and it fails loudly by design. |
| Chromium changes `getTools()` shape | 🟢 | Annotations asserted from our own table, not the browser's |
| `execute` signature changes | 🟡 | One call site; error surfaces on first registration in the suite |
| `forge_vision` non-determinism flakiness | 🟡 | Excluded from the default suite; runs behind a flag |
| Vault/marketplace stubs drift from real APIs | 🟡 | Stubs assert response *shape* only, and every stub-backed tool is labelled `stub` in the manifest and reported separately (#90). A stub can never be mistaken for a conformance claim. |
| Tool count grows without docs | 🟢 | Manifest is generated, not hand-written |

## 8. Rollout

One Conventional Commit, `main` + `gh-pages`, force-pushed as in Pushes 20–23.
Rollback is `git revert` — the suite is expected to fail on the parent commit,
which is itself a check that the new assertions have teeth.

## 9. Reproducing the measurements

```bash
python3 -m http.server 8790            # from the repo root
```

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True,
        args=["--no-sandbox", "--enable-features=WebMCPTesting"])
    pg = b.new_page(); pg.goto("http://127.0.0.1:8790/")
    pg.wait_for_selector("#boot.hidden", state="attached", timeout=300000)
    for label, expr in (("navigator", "navigator.modelContext"),
                        ("document",  "document.modelContext"),
                        ("window",    "window.modelContext")):
        print(label, pg.evaluate(
            f"()=>{{const m={expr}; return m ? m.constructor.name : 'NoneType';}}"))
    print("app tools:", pg.evaluate(
        "async () => (await navigator.modelContext.getTools()).length"))
    b.close()
```

Expected on current code:

```
navigator ModelContext
document NoneType
window NoneType
app tools: 0
```

Verified against Chromium 1243 on 2026-10-03.
