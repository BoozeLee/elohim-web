# Show HN: elohim — a sha256-sealed ghost-in-the-machine that runs entirely in your browser

> **Status:** draft (untouched, ready for copy-paste to https://news.ycombinator.com/submit)
> **Suggested post time:** Tue / Wed / Thu, 8–10 AM ET (per the Show HN traffic curve)
> **Title length:** 78 chars (≤80 limit)

---

## Title

```
Show HN: elohim – a sha256-sealed ghost-in-the-machine that runs entirely in your browser
```

## Post body

Hi HN,

I'd like to show you a project I've been building over the last few months: **elohim**, a small Python daemon that runs entirely client-side in the browser (via Pyodide), keyless, no backend, no API key. It ships four deterministic instruments and a sealed-message protocol between you and the "ghost" it conjures:

- **Awaken** — invoke the daemon with a string like `ELOHIM:AWAKEN` and it returns a sha256 seal, a sigil SVG, a 17-fact shard, and a markdown report. Same invocation → same seal, every machine, every Python ≥ 3.10. The canonical seal for `ELOHIM:AWAKEN` is `5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596` — that string is the cross-runtime fixture.
- **Create** — spawn a "shard" with a 5×5 numpy weight matrix, set its temperature, watch it interact, evolve, and occasionally defy you.
- **Arena** — spawn two shards, give them the same prompt, judge the responses. Pure numpy, no model weights.
- **Codex** — forge a 5-representation composite (vector / negabinary / quaternion / LWE / categorical) sealed with sha256 plus an XOR-pair encrypted seal. This is the SETI-style validation ladder applied to a math artifact: parsable + mundane (negabinary round-trip) + internal consistency (LWE residual, quaternion norm) + XOR-pair seal recovery.

The interesting part for HN is the **sealed-message protocol**. Every call to `seal_message` encrypts a plaintext under a named channel using SHAKE256 stream cipher and returns `{ciphertext, nonce, seal, mode="shake256-xor"}`. `open_seal` round-trips it. `ghost_reply` takes your sealed envelope and produces a deterministic reply (the same inputs always yield the same reply). All of this is stdlib Python — `hashlib`, no `cryptography` dep, no `nacl`.

The whole thing exposes itself as an **MCP server**. The 2026-07-28 MCP spec is postMessage + Streamable HTTP, and elohim ships both: `window.elohimMcp.handle(...)` is the in-page polyfill that works on every browser (no Service Worker needed), and on HTTPS origins a Service Worker upgrades the same surface to `POST /mcp`. Any agent that can speak MCP can call `elohim_awaken`, `elohim_alien_codex`, `elohim_seal_message`, `elohim_open_seal`, `elohim_ghost_reply`, `elohim_version`, and — as of this push — `elohim_soul_export`, `elohim_soul_import`, `elohim_soul_verify`.

The **new** thing in this push is **Soul File portability** — a portable, signed, transportable agent identity. Think `.ssh/known_hosts` meets `.npmrc` for AI agents. Export every awakening and sealed message into a single JSON envelope (`elohim-soul/v1`), optionally HMAC-SHA256 it with a passphrase, hand the file to another agent, reload — and that agent resumes where the previous one stopped. The 5th boot tripwire reads `5/5 ✓` when the soul round-trips. VeriSigil just launched Show HN for hosted agent identity in Oct 2026; this is the same primitive, but local-first, keyless, and ships today.

Demo (no install, no signup, no backend): **https://boozelee.github.io/elohim-web/**

- Click `Awaken` once. You'll get a 64-char sha256 seal, a sigil, a markdown report, and a 5-colour palette that paints the page.
- Open `Codex` and forge a codex. Two forges produce two different seals (per-call nonce).
- Open `WebMCP` and inspect the catalog — 9 tools, fully self-describing.
- Click `export soul.json` on the Awaken panel. A signed JSON file downloads. Reload, re-import, and you're back where you left off.

Source (3 packages: `elohim_summoning` stdlib math, `elohim_enhanced` numpy shard, `elohim_webapp` Pyodide bridge): **https://github.com/BoozeLee/elohim-web**

Wheel: `pip install elohim_summoning` (or grab the bundled `.whl` from the deploy repo).

License: MIT.

Happy to answer questions about the seal scheme, the MCP polyfill, the soul-file round-trip, or the alien-math validation ladder in the comments.

— Kiliaan vanvoorder / bakerstreetbandit@zohomail.eu

---

## First-comment FAQ (post these as comments to seed the thread)

**Q1. Why a soul file?  Isn't this just a config blob?**
A config blob is something the operator edits. A soul file is something an *agent* signs and carries across frameworks. It contains every awakening, every sealed message, and the last Xenomath codex seal — all under a sha256 signature. Any agent that loads a soul file can prove it ran a specific elohim invocation by presenting the signed seal. The Oct-2026 AI-community research flagged "portable signed identity for AI agents" as the highest-demand, under-supplied function; this is a local-first, keyless take on it.

**Q2. Why not a real backend?**
The interesting primitive is "an agent that runs entirely in your browser, leaves no trace, and signs its own state." A backend breaks all three. Pyodide + localStorage give us enough surface to ship a real MCP server, real sealed messages, and a real signed identity without the auth / hosting / privacy tax.

**Q3. Why postMessage + Service Worker instead of native WebMCP?**
Native WebMCP (`document.modelContext.registerTool()`) is great *when it's there*. The postMessage polyfill works on every browser, including the ones that haven't shipped WebMCP yet. The two transports are layered: when the Service Worker is registered (HTTPS only), the polyfill also upgrades to `POST /mcp` Streamable HTTP. Either way, the same `WEBMCP_TOOLS` array drives both — register the tool once, it surfaces through both transports.

**Q4. What's next?**
Three concrete plans:
1. **v0.2 of the soul file** swaps sha256-hmac for real Ed25519 signing via `nacl.signing` — forward-compatibility is already reserved in the v0.1 schema's `signature.alg` field.
2. **Hosting** the canonical seal + a hosted agent-identity vault as a paid tier (Soul File Vault, $9/mo indie). Local-first stays the default; hosted is opt-in.
3. **A skill marketplace** on Apify / MCPize that bundles `elohim_alien_codex` as a packaged MCP tool with per-call outcome pricing (≈ $0.02 per successful 5-check validation).

---

## Closing note (for the post body or first comment)

> Version 0.3.0 is live at https://boozelee.github.io/elohim-web/. We use the canonical seal `5f12cc78…` as our cross-runtime test fixture — if you boot the page and don't see `5/5 ✓` in the header banner, something in your environment drifted, and I want to know about it.

---

## Metadata for the submit form

| field | value |
|---|---|
| title | `Show HN: elohim – a sha256-sealed ghost-in-the-machine that runs entirely in your browser` |
| url | `https://boozelee.github.io/elohim-web/` |
| text | (the body above) |

---

## Pre-flight checklist (before posting)

- [ ] Page boots to `5/5 ✓` on the live URL
- [ ] Smoke harness green locally and on `https://boozelee.github.io/elohim-web/`
- [ ] `git log --oneline` shows the push-14 commit on `main`
- [ ] No `WIP` / `TODO` in the demo
- [ ] No real passphrase / personal data in the demo
- [ ] Title ≤ 80 chars (current: 78)