"""Measure cold-cache boot time for the elohim-web SPA.

Reports three timings, because they answer different questions:
  dom_loaded   — navigationStart → DOMContentLoaded (what D-J21 literally
                 specifies; the HTML/CSS parse cost)
  pyodide_ready— navigationStart → #boot.hidden (the real user-visible
                 boot: Pyodide fetch + module exec + first awaken)
  first_paint  — navigationStart → first contentful paint

Each sample uses a fresh browser context with the HTTP cache disabled,
so it is a genuine cold-cache measurement.

Usage: python3 boot_bench.py <url> [samples]
"""
import sys
import statistics
import time

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8780/"
SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 3

rows = []
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    for i in range(SAMPLES):
        ctx = browser.new_context()
        # Cold cache: refuse every cached response.
        ctx.route("**/*", lambda r: r.continue_(
            headers={**r.request.headers,
                     "Cache-Control": "no-cache, no-store, must-revalidate",
                     "Pragma": "no-cache"}))
        page = ctx.new_page()
        t0 = time.time()
        page.goto(URL, wait_until="commit")
        page.wait_for_selector("#boot.hidden", state="attached", timeout=300000)
        wall = (time.time() - t0) * 1000
        m = page.evaluate("""() => {
          const nav = performance.timing;
          const dcl = nav.domContentLoadedEventEnd - nav.navigationStart;
          let fcp = null;
          try {
            const e = performance.getEntriesByType('paint')
                       .find(x => x.name === 'first-contentful-paint');
            if (e) fcp = e.startTime;
          } catch (_) {}
          return {dcl: dcl, fcp: fcp};
        }""")
        rows.append({"dcl": m["dcl"], "fcp": m["fcp"], "wall": wall})
        print(f"  sample {i+1}: dom_loaded={m['dcl']:.0f}ms  "
              f"fcp={m['fcp'] if m['fcp'] is None else round(m['fcp'])}ms  "
              f"boot_hidden={wall:.0f}ms")
        ctx.close()
    browser.close()

print()
for key, label in (("dcl", "dom_loaded  (D-J21 metric)"),
                   ("wall", "boot_hidden (user-visible)")):
    vals = [r[key] for r in rows]
    print(f"{label:<28} median {statistics.median(vals):7.0f} ms  "
          f"min {min(vals):7.0f}  max {max(vals):7.0f}")
print()
print("D-J21 threshold: dom_loaded < 8000 ms (cold cache)")
print("VERDICT:", "PASS" if statistics.median([r['dcl'] for r in rows]) < 8000
      else "FAIL")
