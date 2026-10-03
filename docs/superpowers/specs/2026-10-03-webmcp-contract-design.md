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

### 4.6 Risk class is measured, not asserted

Because §3.6 shows side effects hide behind the bridge, the test harness
classifies empirically: snapshot `localStorage` before and after each
invocation and assert no delta for tools declared `pure`.

This is the design's most important consequence. A tool declared `pure` that
turns out to write state **fails the suite** and must be re-declared. The
declaration is a hypothesis; the state delta is the measurement.

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

**Playwright-based, launched with `--enable-features=WebMCPTesting`.**

The flag is the whole point. Without it, every assertion silently passes against
the polyfill and proves nothing — a green WebMCP suite that never enables the
flag is worse than no suite, because it manufactures false confidence.

The suite must:

1. Launch Chromium **with the flag**.
2. **Fail loudly** if `navigator.modelContext` is absent. Skipping to the
   polyfill is a failure, not a pass.
3. Assert `getTools()` returns exactly the expected N names.
4. Assert annotations and schema closure against the app's declared table
   (§3.5 — the browser cannot echo them).
5. Assert unknown fields are rejected at the handler (§3.4).
6. Assert `localStorage` deltas match declared risk (§4.6).

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

Nine assertions; six of them fail against current code, which is the honest
measure of remaining work.

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `WebMCPTesting` flag renamed/removed upstream | 🟡 | Suite fails loudly and names the flag; the failure is explicit, not silent |
| Chromium changes `getTools()` shape | 🟢 | Annotations asserted from our own table, not the browser's |
| `execute` signature changes | 🟡 | One call site; error surfaces on first registration in the suite |
| `forge_vision` non-determinism flakiness | 🟡 | Excluded from the default suite; runs behind a flag |
| Vault/marketplace stubs drift from real APIs | 🟡 | Stubs assert response *shape* only; documented as a test double |
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
