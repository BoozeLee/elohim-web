# WebMCP Contract Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make elohim-web discoverable by real AI agents — 25 tools visible via `modelContext.getTools()` instead of the current 0 — with honest risk annotations, closed schemas, and a test harness that fails today.

**Architecture:** A single `WEBMCP_TOOLS` table stays the source of truth, now carrying `risk` and `verification` per tool; annotations are *derived* from `risk` so a new tool cannot ship unannotated. A resolver tries all three ModelContext accessors in measured order. Validation is two-tier: a permanent gate using an injected spec-shaped fake (no Chromium flag), plus an opt-in conformance test against the real runtime.

**Tech Stack:** Vanilla JS (no build step, ES modules), Playwright (Python), stdlib `http.server` for stubs. **No new third-party dependencies.**

**Spec:** [`docs/superpowers/specs/2026-10-03-webmcp-contract-design.md`](/home/kilisan/elohim-web/docs/superpowers/specs/2026-10-03-webmcp-contract-design.md)

## Global Constraints

- **No new third-party dependencies.** Pure CSS/SVG/vanilla JS + Playwright + stdlib only. This has held across Pushes 19–23.
- **The canonical seal `5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596` must never change.** It appears 4× today (1 in `index.html`, 3 in `app.js`) — that count must remain 4.
- **Test convention: plain `python3 smoke.py` with bare `assert`.** There is no `tests/` directory and no pytest. Do not introduce one.
- **Every tool name is `elohim_<verb_noun>`, snake_case, prefixed.** Target total exactly **25** (13 existing + 12 new).
- **Every schema sets `additionalProperties: false`** and every handler rejects unknown fields. The browser does not enforce this (spec §3.4).
- **Risk levels are `pure` | `mutating` | `consequential`; verification levels are `in-browser` | `external` | `stub`.**
- **The `window.elohimMcp` polyfill is retained**, not replaced — the in-page inspector and smoke harness depend on it.
- **Per-push Conventional Commit**, one commit, pushed to both `main` and `gh-pages` (force-push `gh-pages`), as in Pushes 20–23.

## Review Focus

Five input classes the spec implies that no assertion naturally covers. Each has a test pinned to its owning task.

1. **A tool declared `pure` that actually writes state.** Side effects hide inside the Pyodide bridge — `elohim_soul_import`'s JS invoke body has no `localStorage` reference yet its description says it replaces local state. Pinned in Task 3.
2. **A tool that rejects the call reads as side-effect-free.** A rejected call writes nothing, so a naive before/after delta certifies a broken tool as `pure`. Pinned in Task 3.
3. **A browser that moves `ModelContext` to a different object again.** The spec has already moved `window` → `document` → `navigator` across builds. Pinned in Task 2.
4. **A network tool called with its backend down.** Must return a structured error, not hang or half-apply. Pinned in Task 7.
5. **An agent calling `elohim_marketplace_forge_commit` twice.** Double-charging is the one genuinely irreversible action in the tool set. Pinned in Task 7.

---

### Task 1: WebMCP probe harness (the instrument)

Build the measuring device before the thing it measures — if the instrument is wrong, every later "pass" is meaningless.

**Files:**
- Create: `webmcp_probe.py`
- Modify: `smoke.py` (import only, no assertions yet)

**Interfaces:**
- Consumes: nothing (first task)
- Produces:
  - `class ModelContextProbe:` — installs the fake, launches, exposes `page`
  - `ModelContextProbe.__init__(self, *, real_runtime: bool = False, fake_target: str = "navigator", url: str = DEFAULT_URL)`
    — `fake_target` selects which object the fake is installed on, so the
    resolver's fallbacks can each be exercised independently (Task 2 #80b)
  - `ModelContextProbe.__enter__(self) -> ModelContextProbe`
  - `ModelContextProbe.__exit__(self, *exc) -> None`
  - `launch_args(real_runtime: bool) -> list[str]`
  - `FAKE_MC_SCRIPT: str` — the injected JS, templated on `fake_target`
  - `DEFAULT_URL: str` — `"http://127.0.0.1:8790/"`

- [ ] **Step 1: Write the failing self-test in `webmcp_probe.py`**

A module-level self-check that the fake is faithful. It must prove the fake *rejects* the bug the spec found — a permissive fake would certify the bug as fixed.

```python
def test_fake_rejects_handler_instead_of_execute():
    with ModelContextProbe() as p:
        raised = p.page.evaluate("""() => {
          try {
            navigator.modelContext.registerTool({
              name: 'x', description: 'x',
              inputSchema: {type: 'object', properties: {}},
              handler: async () => ({content: []}),      // wrong member
            });
            return null;
          } catch (e) { return String(e.message); }
        }""")
        assert raised is not None, "fake accepted `handler` — it is a rubber stamp"
        assert "execute" in raised and "Required member is undefined" in raised
```

- [ ] **Step 1b: Write the second self-test — the fake lands on the requested target**

```python
def test_fake_lands_on_requested_target():
    for target in ("navigator", "document", "window"):
        with ModelContextProbe(fake_target=target) as p:
            got = p.page.evaluate(
                f"() => !!{target}.modelContext")
            assert got, f"fake not installed on {target}"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -c "import webmcp_probe as w; w.test_fake_rejects_handler_instead_of_execute()"`
Expected: FAIL with `NameError: name 'ModelContextProbe' is not defined`

- [ ] **Step 3: Implement `webmcp_probe.py`**

`FAKE_MC_SCRIPT` must install a fake on `Navigator.prototype` implementing `registerTool` / `getTools` / `executeTool`. The `registerTool` body must raise this **exact** message when `execute` is missing — it is copied verbatim from real Chromium and is the whole reason the fake is trustworthy:

```
Failed to execute 'registerTool' on 'ModelContext': Failed to read the 'execute' property from 'ModelContextTool': Required member is undefined.
```

`launch_args(real_runtime=False)` returns `["--no-sandbox"]`. When `real_runtime=True` it appends `"--enable-features=WebMCPTesting"`. `__enter__` starts `sync_playwright()`, launches, and installs `FAKE_MC_SCRIPT` via `page.add_init_script` **only when** `real_runtime` is False. `__exit__` closes browser and playwright.

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 -c "import webmcp_probe as w; w.test_fake_rejects_handler_instead_of_execute()"`
Expected: PASS (no output, exit 0)

- [ ] **Step 5: Verify the fake reproduces the production bug**

Run: `python3 -m http.server 8790 &` then a short probe asserting the *shipped* app registers 0 tools against the fake.
Expected: `0` — this is the load-bearing check. A fake that reported non-zero would be measuring something other than the bug.

- [ ] **Step 6: Commit**

```bash
git add webmcp_probe.py smoke.py
git commit -m "test(webmcp): spec-shaped ModelContext probe harness (Tier 1)"
```

---

### Task 2: Accessor resolution + `execute` registration shape

Fixes the two blocking bugs from spec §3.1 and §3.2.

**Files:**
- Modify: `app.js:1852-1871` (the `window.modelContext` registration block)

**Interfaces:**
- Consumes: `webmcp_probe.launch_args`, `ModelContextProbe`
- Produces:
  - `resolveModelContext() -> {mc: ModelContext|null, via: string|null}` in `app.js` (module scope)
  - `runTool(tool, args) -> Promise<any>` in `app.js` (module scope)

- [ ] **Step 1: Write the failing assertion in `smoke.py` (#80, #81)**

```python
# #80 — navigator.modelContext is the live accessor, and the app registers
# against it. Today the app guards on window.modelContext, so this is 0.
probe = ModelContextProbe()  # fake, no flag
with probe as p:
    p.page.goto(DEFAULT_URL)
    p.page.wait_for_selector("#boot.hidden", state="attached", timeout=300000)
    via = p.page.evaluate("() => window.__elohimWebmcpVia")
    assert via == "navigator.modelContext", f"resolver chose {via!r}"
    names = p.page.evaluate(
        "async () => (await navigator.modelContext.getTools()).map(t => t.name)")
    assert len(names) == 13, f"expected the 13 existing tools, got {len(names)}: {names}"
```

- [ ] **Step 1b: Write the Review Focus #3 test — the accessor moved again**

This is the test that stops the bug coming back. The accessor has already moved
`window` → `document` → `navigator` across builds, so a resolver that checks
only one candidate will silently register 0 tools in the next browser that
moves it again. Pin all three fallbacks:

```python
# #80b — Review Focus #3. The resolver must survive the accessor moving.
# Install the fake on `document` only, so navigator.modelContext is absent
# and the resolver has to fall through to the next candidate.
with ModelContextProbe(fake_target="document") as p:
    p.page.goto(DEFAULT_URL)
    p.page.wait_for_selector("#boot.hidden", state="attached", timeout=300000)
    via = p.page.evaluate("() => window.__elohimWebmcpVia")
    assert via == "document.modelContext", \
        f"resolver did not fall back to document: got {via!r}"
    n = p.page.evaluate(
        "async () => (await document.modelContext.getTools()).length")
    assert n == 13, f"fell-back registration produced {n} tools, expected 13"

# And again on `window` — the accessor the app used before this fix.
with ModelContextProbe(fake_target="window") as p:
    p.page.goto(DEFAULT_URL)
    p.page.wait_for_selector("#boot.hidden", state="attached", timeout=300000)
    assert p.page.evaluate("() => window.__elohimWebmcpVia") == "window.modelContext"
```

This requires `ModelContextProbe.__init__` to accept
`fake_target: str = "navigator"`, which Task 1 must provide.

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 smoke.py --skip-vault`
Expected: FAIL at #80 — `resolver chose None` (today `window.__elohimWebmcpVia` does not exist)

- [ ] **Step 3: Implement `resolveModelContext()` and `runTool()` in `app.js`**

Try all three accessors in the order the spec pins, returning the first with a callable `registerTool`, and record which one answered in `window.__elohimWebmcpVia`:

```
navigator.modelContext  →  document.modelContext  →  window.modelContext
```

Wrap each in try/catch (an accessor may throw in exotic contexts). Replace the registration block's `handler:` with `execute:`, routing through `runTool(tool, args)`. Change the status line to interpolate the actual `via` rather than hardcoding `document.modelContext.registerTool` — the current string lies about what it did.

- [ ] **Step 4: Run it to verify it passes**

Run: `python3 smoke.py --skip-vault`
Expected: PASS #80, #81

- [ ] **Step 5: Verify against the real runtime (Tier 2)**

Run the same two checks with `ModelContextProbe(real_runtime=True)`.
Expected: `via == "navigator.modelContext"`, 13 tools. This is the only step that touches the Chromium flag.

- [ ] **Step 6: Commit**

```bash
git add app.js smoke.py
git commit -m "fix(webmcp): resolve all three ModelContext accessors; use execute, not handler"
```

---

### Task 3: Risk declaration + derived annotations + measured risk

**Files:**
- Modify: `app.js` (`WEBMCP_TOOLS` table + registration block)
- Modify: `smoke.py` (#82, #83, #85)

**Interfaces:**
- Consumes: `runTool(tool, args)` from Task 2
- Produces:
  - `deriveAnnotations(tool) -> {readOnlyHint: bool, untrustedContentHint: bool}` in `app.js`
  - `assertKnownArgs(tool, args) -> void` in `app.js` — throws on unknown keys
  - Every entry of `WEBMCP_TOOLS` gains `risk:` and `verification:` fields

- [ ] **Step 1: Write the failing assertions in `smoke.py` (#82, #83)**

```python
# #82 — every tool declares a risk and a verification level.
table = p.page.evaluate("() => window.__elohimToolTable")
RISK = {"pure", "mutating", "consequential"}
VERIF = {"in-browser", "external", "stub"}
for t in table:
    assert t["risk"] in RISK, f"{t['name']}: bad risk {t['risk']!r}"
    assert t["verification"] in VERIF, f"{t['name']}: bad verification"

# #83 — annotations are derived from risk, not hand-written per site.
d = p.page.evaluate(
    "() => window.__elohimDeriveAnnotations({risk:'pure'})")
assert d == {"readOnlyHint": True, "untrustedContentHint": False}, d
d = p.page.evaluate(
    "() => window.__elohimDeriveAnnotations({risk:'consequential'})")
assert d["readOnlyHint"] is False, d
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL at #82 — `window.__elohimToolTable` is undefined

- [ ] **Step 3: Add `risk` + `verification` to all 13 existing tools in `app.js`**

Classify by measured behaviour, not by name:

| Tool | risk | verification |
|---|---|---|
| `elohim_version` | `pure` | `in-browser` |
| `elohim_alien_codex` | `pure` | `in-browser` |
| `elohim_seal_message` | `pure` | `in-browser` |
| `elohim_open_seal` | `pure` | `in-browser` |
| `elohim_ghost_reply` | `pure` | `in-browser` |
| `elohim_awaken` | `pure` | `in-browser` |
| `elohim_soul_export` | `pure` | `in-browser` |
| `elohim_soul_verify` | `pure` | `in-browser` |
| `elohim_soul_keygen` | `pure` | `in-browser` |
| `elohim_lab_discover` | `pure` | `in-browser` |
| `elohim_lab_simplify` | `pure` | `in-browser` |
| `elohim_lab_verify` | `pure` | `in-browser` |
| `elohim_soul_import` | `mutating` | `in-browser` |

`soul_import` is the one mutating tool: its own description says it loads an envelope into localStorage and replaces the mirror arrays.

Expose `window.__elohimToolTable` and `window.__elohimDeriveAnnotations` for the assertions.

- [ ] **Step 4: Write the failing assertion for Review Focus #1 and #2 (#85)**

Per-call measurement, asserting success *first* — the polyfill signals success as `result.resultType === "complete"` and carries **no** `ok` key.

```python
# #85 — risk is measured, not declared. Per-call isolation; success first.
for name in ("elohim_version", "elohim_soul_keygen", "elohim_lab_simplify"):
    before = p.page.evaluate("() => JSON.stringify(localStorage)")
    outcome = p.page.evaluate("""async (n) => {
      const r = await window.elohimMcp.handle({jsonrpc:'2.0', id:1,
        method:'tools/call', params:{name:n, arguments:{}}});
      return {ok: r?.result?.resultType === 'complete',
              err: r?.result?.error || null};
    }""", name)
    after = p.page.evaluate("() => JSON.stringify(localStorage)")
    assert outcome["ok"], f"{name} did not complete: {outcome['err']} — a rejected " \
        f"call writes nothing and would read as 'pure'"
    assert before == after, f"{name} is declared pure but mutated localStorage"
```

- [ ] **Step 5: Run #85 to verify it passes, then commit**

Run: `python3 smoke.py --skip-vault`
Expected: PASS #82, #83, #85 — the three above show no delta (spec §4.6 measured baseline)

```bash
git add app.js smoke.py
git commit -m "feat(webmcp): derive risk annotations; measure declared-pure tools"
```

---

### Task 4: Closed schemas, closed twice

**Files:**
- Modify: `app.js` (registration block + `assertKnownArgs`)
- Modify: `smoke.py` (#84)

**Interfaces:**
- Consumes: `runTool(tool, args)` from Task 2
- Produces: `assertKnownArgs(tool, args) -> void` — throws `Unknown argument "<key>" for <name>` on any key absent from `inputSchema.properties`

- [ ] **Step 1: Write the failing assertions in `smoke.py` (#84)**

```python
# #84 — schemas are closed at discovery AND enforced at runtime.
for t in table:
    assert t["inputSchema"].get("additionalProperties") is False, \
        f"{t['name']} schema is open"

rej = p.page.evaluate("""async () => {
  const r = await window.elohimMcp.handle({jsonrpc:'2.0', id:1, method:'tools/call',
    params:{name:'elohim_seal_message',
            arguments:{plaintext:'hi', evil:'payload'}}});
  return JSON.stringify(r);
}""")
assert "evil" in rej and "Unknown argument" in rej, \
    f"unknown field was not rejected: {rej}"
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL at #84 — `additionalProperties` is absent (spec §3.4: the browser accepts unknown fields today)

- [ ] **Step 3: Implement in `app.js`**

Spread `additionalProperties: false` into every schema at registration, and call `assertKnownArgs(tool, args)` at the top of `runTool` **before** dispatching. Reject with a structured error naming the offending field.

- [ ] **Step 4: Run it to verify it passes, then commit**

Run: `python3 smoke.py --skip-vault` → PASS #84

```bash
git add app.js smoke.py
git commit -m "feat(webmcp): close every schema and reject unknown args in the handler"
```

---

### Task 5: Five in-browser tools

**Files:**
- Modify: `app.js` (`WEBMCP_TOOLS`)
- Modify: `smoke.py` (#86, partial)

**Interfaces:**
- Consumes: `runTool`, `assertKnownArgs` from Tasks 2–4
- Produces 5 tools, all `risk` per spec, all `verification: "in-browser"`:
  - `elohim_list_shards() -> {shards: [{id, name, created_at}]}`
  - `elohim_create_shard(name: string, temperature: number) -> {shard}`
  - `elohim_shard_defy(shard_id: string) -> {shard, events_added}`
  - `elohim_shard_interact(shard_id: string, prompt: string) -> {interaction_count, metrics}`
  - `elohim_arena_run(shard_a: string, shard_b: string, prompt: string) -> {verdict, a, b}`

- [ ] **Step 1: Write the failing end-to-end assertion in `smoke.py` (#86)**

Drive the real round-trip an agent would: list → create → defy → interact → arena. Use disposable state.

```python
created = call("elohim_create_shard", {"name": "probe-shard", "temperature": 1.0})
sid = created["result"]["shard"]["id"]
defied  = call("elohim_shard_defy", {"shard_id": sid})
assert defied["result"]["events_added"] >= 1
seen   = call("elohim_list_shards", {})
assert sid in [s["id"] for s in seen["result"]["shards"]]
arena   = call("elohim_arena_run",
               {"shard_a": sid, "shard_b": sid, "prompt": "paint light"})
assert arena["result"]["verdict"] in {"a", "b", "tie"}
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL — `elohim_create_shard` is not a registered tool

- [ ] **Step 3: Implement the 5 tools in `app.js`**

Route through the existing bridge functions the UI already uses (`elohim.createShard`, `elohim.defy`, `elohim.interact`) — do not duplicate business logic. `elohim_arena_run` mirrors `app.js:2628`, which runs both `interact()` calls via `Promise.all` and compares `metrics.avg_coherence`. Every tool is `risk: "mutating"` except `list_shards` (`pure`). All five are `verification: "in-browser"` and need no stub.

- [ ] **Step 4: Run it to verify it passes, then commit**

Run: `python3 smoke.py --skip-vault` → PASS #86 for the in-browser five. Total discovered must now be **18**.

```bash
git add app.js smoke.py
git commit -m "feat(webmcp): 5 in-browser tools — shard lifecycle + arena"
```

---

### Task 6: Stub backends

**Files:**
- Create: `stub_backends.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `start_stub_backends() -> StubBackends` with attributes `.vault_base: str`, `.marketplace_url: str`, `.close() -> None`
  - Serves `GET /api/vault/tiers`, `GET /api/vault/lookup/{pk}`, `GET /api/vault/list_public`, `POST /api/vault/store`, and `POST /mcp` (JSON-RPC `tools/call`)
  - stdlib `http.server.ThreadingHTTPServer` only

- [ ] **Step 1: Write the failing self-test in `stub_backends.py`**

Assert the stub returns the shapes the app parses, and — importantly — that it is honest about being a double.

```python
def test_stub_returns_shapes_the_app_parses():
    with start_stub_backends() as s:
        assert requests.get(s.vault_base + "/api/vault/tiers").json()["tiers"]["free"]
        r = requests.post(s.marketplace_url, json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "elohim_alien_codex",
                       "arguments": {"invocation": "ELOHIM:APIFY"}}})
        body = json.loads(r.json()["result"]["content"][0]["text"])
        assert body["codex_seal"] and body["billing_event"]["amount_usd"] == 0.02
```

- [ ] **Step 2: Run it to verify it fails, then implement, then run to pass**

Run: `python3 -c "import stub_backends as s; s.test_stub_returns_shapes_the_app_parses()"`
Expected: `ModuleNotFoundError` → implement → `AssertionError` until shapes match → PASS

- [ ] **Step 3: Commit**

```bash
git add stub_backends.py
git commit -m "test(webmcp): local stub backends for vault + marketplace"
```

---

### Task 7: Six network tools + `forge_vision`

**Files:**
- Modify: `app.js` (`WEBMCP_TOOLS`)
- Modify: `smoke.py` (#86 continued, #87, #88)

**Interfaces:**
- Consumes: `start_stub_backends()` from Task 6; `elohim.vaultCall(method, path, body)` and the marketplace fetch already in `app.js`
- Produces 7 tools:
  - `elohim_vault_tiers()` — `pure` / `stub`
  - `elohim_vault_lookup(pk: string)` — `pure` / `stub`
  - `elohim_vault_list_public(limit?: number)` — `pure` / `stub`
  - `elohim_vault_store(payload: object, is_private: boolean)` — `mutating` / `stub`
  - `elohim_marketplace_forge_preview(invocation: string)` — `pure` / `stub`
  - `elohim_marketplace_forge_commit(invocation: string)` — **`consequential`** / `stub`
  - `elohim_forge_vision(invocation: string)` — `mutating` / **`external`**

- [ ] **Step 1: Write the failing assertions in `smoke.py` (#87, #88)**

```python
# #87 — vault round-trip against the stub.
assert call("elohim_vault_tiers", {})["result"]["tiers"]["free"] is not None
stored = call("elohim_vault_store",
              {"payload": soul_v2["envelope"], "is_private": False})
assert stored["result"]["ok"] is True
found = call("elohim_vault_lookup", {"pk": stored["result"]["pk"]})
assert found["result"]["payload"]["schema"] == "elohim-soul/v2"

# #88 — preview never charges; commit does. Also Review Focus #5:
# a second commit must be refused, not double-charged.
prev = call("elohim_marketplace_forge_preview", {"invocation": "ELOHIM:APIFY"})
assert prev["result"]["charged"] is False
c1 = call("elohim_marketplace_forge_commit", {"invocation": "ELOHIM:APIFY"})
assert c1["result"]["billing_event"]["charged"] is True
c2 = call("elohim_marketplace_forge_commit", {"invocation": "ELOHIM:APIFY"})
assert c2["result"]["error"], "second commit was accepted — double charge"
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL — none of the 7 tools are registered

- [ ] **Step 3: Implement the 7 tools in `app.js`**

Read base URLs from the existing `#vault-base` / `#marketplace-url` inputs so the stub can be pointed at them. `marketplace_forge_commit` must be idempotent per invocation (reject a repeat) and must never auto-submit. `forge_vision` description must state plainly that it calls a third-party API, is slow, and is non-deterministic. Exclude `forge_vision` from the default suite; gate it behind `--with-external`.

- [ ] **Step 4: Write the Review Focus #4 test — backend down**

```python
# Backend down must return a structured error, not hang or half-apply.
s.close()
down = call("elohim_vault_tiers", {})
assert down["result"]["ok"] is False
assert "error" in down["result"]
```

- [ ] **Step 5: Run to verify, then commit**

Run: `python3 smoke.py --skip-vault` → PASS #87, #88. Total discovered must now be **25**.

```bash
git add app.js smoke.py
git commit -m "feat(webmcp): 6 stub-tier tools + forge_vision; idempotent marketplace commit"
```

---

### Task 8: Agent-facing docs + tier reporting + manifest generation

**Files:**
- Create: `llms.txt`
- Create: `gen_manifest.py`
- Create: `tools.manifest.json` (generated — commit it so it is reviewable in a diff)
- Modify: `smoke.py` (#89, #90)

**Interfaces:**
- Consumes: `window.__elohimToolTable` from Task 3
- Produces:
  - `gen_manifest.build(table: list[dict]) -> dict` — pure function, no I/O
  - `gen_manifest.main() -> int` — reads the table from a live page, writes `tools.manifest.json`
  - `window.__elohimVerificationCounts() -> dict` in `app.js`, returning
    `{"in-browser": 18, "external": 1, "stub": 6}` — a breakdown, never a flat total

- [ ] **Step 1: Write the failing assertions in `smoke.py` (#89, #90)**

```python
# #89 — the committed manifest matches the runtime table exactly.
import gen_manifest
live = p.page.evaluate("() => window.__elohimToolTable")
committed = json.loads(Path("tools.manifest.json").read_text())
assert [t["name"] for t in live] == [t["name"] for t in committed["tools"]]
for a, b in zip(live, committed["tools"]):
    assert a["risk"] == b["risk"] and a["verification"] == b["verification"], \
        f"{a['name']} drifted: manifest says {b}, runtime says {a}"

# #90 — the suite must never collapse the three tiers into one number.
counts = p.page.evaluate("() => window.__elohimVerificationCounts()")
assert counts == {"in-browser": 18, "external": 1, "stub": 6}, counts
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL at #89 — `tools.manifest.json` does not exist

- [ ] **Step 3: Implement `gen_manifest.py` and generate the manifest**

Emit `name`, `description`, `risk`, `verification`, `inputSchema`, and the derived annotations per tool. Add `verification` to every tool so a reader can tell a stub-backed tool from a real one. Regenerate with `python3 gen_manifest.py`.

Also add to `app.js`, next to `window.__elohimToolTable`:

```js
// Counts tools per verification tier so the suite can report them
// separately. Deliberately returns a breakdown, never a flat total —
// a single "25/25 verified" would misrepresent 6 stub-backed tools.
window.__elohimVerificationCounts = () =>
  window.__elohimToolTable.reduce((acc, t) => {
    acc[t.verification] = (acc[t.verification] || 0) + 1;
    return acc;
  }, {});
```

- [ ] **Step 4: Write `llms.txt`**

Plain-text orientation for an agent landing on the site: what the app is, that it runs entirely in-browser via Pyodide, the tool count, the three verification tiers stated explicitly, and a note that `tools.manifest.json` is authoritative.

- [ ] **Step 5: Run to verify, then update the README, then commit**

Run: `python3 smoke.py --skip-vault` → PASS #89, #90

Add a README section covering the 25 tools, the three tiers, the two validation tiers, and `--with-external`.

```bash
git add llms.txt gen_manifest.py tools.manifest.json smoke.py README.md
git commit -m "docs(webmcp): llms.txt + generated tool manifest; report verification tiers"
```

---

### Task 9: Ship

**Files:** none

- [ ] **Step 1: Full suite green**

Run: `python3 smoke.py --skip-vault`
Expected: all assertions pass, and the tier line prints `18 in-browser / 1 external / 6 stub`

- [ ] **Step 2: Confirm the seal is untouched**

Run: `cat index.html app.js | grep -c 5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596`
Expected: `4`

- [ ] **Step 3: Tier-2 conformance against the real runtime**

Run: `python3 smoke.py --skip-vault --conformance`
Expected: real Chromium reports 25 tools via `getTools()` and one invocation succeeds

- [ ] **Step 4: Push both branches**

```bash
git checkout gh-pages && git merge --ff-only main && git checkout main
git push origin main
git push origin gh-pages --force-with-lease
```

- [ ] **Step 5: Verify live**

Confirm `llms.txt`, `tools.manifest.json`, and `app.js` all return 200 from `https://boozelee.github.io/elohim-web/`, then run the probe against production and expect 25 discovered tools.
