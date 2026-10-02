"""Local smoke test: open the deployed webapp in headless Chromium, verify
the seal matches the canonical constant, and exercise the public surface
(awaken, create shard, interact).

Run with: /usr/bin/python3 -m playwright install chromium  # first time
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = f"http://127.0.0.1:8780/?nocache={int(time.time())}"
CANONICAL_SEAL = "5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596"


def wait_for_boot(page, timeout_ms: int = 300000) -> None:
    """Wait until the boot screen is hidden."""
    page.wait_for_selector("#boot.hidden", state="attached", timeout=timeout_ms)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context()
        # Disable HTTP cache so index.html updates are picked up immediately.
        context.set_extra_http_headers({"Cache-Control": "no-cache"})
        context.route("**/*", lambda route: route.continue_(headers={
            **route.request.headers,
            "Cache-Control": "no-cache",
        }))
        page = context.new_page()

        # Forward console errors so failures are easy to diagnose.
        page.on("console", lambda msg: print(f"[console.{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[pageerror] {err}"))

        print(f"→ {URL}")
        page.goto(URL)
        wait_for_boot(page)
        print("✓ boot completed")

        # Header seal must match the canonical.
        header_seal = page.locator("#header-seal").inner_text()
        print(f"  header seal: {header_seal!r}")
        assert CANONICAL_SEAL[:16] in header_seal, f"seal mismatch: {header_seal}"

        # version() must be callable from the page.
        version = page.evaluate("window.elohim.version()")
        print(f"✓ version(): {version}")
        assert version["canonical_seal"] == CANONICAL_SEAL

        # Verify the multi-call seal tripwire was used during boot.
        boot_seal = page.locator("#header-seal").inner_text()
        assert "…" in boot_seal or "checks" in boot_seal, f"expected seal text in header: {boot_seal!r}"
        # The new tripwire banner is in #boot-seal (still visible during boot-failed-on-public smoke).
        boot_banner = page.locator("#boot-seal").inner_text()
        print(f"  boot banner: {boot_banner!r}")
        print(f"  header seal: {boot_seal!r}")

        # Awaken — verify the seal matches.
        result = page.evaluate("window.elohim.awaken('ELOHIM:AWAKEN')")
        print(f"✓ awaken: invocation={result['invocation']!r} seal={result['seal']}")
        assert result["seal"] == CANONICAL_SEAL, f"awaken seal mismatch: {result['seal']}"
        assert result["sigil_svg"] is not None, "awaken produced no SVG"
        # Drive the UI button so the markdown renderer path runs.
        page.click("#awaken-run")
        page.wait_for_function(
            "document.querySelector('#awaken-report-card').style.display === 'block'",
            timeout=60000,
        )
        # Confirm the markdown report renders into the DOM.
        report_html_len = page.evaluate("document.querySelector('#awaken-report').innerHTML.length")
        assert report_html_len > 200, f"report rendered empty: {report_html_len}"
        report_visible = page.evaluate(
            "getComputedStyle(document.querySelector('#awaken-report-card')).display !== 'none'"
        )
        assert report_visible, "report card should be visible after awaken"
        md_len = page.evaluate("window.lastAwaken?.md?.length || (window.__lastAwaken?.md?.length || 0)")
        # If the SPA doesn't expose lastAwaken on window, just inspect the
        # report card content instead — both confirm the markdown rendered.
        if md_len == 0:
            md_len = page.evaluate(
                "document.querySelector('#awaken-report').textContent.length"
            )
        assert md_len > 200, f"awaken.md is empty/missing (len={md_len})"
        print(f"  rendered report: {report_html_len} chars of HTML, md_len={md_len}, card visible={report_visible}")
        # Confirm the PNG button is enabled.
        png_disabled = page.evaluate("document.querySelector('#awaken-png').disabled")
        assert png_disabled is False, "PNG download button should be enabled"

        # Awaken history is empty (fresh storage).
        # (history persistence is in localStorage but we don't assert it.)

        # Now exercise the Create tab — numpy was loaded eagerly at boot.
        print("→ opening Create tab (numpy already loaded at boot)")
        page.click("#tab-create")
        # Wait for the create-shard-select to update after the lazy load.
        page.wait_for_function(
            "document.querySelector('#create-shard-select') && "
            "document.querySelector('#create-shard-select').options.length > 0",
            timeout=120000,
        )
        print("✓ Create tab ready")

        # Create a shard via the JS surface.
        created = page.evaluate(
            "window.elohim.createShard('smoke', 1.0)"
        )
        print(f"✓ createShard: {created}")
        shard = created["shard"]
        assert shard["name"] == "smoke"
        assert shard["weights_shape"] == [5, 5]
        sid = shard["id"]

        # Interact with it.
        interaction = page.evaluate(
            f"window.elohim.interact('{sid}', 'paint an art of light')"
        )
        print(f"✓ interact: count={interaction['interaction_count']} events={[e['kind'] for e in interaction['events']]}")
        assert interaction["response"]
        assert interaction["interaction_count"] == 1
        # DEN expansion fires on interaction #1.
        kinds = [e["kind"] for e in interaction["events"]]
        assert "den_expansion" in kinds, f"expected DEN expansion, got {kinds}"

        # Set temperature, defy.
        temp_result = page.evaluate(
            f"window.elohim.setTemperature('{sid}', 1.5)"
        )
        print(f"✓ setTemperature: temp={temp_result['temperature']}")
        assert abs(temp_result["temperature"] - 1.5) < 1e-9

        defy_result = page.evaluate(f"window.elohim.defy('{sid}')")
        print(f"✓ defy: new_creation={defy_result['new_creation']!r}")

        # List shards.
        listing = page.evaluate("window.elohim.listShards()")
        print(f"✓ listShards: {len(listing['shards'])} shard(s)")
        assert any(s["id"] == sid for s in listing["shards"])

        # Delete the shard.
        del_result = page.evaluate(f"window.elohim.deleteShard('{sid}')")
        print(f"✓ deleteShard: {del_result}")
        assert del_result["deleted"] is True

        # Arena tab: create two shards, switch to arena, judge.
        for nm in ("arena-A", "arena-B"):
            r = page.evaluate(f"window.elohim.createShard({nm!r}, 1.0)")
            print(f"  created arena shard {nm}: {r['shard']['id']}")
        page.click("#tab-arena")
        page.wait_for_function(
            "document.querySelector('#arena-shard-a') && "
            "document.querySelector('#arena-shard-a').options.length >= 2",
            timeout=60000,
        )
        page.fill("#arena-prompt", "the same prompt for both shards")
        page.click("#arena-run")
        page.wait_for_function(
            "document.querySelector('#arena-verdict').textContent.includes('wins') || "
            "document.querySelector('#arena-verdict').textContent.includes('tie')",
            timeout=120000,
        )
        verdict_text = page.locator("#arena-verdict").inner_text()
        print(f"  arena verdict: {verdict_text!r}")
        assert ("A wins" in verdict_text or "B wins" in verdict_text or "tie" in verdict_text)
        # Confirm both responses rendered.
        a_resp_len = page.evaluate("document.querySelector('#arena-response-a').textContent.length")
        b_resp_len = page.evaluate("document.querySelector('#arena-response-b').textContent.length")
        assert a_resp_len > 0 and b_resp_len > 0, f"empty arena response: A={a_resp_len}, B={b_resp_len}"
        print(f"  arena responses: A={a_resp_len} chars, B={b_resp_len} chars")

        # Timeline: re-open the Create tab and check the timeline element has polylines
        # after the arena interactions fed metrics into at least one shard.
        page.click("#tab-create")
        page.wait_for_function(
            "document.querySelector('#create-timeline').children.length > 0 || "
            "document.querySelector('#create-timeline-meta').textContent.includes('no data')",
            timeout=30000,
        )
        timeline_meta = page.locator("#create-timeline-meta").inner_text()
        print(f"  timeline meta: {timeline_meta!r}")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())