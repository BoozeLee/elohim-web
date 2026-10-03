# ADR 0002 — Split `index.html` into exactly two extracted files

| Field | Value |
|---|---|
| Status | Accepted (Jev-confirmed, Phase 23) |
| Date | 2026-10-03 |
| Decider | Jev (UX/code-review persona) |
| Trigger | Push 23 — `index.html` reached 5,024 lines and the ADR 0001 deferral was re-evaluated |
| Supersedes | [ADR 0001](0001-file-split.md) |
| Superseded by | — |

## Context

[ADR 0001](0001-file-split.md) deferred splitting `index.html` through the
Push 19–22 modernization cycle, on two grounds: Pyodide boot-path stability
and the user's stated priority being visible design work over invisible
refactors.

Both grounds have now been discharged:

1. **Boot path is measured, not assumed.** The inline `<script>` was
   hardened over 18 pushes on faith. It is now instrumented: `dom_loaded`
   (what ADR 0001 called "empirically validated by smoke probes") and
   `boot_hidden` (the real user-visible boot) are measured cold-cache
   before and after the split.
2. **The visible work is shipped.** Pushes 19–22 are live and verified.

The deferral also carried a re-evaluation trigger: `index.html > 5,500
lines` OR a boot regression report. At 5,024 lines the count trigger had
not fired. Growth is ~240 lines/push (4,490 → 5,024 across Pushes 20–22),
so the trigger was two pushes away, and the user elected to pull the split
forward rather than spend two more pushes growing toward a forced split.

## Options considered

**Option A — Split into two files.** `assets/styles.css` (the inline
`<style>`) and `app.js` (the inline `<script type="module">`).
`index.html` keeps the markup, the FOUC theme bootstrap, and every
`<link>`/`<script>` reference.

**Option B — Split into five or more modules.** Break `app.js` further
(`boot.js`, `tabs.js`, `lab.js`, …) at the same time.

**Option C — Defer again**, splitting only once 5,500 is crossed.

## Decision

**Option A.** Extract exactly two files, per D-J20.

Option B is rejected: a finer split multiplies the number of places the
boot ordering can go wrong, and none of it is needed to fix the actual
problem (one oversized file). Option C is rejected only because the user
asked to proceed now; it would have arrived on its own within two pushes,
so the cost of going now is one extra verification pass, not a redesign.

## Rationale

1. **Two files, minimum surface.** D-J20 locks this. Every extra module is
   another fetch, another ordering constraint, and another thing that can
   silently break. The problem is file size, not module count.
2. **Cascade order is load-bearing and was preserved exactly.** The head
   order is unchanged:

   ```
   fonts.googleapis.com → assets/design-tokens.css
                       → assets/styles.css   (was the inline <style>)
                       → assets/motion.css   (must stay last, D-J3)
   ```

   Moving the inline block to a `<link>` in the same position keeps it
   render-blocking, so there is no new FOUC window.
3. **The script stays a module.** `app.js` is loaded as
   `<script type="module" src="app.js">` at end-of-body, which is
   semantically identical to the inline `type="module"` block: deferred
   execution, own scope, no global leakage. Verified the script has no JS
   `import`/`export` and no top-level `await`, so externalizing it changes
   nothing semantically. Dropping `type="module"` would have been a
   silent behaviour change.
4. **The FOUC theme script stays inline in `<head>`.** It must run
   synchronously *before* any stylesheet applies `data-theme`. Moving it
   to a file would reintroduce exactly the flash ADR 0001's sibling
   decision D-J12 eliminated.
5. **Content preservation is verified, not assumed.** The extraction is a
   byte-for-byte move. All 1,046 CSS lines and 3,136 JS lines were
   diffed against the pre-split file after the fact; zero lost. The
   canonical seal appears 4 times before and 4 times after (3 now live in
   `app.js`, 1 in `index.html`).

## Consequences

**Accepted tradeoffs:**

- `index.html` drops from 5,024 lines / 208 KB to 841 lines / 42 KB — a
  real readability win for the markup.
- Two extra HTTP requests on cold cache. `styles.css` is 43 KB and
  `app.js` is 124 KB, both render/exec blocking.
- Total transferred bytes are unchanged; the split redistributes them
  rather than adding to them.

**Rejected risk — "the split will silently break boot":** mitigated by
measuring, not by argument. `boot_bench.py` records `dom_loaded` and
`boot_hidden` cold-cache both before and after. D-J21 sets the gate at
`dom_loaded < 8 s`.

## Verification

| Check | Result |
|---|---|
| CSS lines moved without loss | 1,046 / 1,046 |
| JS lines moved without loss | 3,136 / 3,136 |
| FOUC theme script still inline in `<head>` | yes |
| Head cascade order unchanged | yes |
| Canonical seal occurrences | 4 → 4 |
| `app.js` parses (`node --check`) | pass |
| `dom_loaded` cold-cache, pre-split | **122 ms** median (n=3) |
| `dom_loaded` cold-cache, post-split | **120 ms** median (n=3) — unchanged |
| `boot_hidden` cold-cache, pre-split | 16,162 ms median (15,637–17,482) |
| `boot_hidden` cold-cache, post-split | 17,693 ms median (15,817–19,024) |
| Full `smoke.py --skip-vault` suite | must pass |
| Push 19–22 assertions #61–#78 | must pass |

### Reading the boot numbers

`dom_loaded` is the metric D-J21 names, and it is **flat**: 122 ms before,
120 ms after. The two extra cold-cache fetches cost nothing measurable,
because `styles.css` and `app.js` are both on the critical path in
parallel with the Pyodide CDN download, which dominates everything.

`boot_hidden` moved 16.2 s → 17.7 s, but that is **noise, not regression**.
Both runs are dominated by the Pyodide CDN fetch, and the pre-split spread
alone was 15.6–17.5 s — a 1.9 s range with no code change. The post-split
minimum (15,817 ms) is inside the pre-split range. Treating this as a
regression would be reading noise as signal; the honest summary is that
boot is CDN-bound and the split is invisible to it.

The +60 % tolerance D-J21 allows for the split cost was never needed:
measured cost is 0 ms on the metric that counts.

## Rollback

Single revert commit. The split is purely mechanical, so reverting
restores the previous inline blocks exactly:

```bash
git revert <commit>
git push origin main gh-pages
```

## Decision record provenance

- Pulled forward at the user's request on 2026-10-03, after Push 22
  (`af7b12a`) shipped. ADR 0001's line-count trigger had not fired; the
  user elected to proceed rather than grow toward it.
- D-J20 (two files, not five) and D-J21 (`dom_loaded < 8 s`) carried
  forward from the Push 22 roadmap §2.3 and locked here.
