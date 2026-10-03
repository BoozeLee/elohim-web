"""WebMCP probe harness — the instrument the whole contract work is measured with.

The app's native WebMCP path is gated on a Chromium internal feature flag, which
makes it a poor permanent gate: rename the flag upstream and the suite either
dies or, worse, silently passes against the `window.elohimMcp` polyfill while
proving nothing.

So the default mode installs a spec-shaped fake `ModelContext` on the page
before any app script runs. It is deliberately *not* a rubber stamp — its
`registerTool` throws the same error real Chromium throws when the required
`execute` member is missing, so the exact bug the spec found fails here too.

`real_runtime=True` opts into genuine Chromium for the conformance check.
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

DEFAULT_URL = "http://127.0.0.1:8790/"

# Copied verbatim from Chromium 1243 (2026-10-03). The fake reproduces this so
# that a tool using `handler` instead of `execute` fails under test exactly as
# it would in a real browser. Weakening this message would let the original bug
# pass.
_REAL_REGISTER_ERROR = (
    "Failed to execute 'registerTool' on 'ModelContext': "
    "Failed to read the 'execute' property from 'ModelContextTool': "
    "Required member is undefined."
)

# Templated on {target}. Installs the fake on one of Navigator.prototype,
# Document.prototype or Window.prototype so the resolver's fallback chain can
# be exercised one candidate at a time.
FAKE_MC_SCRIPT = """
(() => {{
  const TARGET = "{target}";
  const store = new Map();
  const mc = {{
    _store: store,
    async getTools() {{ return [...store.values()]; }},
    async executeTool(tool, argsJson) {{
      return tool.execute(JSON.parse(argsJson));
    }},
    registerTool(def) {{
      if (typeof def.execute !== 'function') {{
        throw new TypeError({error});
      }}
      store.set(def.name, def);
    }},
  }};
  const proto = TARGET === 'navigator' ? Navigator.prototype
              : TARGET === 'document'  ? Document.prototype
              : Window.prototype;
  Object.defineProperty(proto, 'modelContext',
                       {{ get: () => mc, configurable: true }});
}})();
"""


def launch_args(real_runtime: bool) -> list[str]:
    """Chromium args. The feature flag is opt-in and used only by Tier 2."""
    args = ["--no-sandbox"]
    if real_runtime:
        args.append("--enable-features=WebMCPTesting")
    return args


class ModelContextProbe:
    """Launches Chromium and optionally installs the fake ModelContext.

    fake_target selects which object receives the fake so each resolver
    fallback can be asserted independently.
    """

    def __init__(self, *, real_runtime: bool = False,
                 fake_target: str = "navigator", url: str = DEFAULT_URL):
        if fake_target not in ("navigator", "document", "window"):
            raise ValueError(f"bad fake_target: {fake_target!r}")
        self.real_runtime = real_runtime
        self.fake_target = fake_target
        self.url = url
        self._pw = None
        self._browser = None
        self.page = None

    def __enter__(self) -> "ModelContextProbe":
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True, args=launch_args(self.real_runtime))
        ctx = self._browser.new_context()
        ctx.route("**/*", lambda r: r.continue_(
            headers={**r.request.headers, "Cache-Control": "no-cache"}))
        # Register on the CONTEXT, not the page: a page-level init script
        # only fires for documents created *after* it is added, so it misses
        # the page's initial about:blank. That left navigator.modelContext
        # undefined and made the self-test fail for the wrong reason.
        if not self.real_runtime:
            ctx.add_init_script(FAKE_MC_SCRIPT.format(
                target=self.fake_target, error=_JS_STR(_REAL_REGISTER_ERROR)))
        self.page = ctx.new_page()
        return self

    def __exit__(self, *exc) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._browser = None
        self._pw = None
        self.page = None


def _JS_STR(s: str) -> str:
    """Quote a Python string as a JS string literal."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ── Self-tests. Run: python3 webmcp_probe.py ────────────────────────

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


def test_fake_lands_on_requested_target():
    for target in ("navigator", "document", "window"):
        with ModelContextProbe(fake_target=target) as p:
            got = p.page.evaluate(f"() => !!{target}.modelContext")
            assert got, f"fake not installed on {target}"


if __name__ == "__main__":
    test_fake_rejects_handler_instead_of_execute()
    test_fake_lands_on_requested_target()
    print("webmcp_probe self-tests passed")
