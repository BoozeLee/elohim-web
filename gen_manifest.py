#!/usr/bin/env python3
"""Generate tools.manifest.json — the machine-readable WebMCP tool surface.

An agent loading elohim-web should not have to run the page to learn what
it can call. This generator reads the live `window.__elohimToolTable()` out
of a booted page and writes the committed manifest, so the published
contract is a build artifact rather than hand-maintained prose.

Two functions, deliberately split:

  build(table)  pure, no I/O — the shape an agent reads
  main()        boots a page, pulls the table, writes the file

`build()` is pure so the manifest's shape is unit-testable without a
browser, and so the #89 drift guard can re-derive what a tool entry
*should* look like and compare it against the committed bytes.

Run:  python3 gen_manifest.py
      ELOHIM_SMOKE_URL=http://127.0.0.1:8899/ python3 gen_manifest.py

The output is committed on purpose: an agent fetching tools.manifest.json
gets a reviewable diff when a tool changes, which is more useful than a
blob that is regenerated silently on every deploy.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "tools.manifest.json"
DEFAULT_URL = "http://127.0.0.1:8790/"

# The three verification tiers, spelled out rather than summed. These strings
# must match the `verification` values in app.js's WEBMCP_TOOLS table; #90
# asserts the exact breakdown, so renaming one fails the suite rather than
# quietly dropping a tool out of a total.
TIER_NOTES = {
    "in-browser": (
        "Exercised end-to-end against the real running app. No network "
        "backend involved."
    ),
    "stub": (
        "Exercised against a local stub server written for the test suite. "
        "The request/response contract is verified; the production backend "
        "is not."
    ),
    "external": (
        "Calls a real external service. Opt-in only — run with "
        "--with-external, off in the default suite."
    ),
}


def build(table: list[dict]) -> dict:
    """Assemble the manifest from a runtime tool table. Pure — no I/O.

    `table` is what `window.__elohimToolTable()` returns: a list of
    {name, description, inputSchema, risk, verification}.

    Annotations are NOT recomputed here. They are read back from the live
    page via `window.__elohimDeriveAnnotations()` in main(), because the
    derivation lives in app.js and a Python re-implementation would be a
    second source of truth that can drift from the one that actually
    registers the tools. #89 compares the committed annotations against the
    runtime's own derivation.
    """
    if not table:
        raise ValueError("refusing to build a manifest from an empty table")

    tools = []
    for t in table:
        for key in ("name", "description", "inputSchema", "risk", "verification"):
            if key not in t:
                raise ValueError(f"tool {t.get('name', '<unnamed>')!r} "
                                 f"is missing {key!r}")
        if t["risk"] not in ("pure", "mutating", "consequential"):
            raise ValueError(f"unknown risk {t['risk']!r} for {t['name']}")
        if t["verification"] not in TIER_NOTES:
            raise ValueError(
                f"unknown verification tier {t['verification']!r} for "
                f"{t['name']} — add it to TIER_NOTES before shipping it, so "
                f"readers of the manifest can tell what was actually tested")

        entry = {
            "name": t["name"],
            "description": t["description"],
            "risk": t["risk"],
            "verification": t["verification"],
            "annotations": t.get("annotations", {}),
            "inputSchema": t["inputSchema"],
        }
        # A closed schema is a promise. Surface the fact explicitly so an
        # agent does not have to diff the schema to notice that unknown
        # arguments are rejected — the handler enforces it, not the browser.
        entry["closed"] = t["inputSchema"].get("additionalProperties") is False
        tools.append(entry)

    counts: dict[str, int] = {}
    for t in tools:
        counts[t["verification"]] = counts.get(t["verification"], 0) + 1

    return {
        "schema": "elohim-webmcp-manifest/v1",
        "source": "https://boozelee.github.io/elohim-web/",
        "howToRead": (
            "This manifest is generated from the running app "
            "(gen_manifest.py) and committed. If it disagrees with "
            "modelContext.getTools(), the app is authoritative and this "
            "file is stale — #89 in smoke.py fails on exactly that drift."
        ),
        "count": len(tools),
        # A breakdown, never a flat total. `count` is 25; that does NOT mean
        # 25/25 verified against production. Read verificationCounts.
        "countIsNotAVerificationClaim": True,
        "verificationCounts": counts,
        "verificationTiers": {k: v for k, v in sorted(TIER_NOTES.items())},
        "tools": tools,
    }


def read_table(url: str) -> list[dict]:
    """Boot the page and pull the live table + runtime-derived annotations."""
    from webmcp_probe import ModelContextProbe

    with ModelContextProbe(url=url) as probe:
        page = probe.page
        page.goto(url)
        page.wait_for_selector("#boot.hidden", state="attached", timeout=300000)

        via = page.evaluate("() => window.__elohimWebmcpVia || null")
        if via is None:
            raise SystemExit(
                "app.js never published __elohimWebmcpVia — it did not boot "
                "far enough to register tools. Refusing to write a manifest "
                "that would describe a surface the app does not have.")
        table = page.evaluate("() => window.__elohimToolTable()")
        # Annotations come from the app's own derivation, not from a Python
        # re-implementation of it.
        annotated = page.evaluate(
            """() => window.__elohimToolTable().map(t => ({
                ...t,
                annotations: window.__elohimDeriveAnnotations(t),
            }))""")
        return annotated


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    url = os.environ.get("ELOHIM_SMOKE_URL", DEFAULT_URL)
    out = MANIFEST
    for a in argv:
        if a.startswith("--url="):
            url = a.split("=", 1)[1]
        elif a.startswith("--out="):
            out = HERE / a.split("=", 1)[1]
        else:
            print(__doc__)
            return 2

    table = read_table(url)
    manifest = build(table)

    out.write_text(json.dumps(manifest, indent=2) + "\n")
    counts = manifest["verificationCounts"]
    breakdown = " / ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    print(f"wrote {out.name}: {manifest['count']} tools ({breakdown})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
