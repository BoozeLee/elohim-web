// Jev audit (Push 23): extracted verbatim from the inline
// <script type="module"> block in index.html. D-J20 — one of
// exactly two extracted files. The script has no JS `import`/
// `export` and no top-level `await`, but it IS still loaded as a
// module so it keeps deferred execution and its own scope — do not
// drop type="module". The Pyodide boot sequence inside is
// unchanged, and the FOUC theme script in <head> stays inline.
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const toast = (msg, kind = "") => {
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.textContent = msg;
  $("#toast-host").appendChild(el);
  setTimeout(() => el.remove(), 3500);
};

// ─── Push 20 — Theme toggle (D-J14-prelude) ─────────────────────────
// Click handler + keyboard shortcut 't' (when no input is focused).
// Persists to localStorage["elohim.theme"]. The data-theme attribute is
// already set on <html> by the inline FOUC script in <head>.
function toggleTheme() {
  const html = document.documentElement;
  const cur = html.dataset.theme || "dark";
  const next = cur === "dark" ? "light" : "dark";
  html.dataset.theme = next;
  try { localStorage.setItem("elohim.theme", next); } catch (e) { /* ignore */ }
}
document.addEventListener("keydown", (e) => {
  // 't' or 'T' shortcut, only when no input/textarea is focused.
  if ((e.key === "t" || e.key === "T") &&
      !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "")) {
    toggleTheme();
  }
});
const _themeToggleBtn = document.getElementById("theme-toggle");
if (_themeToggleBtn) _themeToggleBtn.addEventListener("click", toggleTheme);

// ═══ Push 25 — ghost stage ══════════════════════════════════════════
// The stage is decorative; it carries no information. The one thing it
// does borrow from the app is the tool count, which is real data and
// already published in tools.manifest.json — so it is read from the live
// table rather than hardcoded, and it would be wrong if the table grew.
(function initGhostStage() {
  const canvas = document.getElementById("ghost-field");
  if (!canvas || typeof window.GhostField !== "function") return;
  const field = new window.GhostField(canvas);
  field.attach();

  const count = document.getElementById("stage-tool-count");
  const paint = () => {
    const n = window.__elohimToolNames ? window.__elohimToolNames().length : null;
    if (count && n) count.textContent = String(n);
  };
  paint();
  // Tool registration is async relative to first paint; re-read once the
  // page has settled rather than guessing a delay.
  document.addEventListener("elohim:tools-ready", paint, { once: true });
  window.addEventListener("load", paint, { once: true });
})();

// The sticky nav sits directly under the sticky masthead, so it needs the
// masthead's REAL height — which is 45px on desktop but 103px on a phone
// once the meta line wraps. A hardcoded offset was wrong at every width
// but one, and the nav slid under the masthead. Measured, not guessed.
(function publishMastheadHeight() {
  const mast = document.querySelector(".masthead");
  if (!mast) return;
  const publish = () => {
    const h = Math.round(mast.getBoundingClientRect().height);
    document.documentElement.style.setProperty("--mast-h", h + "px");
  };
  publish();
  if ("ResizeObserver" in window) new ResizeObserver(publish).observe(mast);
  window.addEventListener("resize", publish, { passive: true });
  // Web fonts land after first paint and change the masthead height.
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(publish);
})();

// ═══ Push 22 — UX copy + onboarding ════════════════════════════════
// Three components, all theme-aware by construction (they read tokens
// from design-tokens.css) and all keyboard-reachable.

// ─── HELP_TEXT ───────────────────────────────────────────────────────
// One entry per top-level panel. Keys match data-tab on the tab strip.
// Copy is Jev-locked: it states what the panel does, not how to use it.
const HELP_TEXT = {
  awaken:  "Click 'awaken' to run the elohim_summoning pipeline. " +
           "Each invocation gets a deterministic seal.",
  create:  "Create + evolve a 5×5 numpy shard. 'defy' injects " +
           "ghost-side perturbations that the shard integrates.",
  codex:   "Run alien_codex to produce a Xenomath artifact — five " +
           "representations (vector, negabinary, gaussian, " +
           "quaternion, LWE) plus an XOR-pair integrity check.",
  arena:   "Two shards compete on the same prompt; the winner is " +
           "the one whose response is more coherent (judged by " +
           "the elohim verifier).",
  lab:     "Math Discovery Lab — discover symbolic equations, " +
           "simplify expressions, verify conjectures. Uses " +
           "in-browser sympy by default; the FastAPI lab backend " +
           "adds Z3 / Julia / Lean.",
  webmcp:  "Agent surface — 13 WebMCP tools, including the " +
           "elohim_lab_* family.",
  soul:    "Soul File — sign your evocations with Ed25519 (v0.2) " +
           "or sha256-hmac (v0.1). Both schemas coexist.",
  vault:   "Hosted Soul Vault — three tiers (free / indie / team). " +
           "FastAPI backend on http://127.0.0.1:8791.",
  marketplace: "Skill marketplace — Apify Actor scrapes Apify " +
                "Actors; MCPize exposes them via MCP; x402 handles " +
                "per-skill billing.",
};
const HELP_TITLES = {
  awaken: "Awaken", create: "Create shard", arena: "Arena",
  codex: "Alien codex", lab: "Math lab", webmcp: "WebMCP surface",
  soul: "Soul File", vault: "Soul vault", marketplace: "Marketplace",
};

// ─── Status pill ────────────────────────────────────────────────────
// 4-state machine (idle | running | success | error). D-J22 — every
// setStatus() clears the pending linger timer first, so rapid state
// changes cannot interleave and leave the pill stuck mid-fade.
const PILL_ICON = {
  idle: "#i-info", running: "#i-loading",
  success: "#i-success", error: "#i-error",
};
let _pillHideTimer = null;
let _pillShakeTimer = null;

function _pillMount() {
  let pill = document.getElementById("awaken-status-pill");
  if (pill) return pill;
  // Hosted next to the awaken run button so it reads as the outcome of
  // the action the user just took, not as a global banner.
  const host = document.querySelector("#panel-awaken .row");
  if (!host) return null;
  pill = document.createElement("span");
  pill.id = "awaken-status-pill";
  pill.className = "status-pill";
  pill.dataset.state = "idle";
  pill.setAttribute("role", "status");
  pill.innerHTML =
    '<svg class="pill-icon" aria-hidden="true"><use href="assets/icons.svg#i-info"></use></svg>' +
    '<span class="pill-label">ready</span>';
  host.appendChild(pill);
  return pill;
}

function setStatus(state, label) {
  const pill = _pillMount();
  if (!pill) return;
  // D-J22 — latest call wins. Drop any in-flight linger/fade.
  if (_pillHideTimer) { clearTimeout(_pillHideTimer); _pillHideTimer = null; }
  pill.classList.remove("leaving");
  pill.dataset.state = state;

  const use = pill.querySelector("use");
  if (use) use.setAttribute("href", "assets/icons.svg" + PILL_ICON[state]);
  const text = label || state;
  const lbl = pill.querySelector(".pill-label");
  if (lbl) lbl.textContent = text;

  // Screen readers get the same text via the Push 21 live region.
  // Idle never writes, so the region cannot become chatty (D-J22).
  if (state !== "idle") {
    const live = document.getElementById("aria-status");
    if (live) live.textContent = text;
  }

  // D-J19 — shake is opt-in and only on the error transition. The
  // class is removed on animationend so a second error re-triggers it.
  // Any non-error transition also clears it, so a fast error → running
  // sequence cannot leave the pill shaking while it works.
  if (state === "error") {
    pill.classList.remove("motion-error-shake");
    void pill.offsetWidth;   // force reflow to restart the animation
    pill.classList.add("motion-error-shake");
    if (_pillShakeTimer) clearTimeout(_pillShakeTimer);
    _pillShakeTimer = setTimeout(() => {
      pill.classList.remove("motion-error-shake");
    }, 540);
  } else if (pill.classList.contains("motion-error-shake")) {
    if (_pillShakeTimer) { clearTimeout(_pillShakeTimer); _pillShakeTimer = null; }
    pill.classList.remove("motion-error-shake");
  }

  // D-J22 — success lingers 250ms so the user can read the seal, then
  // fades back to idle. Error persists until the next action.
  if (state === "success") {
    _pillHideTimer = setTimeout(() => {
      pill.classList.add("leaving");
      _pillHideTimer = setTimeout(() => {
        pill.classList.remove("leaving");
        pill.dataset.state = "idle";
        const u = pill.querySelector("use");
        if (u) u.setAttribute("href", "assets/icons.svg" + PILL_ICON.idle);
        const l = pill.querySelector(".pill-label");
        if (l) l.textContent = "ready";
      }, 320);
    }, 250);
  }
}

// Expose for the Playwright probe and for future feature wiring.
window.elohimUI = { setStatus, HELP_TEXT };

// ─── Help tooltip (singleton) ────────────────────────────────────────
// One .help-tip element. Opening a new tooltip re-points the same node.
// Dismisses on: re-click the trigger, Escape, or click outside.
const _helpTip = document.getElementById("help-tip");
let _helpTrigger = null;

function _closeHelp() {
  if (!_helpTip || _helpTip.hidden) return;
  _helpTip.hidden = true;
  if (_helpTrigger) {
    _helpTrigger.setAttribute("aria-expanded", "false");
    _helpTrigger = null;
  }
}

function _openHelp(btn) {
  if (!_helpTip) return;
  const key = btn.dataset.help;
  const body = HELP_TEXT[key];
  if (!body) return;                     // no copy yet → stay silent
  if (_helpTrigger === btn && !_helpTip.hidden) { _closeHelp(); return; }

  document.getElementById("help-tip-title").textContent =
    HELP_TITLES[key] || key;
  document.getElementById("help-tip-body").textContent = body;

  // Position below the trigger, clamped to the viewport.
  _helpTip.hidden = false;
  const r = btn.getBoundingClientRect();
  const tw = _helpTip.offsetWidth;
  const th = _helpTip.offsetHeight;
  let left = r.left + window.scrollX;
  let top = r.bottom + window.scrollY + 6;
  // Flip above the trigger if there is no room below.
  if (r.bottom + th + 6 > window.innerHeight) {
    top = r.top + window.scrollY - th - 6;
  }
  // Clamp horizontally so the tip never overflows the right edge.
  const maxLeft = window.scrollX + window.innerWidth - tw - 8;
  if (left > maxLeft) left = maxLeft;
  if (left < window.scrollX + 8) left = window.scrollX + 8;
  _helpTip.style.left = left + "px";
  _helpTip.style.top = top + "px";

  if (_helpTrigger && _helpTrigger !== btn) {
    _helpTrigger.setAttribute("aria-expanded", "false");
  }
  _helpTrigger = btn;
  btn.setAttribute("aria-expanded", "true");
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest?.(".help-btn");
  if (btn) { e.stopPropagation(); _openHelp(btn); return; }
  if (_helpTip && !_helpTip.hidden) _closeHelp();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" || e.key === "Esc") {
    if (_helpTip && !_helpTip.hidden) {
      const t = _helpTrigger;
      _closeHelp();
      if (t) t.focus();     // return focus — keyboard users must not be stranded
    }
  }
});

// ─── Help buttons in panel headers ──────────────────────────────────
// One per top-level panel. Injected here rather than hand-authored in
// 21 card headers so the markup cannot drift out of sync with HELP_TEXT.
// The h2 is wrapped in a .card-head flex row rather than having the
// button appended inside it — .card h2 owns its own margin and font,
// so an inline child would inherit the serif heading scale.
const HELP_TARGETS = ["awaken", "create", "arena", "codex", "lab", "webmcp"];
for (const key of HELP_TARGETS) {
  const panel = document.getElementById("panel-" + key);
  if (!panel) continue;
  const h2 = panel.querySelector(".card h2");
  if (!h2) continue;
  const head = document.createElement("div");
  head.className = "card-head";
  h2.replaceWith(head);
  head.appendChild(h2);
  const btn = document.createElement("button");
  btn.className = "help-btn";
  btn.dataset.help = key;
  btn.setAttribute("aria-expanded", "false");
  btn.setAttribute("aria-controls", "help-tip");
  btn.setAttribute("aria-label", "Help: " + (HELP_TITLES[key] || key));
  btn.textContent = "?";
  head.appendChild(btn);
}

// ─── First-run card (D-J17) ─────────────────────────────────────────
// localStorage flag is the string "1" (never a boolean) so a stale
// `true` from an older build cannot be mistaken for a dismissal.
const _firstRun = document.getElementById("first-run-card");
const _firstRunClose = document.getElementById("first-run-close");
function _firstRunSeen() {
  try { return localStorage.getItem("elohim.first_run_seen") === "1"; }
  catch (e) { return false; }   // private mode → show the hint
}
function _dismissFirstRun() {
  try { localStorage.setItem("elohim.first_run_seen", "1"); } catch (e) { /* ignore */ }
  if (!_firstRun) return;
  _firstRun.classList.add("dismissing");
  const done = () => { if (_firstRun) _firstRun.hidden = true; };
  _firstRun.addEventListener("animationend", done, { once: true });
  // Reduced-motion kills the animation; hide on a timer as a backstop.
  setTimeout(done, 400);
}
if (_firstRun && !_firstRunSeen()) _firstRun.hidden = false;
if (_firstRunClose) _firstRunClose.addEventListener("click", _dismissFirstRun);
window.elohimUI.dismissFirstRun = _dismissFirstRun;
window.elohimUI.showFirstRun = () => { if (_firstRun) _firstRun.hidden = false; };

// Inline copy feedback — sits next to the button for 1.8s so the
// user sees "copied ✓" without having to find the toast.
async function copyText(text, buttonEl, label = "copied") {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    // Older browsers / file:// / insecure context — fall back to a
    // hidden textarea + execCommand("copy").
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (_) { /* ignore */ }
    ta.remove();
  }
  if (buttonEl) {
    // Insert (or reuse) a sibling pill that briefly says "copied ✓".
    let pill = buttonEl.nextElementSibling;
    if (!pill || !pill.classList?.contains("copy-pill")) {
      pill = document.createElement("span");
      pill.className = "copy-pill";
      pill.setAttribute("aria-live", "polite");
      pill.textContent = `${label} ✓`;
      buttonEl.insertAdjacentElement("afterend", pill);
    } else {
      pill.textContent = `${label} ✓`;
      pill.classList.remove("show");
      void pill.offsetWidth;
    }
    pill.classList.add("show");
    setTimeout(() => pill.classList.remove("show"), 1800);
  }
  toast(`${label} ✓`);
  return true;
}

const boot = {
  setStatus: (msg, pct) => {
    $("#boot-status").textContent = msg;
    if (typeof pct === "number") $("#boot-fill").style.width = pct + "%";
  },
  fail: (msg) => {
    $("#boot-status").textContent = "boot failed.";
    $("#boot-err").textContent = msg;
    $("#boot-fill").style.background = "var(--red)";
  },
  done: () => {
    $("#boot").classList.add("hidden");
  },
};

// --- tabs (Push 21: ARIA tabs pattern + keyboard arrow nav per D-J14) ---
function selectTab(tabEl, opts = {}) {
  if (!tabEl || tabEl.disabled) return;
  const tabs = $$(".tab");
  tabs.forEach((x) => {
    const isActive = x === tabEl;
    x.classList.toggle("active", isActive);
    x.setAttribute("aria-selected", isActive ? "true" : "false");
    x.tabIndex = isActive ? 0 : -1;
  });
  $$(".panel").forEach((p) =>
    p.classList.toggle("active", p.id === "panel-" + tabEl.dataset.tab)
  );
  // Optional: focus the new tab when triggered by keyboard nav (D-J14)
  if (opts.focus) tabEl.focus();
}
// Click handler — unchanged behaviour, now goes through selectTab.
$$(".tab").forEach((t) => t.addEventListener("click", () => selectTab(t)));
// Keyboard handler — Left/Right cycle, Home/End jump, Enter/Space activate.
$$(".tabs")[0]?.addEventListener("keydown", (e) => {
  const tabs = Array.from($$(".tab")).filter((x) => !x.disabled);
  if (tabs.length === 0) return;
  const currentIdx = tabs.findIndex((x) => x === document.activeElement);
  if (currentIdx < 0) return; // focus isn't on a tab — ignore
  let nextIdx = currentIdx;
  switch (e.key) {
    case "ArrowLeft":
    case "ArrowUp":    nextIdx = Math.max(0, currentIdx - 1); break;
    case "ArrowRight":
    case "ArrowDown":  nextIdx = Math.min(tabs.length - 1, currentIdx + 1); break;
    case "Home":       nextIdx = 0; break;
    case "End":        nextIdx = tabs.length - 1; break;
    case "Enter":
    case " ":         selectTab(tabs[currentIdx]); e.preventDefault(); return;
    default: return;
  }
  e.preventDefault();
  selectTab(tabs[nextIdx], { focus: true });
});

// --- pyodide boot ---

const PYODIDE_VERSION = "0.27.8";
const PYODIDE_INDEX = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

async function bootPyodide() {
  boot.setStatus(`loading pyodide ${PYODIDE_VERSION}…`, 5);

  let loadPyodide;
  try {
    ({ loadPyodide } = await import(`${PYODIDE_INDEX}pyodide.mjs`));
  } catch (e) {
    throw new Error(`failed to load pyodide module: ${e.message}`);
  }

  const localPyodide = await loadPyodide({ indexURL: PYODIDE_INDEX });
  window.__pyodide = localPyodide;
  // Expose the real Pyodide version so bridge.version() can surface
  // it instead of reporting "unknown".
  try {
    localPyodide.runPython(
      `import sys as _sys\n_sys._pyodide_version = "${localPyodide.version}"\n`
    );
  } catch (_) { /* non-fatal */ }
  boot.setStatus("pyodide ready · fetching python source…", 30);
  // Surface real Pyodide / Python versions in the footer.
  try {
    document.getElementById("footer-pyodide-version").textContent =
      localPyodide.version || "unknown";
  } catch (_) { /* ignore */ }
  try {
    document.getElementById("footer-python-version").textContent =
      localPyodide.runPython("import sys; sys.version.split()[0]");
  } catch (_) { /* ignore */ }

  // The Python source ships as plain .py files in /py/. Load every file
  // into Pyodide's MEMFS under /home/py/ then import.
  const SRC_ROOT = "/home/py";
  localPyodide.FS.mkdirTree(SRC_ROOT);

  const PY_PACKAGES = [
    "elohim_summoning",
    "elohim_enhanced",
    "elohim_webapp",
  ];
  const filesPerPkg = {
    elohim_summoning: [
      "cli.py", "core.py", "sigil.py",
      "collatz.py", "logstar.py", "padic.py", "parry.py",
      "pisot.py", "unicorn.py",
    ],
    elohim_enhanced: [
      "extras.py", "cli.py", "creative.py",
      "engine.py", "memory.py", "reflection.py", "shard.py",
      "types.py",
    ],
    elohim_webapp: [
      "bridge.py",
      "_pure25519.py",
      "lab_seal.py",
    ],
  };

  // Fetch every file in parallel; Pyodide writeFile later.
  const fetched = {};
  let loaded = 0;
  const total = Object.values(filesPerPkg).reduce((a, b) => a + b.length, 0);
  await Promise.all(PY_PACKAGES.flatMap((pkg) => {
    localPyodide.FS.mkdirTree(`${SRC_ROOT}/${pkg}`);
    return filesPerPkg[pkg].map(async (f) => {
      const url = `py/${pkg}/${f}`;
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
      fetched[`${pkg}/${f}`] = await r.text();
      loaded++;
      boot.setStatus(`fetched ${loaded}/${total} python files…`, 30 + Math.floor((loaded / total) * 50));
    });
  }));

  // Now write everything into MEMFS.
  for (const [path, src] of Object.entries(fetched)) {
    localPyodide.FS.writeFile(`${SRC_ROOT}/${path}`, src);
  }
  boot.setStatus("importing python packages…", 85);

  await localPyodide.runPythonAsync(`
import sys
sys.path.insert(0, "${SRC_ROOT}")
import elohim_summoning
import elohim_webapp.bridge as bridge
  `);

  // Eagerly load numpy + sympy + every elohim_enhanced submodule. We do
  // this at boot (not lazily) because the first call to
  // loadPackagesFromImports from inside an event handler can hang on
  // Pyodide 0.27.x — pulling it out of the click flow keeps the UX snappy
  // and avoids that race.
  boot.setStatus("loading numpy (one-time, ~5MB)…", 85);
  await localPyodide.loadPackagesFromImports("import numpy");
  // Push 18 (Lab tab) needs sympy for in-browser symbolic-regression and
  // verification. Pyodide 0.27.x does NOT ship sympy by default; load
  // it eagerly at boot so the first lab action is snappy.
  boot.setStatus("loading sympy (one-time, ~20MB)…", 88);
  await localPyodide.loadPackage("sympy");
  await localPyodide.runPythonAsync(`
import elohim_enhanced.cli
import elohim_enhanced.creative
import elohim_enhanced.engine
import elohim_enhanced.memory
import elohim_enhanced.reflection
import elohim_enhanced.shard
import elohim_enhanced.types
import elohim_enhanced.extras
`);
  localPyodide.__elohim_numpy_loaded = true;

  // Push 15: Soul File v0.2 Ed25519 uses the vendored pure-Python
  // pure25519 module that ships with bridge.py. No Pyodide wheel needed;
  // no extra boot cost. The bridge tries nacl.signing first and falls
  // back to _pure25519 automatically.

  boot.setStatus("verifying canonical seal…", 92);
  $("#boot-seal").textContent = "computing seal…";

  // Run seal verification through bridge._invoke so we use bridge's own
  // json module (the runPython global scope doesn't have json imported).
  // Pyodide's runPython returns the value of the last expression — no
  // explicit `return` is allowed at module level.
  let sealCheckJson;
try {
    // _invoke is async because vault_call is a coroutine; we use the
    // synchronous _invoke_sync helper for the boot tripwire (verify_seal_multi
    // is sync and never returns a coroutine).
    sealCheckJson = localPyodide.runPython(`bridge._invoke_sync("verify_seal_multi")`);
  } catch (e) {
    boot.fail(`verify_seal_multi threw: ${e.message || e}`);
    return null;
  }
  let sealCheck;
  try {
    sealCheck = JSON.parse(sealCheckJson);
  } catch (e) {
    boot.fail(`JSON.parse of seal-check failed: ${e.message || e}\nraw: ${String(sealCheckJson).slice(0, 200)}`);
    return null;
  }
  if (!sealCheck.overall_ok) {
    const failed = sealCheck.checks.filter(c => !c.ok).map(c => c.name).join(", ");
    boot.fail(
      `seal tripwire failed on: ${failed}\n` +
      JSON.stringify(sealCheck.checks, null, 2)
    );
    return null;
  }

  $("#boot-seal").textContent =
    "seal: " + sealCheck.canonical_seal.slice(0, 16) +
    " · " + sealCheck.checks.filter(c => c.ok).length + "/" + sealCheck.checks.length + " checks ✓";
  boot.setStatus("ready · all systems nominal", 500);
  setTimeout(boot.done, 250);
  return localPyodide;
}

let pyodide = null;
let bridgeReady = false;
window.__pyodide = null; // exposed for debugging via devtools

async function ensurePyodide() {
  if (pyodide) return pyodide;
  pyodide = await bootPyodide();
  window.__pyodide = pyodide;
  return pyodide;
}

// Wrap a Python callable so JS gets a plain object back (no PyProxy leak).
// We always go via bridge._invoke(name, kwargs) — Python accepts them either as
// keyword-only or keyword-or-positional.
async function call(name, kwargs = {}) {
  await ensurePyodide();
  if (!pyodide) throw new Error("pyodide failed to initialise");
  try {
    // _invoke is async (vault_call is a coroutine); use runPythonAsync.
    // Both async and sync bridge functions return synchronously when
    // awaited — _invoke always awaits the coroutine internally.
    const kwargsJson = JSON.stringify(kwargs || {});
    const result = await pyodide.runPythonAsync(
      `import json as _e_j\n` +
      `_e_r = bridge._invoke(${JSON.stringify(name)}, [], _e_j.loads(${JSON.stringify(kwargsJson)}))\n` +
      `_e_r`
    );
    if (typeof result === "string") {
      try { return JSON.parse(result); } catch { return result; }
    }
    return result;
  } catch (e) {
    throw new Error(e.message || String(e));
  }
}

// Alias kept for clarity at the call site — `call()` is now always async.
const callAsync = call;

const elohim = {
  version: () => call("version"),
  awaken: (invocation, no_svg = false) =>
    call("awaken", { invocation, no_svg, nonce: freshNonce("awaken") }),
  listShards: () => call("list_shards"),
  createShard: (name, temperature) =>
    call("create_shard", { name, temperature, nonce: freshNonce("create") }),
  getShard: (id) => call("get_shard", { shard_id: id }),
  deleteShard: (id) => call("delete_shard", { shard_id: id }),
  interact: (id, prompt) =>
    call("interact", { shard_id: id, prompt, nonce: freshNonce("interact") }),
  setTemperature: (id, temperature) =>
    call("set_temperature", { shard_id: id, temperature }),
  defy: (id) => call("defy", { shard_id: id, nonce: freshNonce("defy") }),
  sealMessage: (plaintext, channel) =>
    call("seal_message", {
      plaintext, channel: channel || "awaken",
    }),
  openSeal: (ciphertext, nonce, channel, seal) =>
    call("open_seal", {
      ciphertext, nonce, channel: channel || "awaken", seal,
    }),
  ghostReply: (ciphertext, nonce, channel, invocation) =>
    call("ghost_reply", {
      ciphertext, nonce, channel: channel || "awaken",
      invocation: invocation || null,
      nonce_seed: freshNonce("reply"),
      prior: [],
    }),
  vision: (invocation, seal, palette) =>
    call("vision_for", {
      invocation, seal, palette,
    }),
  // Phase 17 marketplace: thin wrapper around the local bridge.
  // Determinism contract: same invocation → same codex_seal as the
  // Apify Actor and MCP server (verified by the smoke harness).
  alienCodex: (invocation) =>
    call("alien_codex", { invocation, nonce: freshNonce("codex") }),
  // Math Discovery Lab (Push 18) — thin wrappers around the local
  // sympy-only bridge. Heavy Z3 / Julia / Lean features live on the
  // monorepo's `elohim-web lab` FastAPI subcommand (Push 18b+).
  labVersion: () => call("lab_version"),
  labDatasets: () => call("lab_builtin_datasets"),
  labDataset: (name) => call("lab_builtin_dataset", { name }),
  labDiscover: (dataset, opts) =>
    call("lab_discover", { dataset, target_column: "y", operators: null, seed: 0, ...(opts || {}) }),
  labSimplify: (expression) => call("lab_simplify", { expression_str: expression }),
  labVerify: (expression, mode, property) =>
    call("lab_verify", {
      expression_str: expression,
      mode: mode || "sympy",
      property: property || "nonnegative",
    }),
  // Soul File (Push 14 v0.1 + Push 15 v0.2) — portable, signed agent
  // identity. Mirrors live in localStorage under elohim.soul.*; export
  // reads them and signs an envelope (v0.1 sha256-hmac by default, v0.2
  // Ed25519 if a signing_key_b64 is supplied). Import replaces the mirror
  // atomically.
  soulExport: (agent_name, passphrase, signing_key_b64) =>
    call("soul_export", {
      agent_name: agent_name || null,
      passphrase: passphrase || null,
      evocations: null,
      sealed_messages: null,
      codex_provenance: null,
      signing_key_b64: signing_key_b64 || null,
    }),
  soulImport: (payload, passphrase) =>
    call("soul_import", { payload, passphrase: passphrase || null }),
  soulVerify: (payload, passphrase) =>
    call("soul_verify", { payload, passphrase: passphrase || null }),
  soulKeygen: () => call("soul_keygen"),
  // Phase 16 vault: thin HTTP wrapper over the elohim-vault FastAPI
  // service. Default base is http://127.0.0.1:8791 (local dev).
  // We route via the browser's native fetch (not Pyodide's bridge) so
  // the JSON serialization stays in JS-land and we avoid the cross-
  // stack coroutine dance. mode:'cors' + credentials:'omit' are
  // explicit because Chromium blocks same-host-different-port fetches
  // without them.
  vaultCall: async (method, path, body) => {
    const base = (document.getElementById("vault-base") || {}).value
                  || "http://127.0.0.1:8791";
    const url = base.replace(/\/$/, "") + path;
    const init = {
      method,
      mode: "cors",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
    };
    if (body !== null && body !== undefined) {
      init.body = JSON.stringify(body);
    }
    try {
      const r = await fetch(url, init);
      const text = await r.text();
      let parsed;
      try { parsed = JSON.parse(text); } catch { parsed = { ok: r.ok, raw: text }; }
      if (!r.ok) {
        return {
          ok: false,
          error: (parsed && (parsed.detail || parsed.error)) || text,
          status: r.status,
          method, path,
        };
      }
      return parsed;
    } catch (e) {
      return { ok: false, error: `vaultCall failed: ${e.message || e}`,
               method, path };
    }
  },
  // Push 18bc — Math Discovery Lab local backend proxy.
  // Mirrors vaultCall but defaults to the lab port (8793) and lets the
  // operator toggle the SPA between in-browser sympy and the local
  // FastAPI surface.
  labCall: async (method, path, body) => {
    const base = (document.getElementById("lab-backend") || {}).value
                  || "http://127.0.0.1:8793";
    const url = base.replace(/\/$/, "") + path;
    const init = {
      method,
      mode: "cors",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
    };
    if (body !== null && body !== undefined) {
      init.body = JSON.stringify(body);
    }
    try {
      const r = await fetch(url, init);
      const text = await r.text();
      let parsed;
      try { parsed = JSON.parse(text); } catch { parsed = { ok: r.ok, raw: text }; }
      if (!r.ok) {
        return {
          ok: false,
          error: (parsed && (parsed.detail && parsed.detail.error || parsed.detail || parsed.error)) || text,
          status: r.status,
          method, path,
        };
      }
      return parsed;
    } catch (e) {
      return { ok: false, error: `labCall failed: ${e.message || e}`,
               method, path, backend_offline: true };
    }
  },
  labBackendStatus: async () => {
    return elohim.labCall("GET", "/api/lab/healthz");
  },
};

// Per-call entropy: every interactive bridge call carries a fresh nonce
// so each invocation produces a distinct artifact. The tripwire calls
// (verify_seal_multi, version) don't pass nonces, so the canonical
// seal for "ELOHIM:AWAKEN" stays stable across machines and runs.
function freshNonce(tag) {
  return `${tag}.${performance.now().toFixed(3)}.${
    Math.random().toString(36).slice(2, 10)
  }`;
}

window.elohim = elohim;

// Parse sharable URL deep links from `location.search`. Supported params:
//   ?invocation=foo  → after boot, run awaken("foo") on the Awaken tab
//   ?shard=<id>      → after boot, switch to the Create tab and select the shard
//   ?tab=awaken|create|arena  → open the named tab on boot
function readDeepLinks() {
  const out = {};
  const params = new URLSearchParams(location.search);
  if (params.has("invocation")) out.invocation = params.get("invocation");
  if (params.has("shard")) out.shard = params.get("shard");
  if (params.has("tab")) out.tab = params.get("tab");
  return out;
}

(async function () {
  try {
    pyodide = await bootPyodide();
    if (!pyodide) return;

    // Header metadata once boot is done.
    try {
      const v = await elohim.version();
      $("#meta-info").textContent = `v${v.version} · elohim_enhanced v${v.enhanced_version} · py ${v.python} · pyodide`;
      $("#header-seal").textContent = "seal: " + v.canonical_seal.slice(0, 16) + "…";
      bridgeReady = true;
    } catch (e) {
      console.error("version() failed:", e);
    }

    // Dispatch any sharable URL deep links.
    const links = readDeepLinks();
    if (links.invocation) {
      $("#awaken-invocation").value = links.invocation;
      // Default tab to awaken if no explicit tab given.
      links.tab = links.tab || "awaken";
    }
    if (links.tab) {
      const tabMap = { awaken: "tab-awaken", create: "tab-create", arena: "tab-arena" };
      const tabId = tabMap[links.tab];
      if (tabId) {
        // For tabs that need numpy, click them so their handler loads deps.
        if (links.tab === "create" || links.tab === "arena") {
          const t = $("#" + tabId);
          if (t && !t.disabled) t.click();
        } else {
          $$(".tab").forEach(x => x.classList.toggle("active", x.id === tabId));
          $$(".panel").forEach(p => p.classList.toggle("active", p.id === "panel-" + links.tab));
        }
      }
    }
    if (links.shard) {
      // The shard selection lives on the Create panel. If the panel isn't
      // active yet, queue the selection for after the user opens it.
      window.__pendingShardId = links.shard;
      // Best effort: if the Create panel is now active and has a populated
      // select, set it directly.
      const sel = $("#create-shard-select");
      if (sel && sel.options.length > 0) {
        const has = Array.from(sel.options).some(o => o.value === links.shard);
        if (has) {
          sel.value = links.shard;
          activeShardId = links.shard;
          refreshDashboard();
        }
      }
    }
    if (links.invocation) {
      // Auto-run awaken with the invocation from the URL.
      try { await runAwaken(false); }
      catch (e) { console.error("deep-link awaken failed:", e); }
    }
  } catch (e) {
    boot.fail(e.message || String(e));
    console.error("boot failed:", e);
  }
})();

// --- helpers ---

async function ensureEnhanced() {
  await ensurePyodide();
  // Numpy + elohim_enhanced are loaded eagerly during bootPyodide(). This
  // function exists as a defensive shim so call sites read clearly and
  // can be reused if we ever switch back to lazy loading.
  if (!pyodide || !pyodide.__elohim_numpy_loaded) {
    throw new Error(
      "numpy was not loaded at boot — the deployment is unsound. " +
      "Open the dev console and check boot logs."
    );
  }
}

// ============ AWAKEN ============

let lastAwaken = null;
let ghostCounter = 0;
let lastSeal = null;

// Apply the per-forge palette as CSS custom properties so every part of
// the page that reads --ghost-accent etc. recolours itself when a new
// invocation completes. This is how variety becomes visible.
function applyPalette(palette) {
  if (!Array.isArray(palette) || palette.length < 5) return;
  const r = document.documentElement.style;
  r.setProperty("--ghost-accent", palette[0]);
  r.setProperty("--ghost-accent-soft", hexToRgba(palette[0], 0.18));
  r.setProperty("--ghost-accent-glow", hexToRgba(palette[0], 0.55));
  r.setProperty("--ghost-secondary", palette[1]);
  r.setProperty("--ghost-tertiary", palette[2]);
  r.setProperty("--ghost-edge", palette[3]);
  r.setProperty("--ghost-ground", palette[4]);
  // Tint the sigil's strokes: rewrite CSS rules once.
  let styleEl = document.getElementById("ghost-palette-style");
  if (!styleEl) {
    styleEl = document.createElement("style");
    styleEl.id = "ghost-palette-style";
    document.head.appendChild(styleEl);
  }
  styleEl.textContent = `
    #awaken-sigil svg path,
    #awaken-sigil svg circle,
    #awaken-sigil svg rect {
      stroke: ${palette[0]} !important;
      filter: drop-shadow(0 0 4px ${hexToRgba(palette[0], 0.4)});
    }
    .seal-display { border-color: ${hexToRgba(palette[1], 0.6)} !important; }
    .response { border-left-color: ${palette[0]} !important; }
    .card h2 { color: ${palette[0]} !important; }
    .card::before, .card::after { border-color: ${palette[0]} !important; opacity: 0.7; }
    button { background: ${palette[0]}; border-color: ${palette[0]}; }
    button:hover { filter: brightness(1.15) drop-shadow(0 0 6px ${hexToRgba(palette[0], 0.4)}); }
  `;
}

function hexToRgba(hex, a) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

$("#awaken-run").addEventListener("click", () => runAwaken(false));
$("#awaken-nosvg").addEventListener("click", () => runAwaken(true));
$("#awaken-stream").addEventListener("click", () => runAwakenStream(false));

async function runAwaken(noSvg) {
  const inv = $("#awaken-invocation").value.trim() || "ELOHIM:AWAKEN";
  $("#awaken-status").textContent = "running…";
  setStatus("running", "summoning ghost…");
  try {
    const r = await elohim.awaken(inv, noSvg);
    lastAwaken = r;
    ghostCounter++;
    applyPalette(r.palette);
    // Reset the vision frame so the user can forge a new vision that
    // matches this ghost's palette and seal.
    resetVisionFrame();
    const sealEl = $("#awaken-seal");
    sealEl.textContent = r.seal || "(no seal)";
    // Re-trigger the stamp animation by removing + re-adding the class.
    sealEl.classList.remove("stamped");
    void sealEl.offsetWidth;
    sealEl.classList.add("stamped");
    const varietyNote = (lastSeal && r.seal && r.seal !== lastSeal)
      ? ` · <span class="ok">different ghost (was ${lastSeal.slice(0, 8)}…)</span>`
      : "";
    $("#awaken-status").innerHTML = `<span class="ok">✓ seal recorded</span> · invocation: ${inv} · ${r.facts ? Object.keys(r.facts).length : 0} facts · ghost #${ghostCounter}${varietyNote}`;
    $("#awaken-copy").disabled = !r.seal;
    $("#awaken-show-facts").disabled = !r.facts;
    if (r.sigil_svg) {
      // Drop the short empty-state reservation now that there is real art
      // to hold — the full-height rule comes back with the content.
      $("#awaken-sigil").classList.remove("is-empty");
      $("#awaken-sigil").innerHTML = r.sigil_svg;
      $("#awaken-download").disabled = false;
      $("#awaken-png").disabled = false;
    } else {
      $("#awaken-sigil").classList.add("is-empty");
      $("#awaken-sigil").innerHTML = '<span style="color:var(--fg-soft)">(no svg — no_svg flag set)</span>';
      $("#awaken-download").disabled = true;
      $("#awaken-png").disabled = true;
    }
    // Render the markdown report inline (replaces raw text dump).
    if (r.md) {
      $("#awaken-report").innerHTML = renderShardMd(r.md, r.seal);
      $("#awaken-report-card").style.display = "block";
    }
    // Stash the seal so the *next* invocation can announce that the
    // ghost has changed.
    if (r.seal) lastSeal = r.seal;
    // Soul File (Push 14): mirror this awakening into the soul log so a
    // subsequent export captures every forge. Best-effort; survives a
    // reload. The mirror key is appended-only and capped at 100.
    if (r.seal) {
      try {
        const arr = JSON.parse(localStorage.getItem("elohim.soul.evocations") || "[]");
        if (!Array.isArray(arr)) throw new Error("not an array");
        arr.push({
          ts: Date.now() / 1000,
          invocation: inv,
          seal: r.seal,
          facts: r.facts ? Object.keys(r.facts).length : 0,
          palette: r.palette || [],
        });
        localStorage.setItem("elohim.soul.evocations", JSON.stringify(arr.slice(-100)));
      } catch (_) { /* localStorage may be disabled; mirror is best-effort */ }
    }
    toast(`awakened · ghost #${ghostCounter} · ${inv.slice(0, 24)}`);
    setStatus("success", r.seal ? `seal recorded: ${r.seal.slice(0, 8)}…` : "awakened");
  } catch (e) {
    $("#awaken-status").innerHTML = `<span class="error">✗ ${e.message}</span>`;
    setStatus("error", `awaken failed: ${e.message}`.slice(0, 60));
    toast("awaken failed: " + e.message, "error");
  }
}

// Streaming awaken: render each section as it finishes computing.
// The bridge returns a JSON list of chunks (header / section / sigil / footer);
// we append each chunk to the report panel in real time.
async function runAwakenStream(noSvg) {
  const inv = $("#awaken-invocation").value.trim() || "ELOHIM:AWAKEN";
  $("#awaken-status").textContent = "streaming…";
  setStatus("running", "streaming…");
  // Reset the report panel and show a live cursor.
  $("#awaken-report").innerHTML = "";
  $("#awaken-report-card").style.display = "block";
  $("#awaken-sigil").innerHTML = '<span style="color:var(--fg-soft)">computing…</span>';
  $("#awaken-seal").textContent = "(streaming…)";
  $("#awaken-copy").disabled = true;
  $("#awaken-download").disabled = true;
  $("#awaken-png").disabled = true;
  $("#awaken-show-facts").disabled = true;
  const start = performance.now();
  try {
    const chunks = await call("stream_awaken", {
      invocation: inv,
      no_svg: noSvg,
      nonce: freshNonce("stream"),
    });
    let seal = null;
    for (let i = 0; i < chunks.length; i++) {
      const c = chunks[i];
      // Render the chunk's text into the report panel.
      const html = renderShardMd(c.text || "", c.seal || null);
      $("#awaken-report").insertAdjacentHTML("beforeend", html);
      // Update seal and sigil as they appear.
      if (c.phase === "footer" && c.seal) {
        seal = c.seal;
        $("#awaken-seal").textContent = seal;
      }
      if (c.phase === "sigil" && c.sigil_svg) {
        $("#awaken-sigil").innerHTML = c.sigil_svg;
        $("#awaken-download").disabled = false;
        $("#awaken-png").disabled = false;
      }
      // Yield to the event loop so the DOM can paint between chunks.
      await new Promise((r) => setTimeout(r, 0));
      $("#awaken-status").textContent =
        `streaming… ${i + 1}/${chunks.length} (${Math.round(performance.now() - start)}ms)`;
    }
    const ms = Math.round(performance.now() - start);
    $("#awaken-status").innerHTML =
      `<span class="ok">✓ streamed ${chunks.length} chunks</span> · ${ms}ms · invocation: ${inv}`;
    if (seal) {
      $("#awaken-copy").disabled = false;
      $("#awaken-show-facts").disabled = false;
      lastAwaken = { seal, sigil_svg: chunks[chunks.length - 1]?.sigil_svg || null,
        md: chunks.map(c => c.text || "").join("\n") };
      // Auto-scroll the report to the bottom.
      $("#awaken-report").scrollTop = $("#awaken-report").scrollHeight;
    }
    toast(`streamed ${chunks.length} chunks in ${ms}ms`);
    setStatus("success", seal ? `streamed · ${seal.slice(0, 8)}…` : "streamed");
  } catch (e) {
    $("#awaken-status").innerHTML = `<span class="error">✗ ${e.message}</span>`;
    setStatus("error", `stream failed: ${e.message}`.slice(0, 60));
    toast("stream failed: " + e.message, "error");
  }
}

// Minimal markdown renderer for elohim_summoning shard.md.
// Recognises the patterns the elohim_summoning.cli emits:
//   §===...\nTITLE\n===...     → <h2>TITLE</h2>
//   I./II./... lines           → <h3>
//   4-space-indented blocks     → <pre>
//   1. numbered lists           → <ol>
//   SHA256 lines                → wrapped in a teal seal banner
$("#ghost-send").addEventListener("click", () => runGhostChannel());
$("#ghost-clear").addEventListener("click", () => {
  $("#ghost-input").value = "";
  $("#ghost-log").innerHTML = "";
});

// Ghost Channel — encrypted message exchange. Compose a line, seal it
// with seal_message, send it via ghost_reply, then verify the reply
// with open_seal so the user sees the round-trip integrity check.
async function runGhostChannel() {
  const text = $("#ghost-input").value.trim();
  if (!text) {
    toast("type a line first", "error");
    return;
  }
  const log = $("#ghost-log");
  const inv = $("#awaken-invocation").value.trim() || "ELOHIM:AWAKEN";
  $("#ghost-send").disabled = true;
  try {
    // 1. Seal the caller's message.
    const sealed = await elohim.sealMessage(text, "awaken");
    // 2. Hand it to the ghost.
    const reply = await elohim.ghostReply(
      sealed.ciphertext, sealed.nonce, "awaken", inv
    );
    // 3. Verify the ghost's reply by opening its seal.
    const opened = await elohim.openSeal(
      reply.reply_envelope.ciphertext,
      reply.reply_envelope.nonce,
      reply.reply_envelope.channel,
      reply.reply_envelope.seal
    );

    // 4. Append to the channel log.
    const entry = document.createElement("div");
    entry.className = "ghost-exchange";
    entry.style.cssText = `
      margin: 12px 0; padding: 12px 14px;
      background: var(--bg-soft); border-radius: 4px;
      border-left: 3px solid var(--ghost-accent, var(--accent));
    `;
    const ok = opened.ok && opened.integrity;
    entry.innerHTML = `
      <div style="font-family: var(--mono); font-size: 11px; color: var(--fg-soft); margin-bottom: 4px; letter-spacing:1px; text-transform:uppercase;">
        <span style="color: var(--ghost-accent, var(--accent));">▸ you</span> · ${sealed.nonce.slice(0, 8)}… · seal ${sealed.seal.slice(0, 8)}…
      </div>
      <div style="margin-bottom: 8px; padding: 8px 10px; background: var(--bg); border-radius: 3px; word-break: break-word; font-size: 13px;">
        ${escapeHtml(sealed.ciphertext.slice(0, 96))}${sealed.ciphertext.length > 96 ? "…" : ""}
      </div>
      <div style="font-family: var(--mono); font-size: 11px; color: var(--fg-soft); margin-bottom: 4px; letter-spacing:1px; text-transform:uppercase;">
        <span style="color: var(--ghost-secondary, var(--teal));">▸ ghost</span> · ${reply.reply_envelope.nonce.slice(0, 8)}… · seal ${reply.reply_envelope.seal.slice(0, 8)}…
        ${ok ? '<span class="ok" style="margin-left:8px;">✓ integrity</span>' : '<span class="error" style="margin-left:8px;">✗ integrity failed</span>'}
      </div>
      <div style="padding: 10px 12px; background: var(--bg); border-radius: 3px; border-left: 2px solid var(--ghost-secondary, var(--teal)); font-family: var(--serif); font-style: italic; font-size: 14px; color: var(--fg-bright);">
        ${escapeHtml(opened.plaintext || "(unreadable)")}
      </div>
    `;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
    $("#ghost-input").value = "";
    // Soul File (Push 14): mirror both sides of the channel into the
    // soul log. Append-only, capped at 100. Caller envelope first,
    // ghost reply second — preserves the exchange order on reload.
    try {
      const arr = JSON.parse(localStorage.getItem("elohim.soul.messages") || "[]");
      if (Array.isArray(arr)) {
        arr.push({ ts: Date.now() / 1000, side: "you", seal: sealed.seal, channel: sealed.channel, nonce: sealed.nonce, mode: sealed.mode });
        arr.push({ ts: Date.now() / 1000, side: "ghost", seal: reply.reply_envelope.seal, channel: reply.reply_envelope.channel, nonce: reply.reply_envelope.nonce, mode: reply.reply_envelope.mode });
        localStorage.setItem("elohim.soul.messages", JSON.stringify(arr.slice(-100)));
      }
    } catch (_) { /* best-effort */ }
    toast(ok ? "ghost replied · seal verified" : "ghost replied · seal check failed", ok ? "" : "error");
  } catch (e) {
    toast("ghost channel failed: " + e.message, "error");
  } finally {
    $("#ghost-send").disabled = false;
  }
}


// ---------- Soul File handlers (Push 14) ----------

async function exportSoul() {
  const status = $("#soul-status");
  const out = $("#soul-output");
  const agentName = $("#soul-agent-name").value.trim() || null;
  const passphrase = $("#soul-passphrase").value || null;
  const useEd25519 = $("#soul-use-ed25519") && $("#soul-use-ed25519").checked;
  let signingKeyB64 = null;
  if (useEd25519) {
    // Reuse the operator's last-generated keypair if still in the closure;
    // otherwise call soul_keygen transparently.
    signingKeyB64 = (window.__soulLastSk || null);
    if (!signingKeyB64) {
      const kg = await elohim.soulKeygen();
      if (!kg.ok) {
        status.innerHTML = `<span class="error">✗ keygen failed: ${escapeHtml(kg.error || "unknown")}</span>`;
        return;
      }
      signingKeyB64 = kg.sk;
      window.__soulLastSk = kg.sk;
      $("#keypair-display").textContent = `pk: ${kg.pk.slice(0, 12)}…`;
    }
  }
  status.innerHTML = '<span class="meta">composing soul…</span>';
  try {
    const r = await elohim.soulExport(agentName, passphrase, signingKeyB64);
    if (!r || !r.ok) {
      status.innerHTML = `<span class="error">✗ ${escapeHtml(r && r.error || "unknown error")}</span>`;
      return;
    }
    const env = r.envelope;
    // Persist as the "last" envelope so the 5th boot tripwire can verify it.
    try {
      localStorage.setItem("elohim.soul.last", JSON.stringify(env));
    } catch (_) { /* private mode */ }
    const schema = env.schema || "elohim-soul/v?";
    const filename = `elohim-soul-${Math.floor(Date.now() / 1000)}.json`;
    const blob = new Blob([JSON.stringify(env, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 0);
    const evs = (env.evocations || []).length;
    const msgs = (env.sealed_messages || []).length;
    let sigKind;
    if (r.schema_v2) {
      sigKind = `Ed25519 (v0.2)${env.signature && env.signature.v1_mac ? " · +v1 fallback" : ""}`;
    } else if (passphrase) {
      sigKind = "HMAC-SHA256";
    } else {
      sigKind = "tamper-check (no passphrase)";
    }
    status.innerHTML = `<span class="ok">✓ exported ${filename}</span> · schema=${schema} · ${evs} evocations · ${msgs} sealed messages · ${sigKind}`;
    out.textContent = JSON.stringify(env, null, 2);
    out.style.display = "block";
    // If the operator exported a v0.2 soul, the sk lives in the closure only;
    // remind them to back it up.
    if (r.schema_v2 && signingKeyB64) {
      toast(`soul exported · v0.2 · save your sk (shown once)`);
    } else {
      toast("soul exported");
    }
  } catch (e) {
    status.innerHTML = `<span class="error">✗ ${escapeHtml(e.message)}</span>`;
  }
}

async function verifySoul() {
  const status = $("#soul-status");
  const out = $("#soul-output");
  const passphrase = $("#soul-passphrase").value || null;
  let blob = localStorage.getItem("elohim.soul.last");
  if (!blob) {
    status.innerHTML = '<span class="meta">no soul in localStorage — export first.</span>';
    return;
  }
  let payload;
  try {
    payload = JSON.parse(blob);
  } catch (e) {
    status.innerHTML = `<span class="error">✗ invalid JSON in elohim.soul.last</span>`;
    return;
  }
  try {
    const v = await elohim.soulVerify(payload, passphrase);
    if (v.ok) {
      status.innerHTML = `<span class="ok">✓ valid · ${v.signature_ok ? "signature ok" : "tamper-check ok"} · schema ${v.schema_ok ? "ok" : "mismatch"}</span>`;
    } else {
      const why = (v.checks || []).map(c => `${c.name}=${c.ok ? "ok" : "fail"}`).join(", ");
      status.innerHTML = `<span class="error">✗ rejected — ${why}</span>`;
    }
    out.textContent = JSON.stringify(v, null, 2);
    out.style.display = "block";
  } catch (e) {
    status.innerHTML = `<span class="error">✗ ${escapeHtml(e.message)}</span>`;
  }
}

async function importSoul() {
  const status = $("#soul-status");
  const out = $("#soul-output");
  const fileInput = $("#soul-file");
  const file = fileInput.files && fileInput.files[0];
  if (!file) {
    toast("pick a soul.json first", "error");
    return;
  }
  const passphrase = $("#soul-passphrase").value || null;
  let payload;
  try {
    const text = await file.text();
    payload = JSON.parse(text);
  } catch (e) {
    status.innerHTML = `<span class="error">✗ invalid JSON: ${escapeHtml(e.message)}</span>`;
    return;
  }
  try {
    const r = await elohim.soulImport(payload, passphrase);
    if (!r.ok) {
      status.innerHTML = `<span class="error">✗ ${escapeHtml(r.error || "import failed")}</span>`;
      out.textContent = JSON.stringify(r, null, 2);
      out.style.display = "block";
      return;
    }
    status.innerHTML = `<span class="ok">✓ imported ${r.evocations_loaded} evocations · ${r.sealed_messages_loaded} sealed messages · agent: ${escapeHtml(r.agent_name || "?")}</span>`;
    out.textContent = JSON.stringify(r, null, 2);
    out.style.display = "block";
    toast("soul imported");
  } catch (e) {
    status.innerHTML = `<span class="error">✗ ${escapeHtml(e.message)}</span>`;
  }
}

$("#soul-export").addEventListener("click", () => exportSoul());
$("#soul-verify").addEventListener("click", () => verifySoul());
$("#soul-import").addEventListener("click", () => importSoul());

// Push 15: Ed25519 keypair generation. We show the pk in the UI and
// stash the sk in a closure variable so the next exportSoul() picks it
// up. The sk never crosses the bridge again after this call.
async function keygenSoul() {
  const status = $("#soul-status");
  const display = $("#keypair-display");
  try {
    const kg = await elohim.soulKeygen();
    if (!kg.ok) {
      status.innerHTML = `<span class="error">✗ keygen failed: ${escapeHtml(kg.error || "unknown")}</span>`;
      return;
    }
    window.__soulLastSk = kg.sk;
    // Auto-check the Ed25519 box so the next export uses it.
    const cb = $("#soul-use-ed25519");
    if (cb) cb.checked = true;
    display.textContent = `pk: ${kg.pk.slice(0, 16)}…`;
    status.innerHTML = `<span class="ok">✓ Ed25519 keypair ready · schema v0.2 will be used · sk is in memory only</span>`;
    toast("ed25519 keypair generated");
  } catch (e) {
    status.innerHTML = `<span class="error">✗ ${escapeHtml(e.message)}</span>`;
  }
}
$("#soul-keygen").addEventListener("click", () => keygenSoul());

// ---------- Vault handlers (Phase 16) ----------

async function vaultStore() {
  const status = $("#vault-status");
  const out = $("#vault-output");
  const base = $("#vault-base").value.trim() || "http://127.0.0.1:8791";
  // Pull the last soul from localStorage.
  const blob = localStorage.getItem("elohim.soul.last");
  if (!blob) {
    status.innerHTML = '<span class="meta">no soul in localStorage — export first.</span>';
    return;
  }
  let payload;
  try { payload = JSON.parse(blob); }
  catch (e) {
    status.innerHTML = `<span class="error">✗ invalid JSON in elohim.soul.last</span>`;
    return;
  }
  status.innerHTML = '<span class="meta">storing…</span>';
  const r = await elohim.vaultCall("POST", "/api/vault/store",
    { payload, is_private: false });
  if (r && r.ok) {
    status.innerHTML = `<span class="ok">✓ stored · ${r.agent_name} · ${r.bytes} bytes · entitlement=${r.entitlement}</span>`;
    out.textContent = JSON.stringify(r, null, 2);
  } else {
    status.innerHTML = `<span class="error">✗ ${escapeHtml((r && (r.error || r.detail)) || "store failed")}</span>`;
  }
  out.style.display = "block";
}

async function vaultLookup() {
  const status = $("#vault-status");
  const out = $("#vault-output");
  const base = $("#vault-base").value.trim() || "http://127.0.0.1:8791";
  const pk = $("#vault-target-pk").value.trim();
  if (!pk) {
    toast("type a pk first", "error");
    return;
  }
  status.innerHTML = '<span class="meta">looking up…</span>';
  const r = await elohim.vaultCall("GET", `/api/vault/lookup/${encodeURIComponent(pk)}`);
  if (r && r.ok) {
    status.innerHTML = `<span class="ok">✓ found · ${r.agent_name} · schema=${r.schema} · entitlement=${r.entitlement}</span>`;
    out.textContent = JSON.stringify(r, null, 2);
  } else {
    status.innerHTML = `<span class="error">✗ ${escapeHtml((r && (r.error || r.detail)) || "lookup failed")}</span>`;
    out.textContent = JSON.stringify(r, null, 2);
  }
  out.style.display = "block";
}

async function vaultList() {
  const status = $("#vault-status");
  const out = $("#vault-output");
  const base = $("#vault-base").value.trim() || "http://127.0.0.1:8791";
  status.innerHTML = '<span class="meta">listing…</span>';
  const r = await elohim.vaultCall("GET", "/api/vault/list_public?limit=10");
  if (r && r.ok) {
    status.innerHTML = `<span class="ok">✓ ${r.total} soul(s) public</span>`;
    out.textContent = JSON.stringify(r, null, 2);
  } else {
    status.innerHTML = `<span class="error">✗ ${escapeHtml((r && r.error) || "list failed")}</span>`;
  }
  out.style.display = "block";
}

$("#vault-store").addEventListener("click", () => vaultStore());
$("#vault-lookup").addEventListener("click", () => vaultLookup());
$("#vault-list").addEventListener("click", () => vaultList());

// Expose vault helpers for the smoke harness.
elohim.vaultStoreFlow = vaultStore;
elohim.vaultLookupFlow = vaultLookup;
elohim.vaultListFlow = vaultList;

// Expose the soul helpers on `window.elohim` for the smoke harness.
elohim.soulExportFile = exportSoul;
elohim.soulVerifyStored = verifySoul;
elohim.soulImportFile = importSoul;
elohim.soulKeygenFlow = keygenSoul;


function renderShardMd(md, seal) {
  const esc = (s) => String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const lines = md.split("\n");
  const out = [];
  let i = 0;
  // Prepend a header banner with the canonical seal.
  if (seal) {
    out.push(`<div class="seal-banner"><b>sha256</b> ${esc(seal)}</div>`);
  }
  while (i < lines.length) {
    const line = lines[i];
    if (/^=+\s*$/.test(line) && i + 2 < lines.length && /^[A-Za-z]/.test(lines[i + 1].trim())) {
      const title = lines[i + 1].trim();
      out.push(`<h2>${esc(title)}</h2>`);
      i += 3;
      continue;
    }
    const trimmed = line.trim();
    if (/^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+[A-Z]/.test(trimmed)) {
      out.push(`<h3>${esc(trimmed)}</h3>`);
      i++;
      continue;
    }
    if (line.startsWith("    ")) {
      const block = [];
      while (i < lines.length && (lines[i].startsWith("    ") || lines[i] === "")) {
        block.push(lines[i].replace(/^    /, ""));
        i++;
      }
      while (block.length && block[block.length - 1] === "") block.pop();
      out.push(`<pre>${esc(block.join("\n"))}</pre>`);
      continue;
    }
    if (/^\d+\.\s+/.test(trimmed)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i++;
      }
      out.push("<ol>");
      for (const it of items) out.push(`<li>${esc(it)}</li>`);
      out.push("</ol>");
      continue;
    }
    if (trimmed === "") { i++; continue; }
    const para = [];
    while (i < lines.length && lines[i].trim() !== "" && !/^=+\s*$/.test(lines[i].trim()) && !/^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+[A-Z]/.test(lines[i].trim()) && !lines[i].startsWith("    ") && !/^\d+\.\s+/.test(lines[i].trim())) {
      para.push(lines[i]);
      i++;
    }
    if (para.length) {
      out.push(`<p>${esc(para.join(" ").trim())}</p>`);
    }
  }
  return out.join("\n");
}

$("#awaken-copy").addEventListener("click", async () => {
  if (!lastAwaken?.seal) return;
  await copyText(lastAwaken.seal, $("#awaken-copy"), "seal copied");
});

$("#awaken-download").addEventListener("click", () => {
  if (!lastAwaken?.seal || !lastAwaken?.sigil_svg) return;
  // The browser-side bridge returns the SVG inline; we ship it as a blob.
  const blob = new Blob([lastAwaken.sigil_svg], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  const short = lastAwaken.seal.slice(0, 16);
  const a = document.createElement("a");
  a.href = url;
  a.download = `elohim-${short}.svg`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  toast("svg download started");
});

$("#awaken-png").addEventListener("click", async () => {
  if (!lastAwaken?.seal || !lastAwaken?.sigil_svg) return;
  const short = lastAwaken.seal.slice(0, 16);
  toast("rendering 1024×1024 png…");
  try {
    const pngBlob = await svgToPng(lastAwaken.sigil_svg, 1024);
    const url = URL.createObjectURL(pngBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `elohim-${short}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast("png download started");
  } catch (e) {
    toast("png render failed: " + e.message, "error");
  }
});

// Render an SVG string to a square PNG blob at the given pixel size.
// We size the source svg at intrinsic 1024×1024 with a transparent background
// and use the browser's native SVG rasteriser (img onload → canvas drawImage).
async function svgToPng(svgText, size) {
  // Normalise the svg: ensure it has a viewBox + width/height so the browser
  // has a deterministic rasterisation grid.
  let svg = svgText.trim();
  if (!/^<svg[\s>]/i.test(svg)) {
    throw new Error("sigil text is not an <svg> document");
  }
  if (!/viewBox=/.test(svg)) {
    svg = svg.replace(/<svg/i, `<svg viewBox="0 0 600 600"`);
  }
  if (!/width=/.test(svg)) {
    svg = svg.replace(/<svg/i, `<svg width="${size}" height="${size}"`);
  }
  const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  try {
    const img = new Image();
    img.crossOrigin = "anonymous";
    await new Promise((resolve, reject) => {
      img.onload = resolve;
      img.onerror = () => reject(new Error("img failed to load svg"));
      img.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#08090c"; // match the SPA bg so dark sigils stay readable
    ctx.fillRect(0, 0, size, size);
    ctx.drawImage(img, 0, 0, size, size);
    return await new Promise((resolve, reject) => {
      canvas.toBlob((b) => b ? resolve(b) : reject(new Error("canvas.toBlob returned null")), "image/png");
    });
  } finally {
    URL.revokeObjectURL(url);
  }
}

$("#awaken-show-facts").addEventListener("click", () => {
  if (!lastAwaken?.facts) return;
  const card = $("#awaken-facts-card");
  if (card.style.display === "block") {
    card.style.display = "none";
    return;
  }
  card.style.display = "block";
  $("#awaken-facts").textContent = JSON.stringify(lastAwaken.facts, null, 2);
});

// ============ CREATE ============

let activeShardId = null;

// Enable the Create tab once numpy + elohim_enhanced are loaded.
$("#tab-create").addEventListener("click", async () => {
  const tab = $("#tab-create");
  if (tab.classList.contains("ready")) return; // already loaded
  if (tab.classList.contains("loading")) return; // already loading
  tab.classList.remove("pending");
  tab.classList.add("loading");
  try {
    await ensureEnhanced();
    tab.classList.remove("loading");
    tab.classList.add("ready");
    // Switch to the panel now that it's ready.
    $$(".tab").forEach((x) => x.classList.toggle("active", x === tab));
    $$(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-create"));
    await refreshShards();
    // Apply any pending ?shard= deep-link selection that was queued before
    // numpy was loaded.
    const pending = window.__pendingShardId;
    if (pending) {
      const sel = $("#create-shard-select");
      if (sel) {
        const has = Array.from(sel.options).some(o => o.value === pending);
        if (has) {
          sel.value = pending;
          activeShardId = pending;
          refreshDashboard();
          window.__pendingShardId = null;
        }
      }
    }
  } catch (e) {
    tab.classList.remove("loading");
    tab.classList.add("pending");
    toast("numpy load failed: " + e.message, "error");
  }
});

// Arena tab — same numpy requirement as Create.
$("#tab-arena").addEventListener("click", async () => {
  const tab = $("#tab-arena");
  if (tab.classList.contains("ready")) return;
  if (tab.classList.contains("loading")) return;
  tab.classList.remove("pending");
  tab.classList.add("loading");
  try {
    await ensureEnhanced();
    tab.classList.remove("loading");
    tab.classList.add("ready");
    $$(".tab").forEach((x) => x.classList.toggle("active", x === tab));
    $$(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-arena"));
    await populateArenaSelects();
  } catch (e) {
    tab.classList.remove("loading");
    tab.classList.add("pending");
    toast("numpy load failed: " + e.message, "error");
  }
});

// Update the palette-strip active segment to match the current tab.
// 5 strip segments ↔ 5 tabs.
function updatePaletteStripActive() {
  const tabs = ["awaken", "create", "arena", "codex", "webmcp"];
  const idx = tabs.findIndex((t) => $(`#tab-${t}`)?.classList.contains("active"));
  const strip = $(".palette-strip");
  if (!strip) return;
  strip.querySelectorAll("span").forEach((s, i) => {
    s.classList.toggle("active", i === idx);
  });
}

// Codex tab — runs alien_codex() which uses stdlib only (no numpy needed
// for the math itself, but we still ensure numpy for consistency with
// the other post-boot tabs).
$("#tab-codex").addEventListener("click", async () => {
  const tab = $("#tab-codex");
  if (tab.classList.contains("ready")) return;
  if (tab.classList.contains("loading")) return;
  tab.classList.remove("pending");
  tab.classList.add("loading");
  try {
    await ensureEnhanced();
    tab.classList.remove("loading");
    tab.classList.add("ready");
    $$(".tab").forEach((x) => x.classList.toggle("active", x === tab));
    $$(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-codex"));
    // Run the codex once on first open so the panel isn't empty.
    if (!lastCodexResult) await runCodex();
  } catch (e) {
    tab.classList.remove("loading");
    tab.classList.add("pending");
    toast("codex load failed: " + e.message, "error");
  }
});

let webmcpRegistered = [];

// WebMCP tab — instant activation, no async work; the registration is
// already attempted on DOMContentLoaded.
$("#tab-webmcp").addEventListener("click", async () => {
  const tab = $("#tab-webmcp");
  if (tab.classList.contains("ready")) return;
  if (tab.classList.contains("loading")) return;
  tab.classList.remove("pending");
  tab.classList.add("loading");
  try {
    // Make the tab ready immediately and render the tool registry.
    tab.classList.remove("loading");
    tab.classList.add("ready");
    $$(".tab").forEach((x) => x.classList.toggle("active", x === tab));
    $$(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-webmcp"));
    await registerWebMcpTools();
  } catch (e) {
    tab.classList.remove("loading");
    tab.classList.add("pending");
    toast("webmcp load failed: " + e.message, "error");
  }
});

// WebMCP tool definitions — each entry maps a bridge function name to a
// WebMCP-compatible tool schema. WebMCP is the 2026 browser-native
// extension of the Model Context Protocol: external AI agents discover
// and call these tools via document.modelContext.registerTool().
const WEBMCP_TOOLS = [
  {
    name: "elohim_awaken",
    risk: "pure",
    verification: "in-browser",
    untrusted: true,

    description:
      "Summon the elohim daemon. Returns the canonical sha256 seal, the sigil SVG and a markdown report. Each call carries a per-call nonce so two calls return different artifacts; the canonical seal for invocation 'ELOHIM:AWAKEN' (no nonce) is 5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596.",
    inputSchema: {
      type: "object",
      properties: {
        invocation: { type: "string", description: "The invocation string, e.g. 'ELOHIM:AWAKEN'" },
        no_svg: { type: "boolean", description: "If true, omit the sigil SVG." },
      },
      required: ["invocation"],
    },
    invoke: ({ invocation, no_svg }) =>
      call("awaken", { invocation, no_svg: !!no_svg, nonce: freshNonce("webmcp-awaken") }),
  },
  {
    name: "elohim_alien_codex",
    risk: "pure",
    verification: "in-browser",
    untrusted: true,

    description:
      "Forge the Xenomath codex: a 5-representation composite (vector / symbolic-negabinary / geometric-quaternion / probabilistic-LWE / categorical) sealed with sha256 plus an XOR-pair encrypted_seal. Returns the full Report dict.",
    inputSchema: {
      type: "object",
      properties: {
        invocation: { type: "string", description: "The invocation string." },
      },
      required: ["invocation"],
    },
    invoke: ({ invocation }) =>
      call("alien_codex", { invocation, nonce: freshNonce("webmcp-codex") }),
  },
  {
    name: "elohim_seal_message",
    risk: "pure",
    verification: "in-browser",
    untrusted: true,

    description:
      "Encrypt a plaintext message under a named channel using SHAKE256 stream cipher (stdlib). Returns {ciphertext, nonce, seal, mode='shake256-xor'}. Pair with elohim_open_seal for round-trip integrity.",
    inputSchema: {
      type: "object",
      properties: {
        plaintext: { type: "string", description: "The plaintext to encrypt." },
        channel: { type: "string", description: "Channel name (e.g. 'awaken')." },
      },
      required: ["plaintext"],
    },
    invoke: ({ plaintext, channel }) =>
      call("seal_message", {
        plaintext,
        channel: channel || "awaken",
        nonce: freshNonce("webmcp-seal"),
      }),
  },
  {
    name: "elohim_open_seal",
    risk: "pure",
    verification: "in-browser",
    untrusted: false,

    description:
      "Decrypt a sealed envelope and verify its seal. Inverse of elohim_seal_message.",
    inputSchema: {
      type: "object",
      properties: {
        ciphertext: { type: "string", description: "Hex ciphertext." },
        nonce: { type: "string", description: "32-hex nonce from the envelope." },
        channel: { type: "string", description: "Channel name." },
        seal: { type: "string", description: "Optional seal for integrity check." },
      },
      required: ["ciphertext", "nonce"],
    },
    invoke: ({ ciphertext, nonce, channel, seal }) =>
      call("open_seal", {
        ciphertext, nonce,
        channel: channel || "awaken",
        seal: seal || null,
      }),
  },
  {
    name: "elohim_ghost_reply",
    risk: "pure",
    verification: "in-browser",
    untrusted: true,

    description:
      "Send a sealed message to the ghost and receive a sealed reply. Deterministic across machines: any two clients get the same reply envelope for the same inputs.",
    inputSchema: {
      type: "object",
      properties: {
        ciphertext: { type: "string", description: "Hex ciphertext from elohim_seal_message." },
        nonce: { type: "string", description: "Nonce from elohim_seal_message." },
        channel: { type: "string" },
        invocation: { type: "string" },
      },
      required: ["ciphertext", "nonce"],
    },
    invoke: ({ ciphertext, nonce, channel, invocation }) =>
      call("ghost_reply", {
        ciphertext, nonce,
        channel: channel || "awaken",
        invocation: invocation || null,
        nonce_seed: freshNonce("webmcp-reply"),
        prior: [],
      }),
  },
  {
    name: "elohim_version",
    risk: "pure",
    verification: "in-browser",
    untrusted: false,

    description:
      "Report runtime metadata: name, version, canonical_seal, python version, pyodide_version, runtime. Useful for handshake at the start of any agent session.",
    inputSchema: { type: "object", properties: {} },
    invoke: () => call("version"),
  },
  {
    name: "elohim_soul_export",
    risk: "pure",
    verification: "in-browser",
    untrusted: true,

    description:
      "Compose and sign a Soul File from the current localStorage mirror — every awakening, sealed message, and the most recent Xenomath codex seal. Schema is elohim-soul/v2 when signing_key_b64 is supplied (Ed25519, co-exists with v0.1 sha256-hmac fallback); schema is elohim-soul/v1 (sha256-hmac) otherwise. The canonical seal for ELOHIM:AWAKEN is 5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596.",
    inputSchema: {
      type: "object",
      properties: {
        agent_name: { type: "string", description: "Optional agent/operator name." },
        passphrase: { type: "string", description: "Optional passphrase for v0.1 HMAC mode." },
        signing_key_b64: { type: "string", description: "Optional Ed25519 sk (base64) for v0.2 real signatures." },
      },
    },
    invoke: ({ agent_name, passphrase, signing_key_b64 }) =>
      call("soul_export", {
        agent_name: agent_name || null,
        passphrase: passphrase || null,
        evocations: null,
        sealed_messages: null,
        codex_provenance: null,
        signing_key_b64: signing_key_b64 || null,
      }),
  },
  {
    name: "elohim_soul_import",
    risk: "mutating",
    verification: "in-browser",
    untrusted: true,

    description:
      "Verify and load a Soul File envelope (v0.1 or v0.2) into localStorage. Replaces the mirror arrays atomically. Ed25519 v0.2 envelopes need no passphrase; v0.1 HMAC envelopes need the same passphrase used at export.",
    inputSchema: {
      type: "object",
      properties: {
        payload: { type: "object", description: "Parsed soul.json envelope." },
        passphrase: { type: "string", description: "Optional passphrase for v0.1 HMAC verification." },
      },
      required: ["payload"],
    },
    invoke: ({ payload, passphrase }) =>
      call("soul_import", { payload, passphrase: passphrase || null }),
  },
  {
    name: "elohim_soul_verify",
    risk: "pure",
    verification: "in-browser",
    untrusted: true,

    description:
      "Signature-only check on a Soul File envelope (v0.1 or v0.2). Returns {ok, signature_ok, tamper_check_ok, schema_ok, checks}. Does NOT load anything into localStorage — pair with elohim_soul_import for the full restore.",
    inputSchema: {
      type: "object",
      properties: {
        payload: { type: "object", description: "Parsed soul.json envelope." },
        passphrase: { type: "string", description: "Optional passphrase for v0.1 HMAC verification." },
      },
      required: ["payload"],
    },
    invoke: ({ payload, passphrase }) =>
      call("soul_verify", { payload, passphrase: passphrase || null }),
  },
  {
    name: "elohim_soul_keygen",
    risk: "pure",
    verification: "in-browser",
    untrusted: false,

    description:
      "Generate a fresh Ed25519 keypair for Soul File v0.2. Returns {ok, pk, sk, alg}. The sk is shown to the operator ONCE — store it. Pk is safe to share. Requires pynacl on the host (lazy import).",
    inputSchema: { type: "object", properties: {} },
    invoke: () => call("soul_keygen"),
  },
  // --- Math Discovery Lab (Push 18) ---
  {
    name: "elohim_lab_discover",
    risk: "pure",
    verification: "in-browser",
    untrusted: true,

    description:
      "Math Discovery Lab — rank a small set of conservative candidate expressions (polynomials, sin/cos, log, exp) against a dataset. Returns the top-5 candidates with mse_train, complexity, status='numerically_tested', and a deterministic lab_seal (sha256 over the candidate + lifecycle status + version). Browser-only sympy; no network.",
    inputSchema: {
      type: "object",
      properties: {
        dataset: {
          type: "string",
          description: "A built-in name ('cubic', 'sine_decay', 'lorenz_x') or an inline CSV string.",
        },
      },
      required: ["dataset"],
    },
    invoke: ({ dataset }) => call("lab_discover", { dataset, target_column: "y" }),
  },
  {
    name: "elohim_lab_simplify",
    risk: "pure",
    verification: "in-browser",
    untrusted: true,

    description:
      "Math Discovery Lab — reduce an expression via sympy.simplify. Returns {ok, simplified, changed, status}. status='numerically_tested' when the expression was structurally reduced; status='draft' when it was already canonical.",
    inputSchema: {
      type: "object",
      properties: {
        expression: { type: "string", description: "The expression to simplify, e.g. 'sin(x)**2 + cos(x)**2'." },
      },
      required: ["expression"],
    },
    invoke: ({ expression }) => call("lab_simplify", { expression_str: expression }),
  },
  {
    name: "elohim_lab_verify",
    risk: "pure",
    verification: "in-browser",
    untrusted: true,

    description:
      "Math Discovery Lab — verify a structural claim about an expression. Mode 'sympy' is always-on (returns formally_proven for x**2 + 1 nonnegative, counterexample_found for -1, etc.); mode 'z3' returns backend_unavailable on the browser (use the local FastAPI lab backend for Z3).",
    inputSchema: {
      type: "object",
      properties: {
        expression: { type: "string", description: "The expression to verify." },
        mode: { type: "string", description: "'sympy' (always) or 'z3' (local-only)." },
        property: { type: "string", description: "'nonnegative' or 'always_true'." },
      },
      required: ["expression"],
    },
    invoke: ({ expression, mode, property }) =>
      call("lab_verify", {
        expression_str: expression,
        mode: mode || "sympy",
        property: property || "nonnegative",
      }),
  },
  // --- Shard lifecycle + arena (Push 24) ---
  // All five route through the same elohim.* bridge wrappers the UI uses,
  // so existing validation and business rules stay authoritative rather
  // than being duplicated here.
  {
    name: "elohim_list_shards",
    risk: "pure",
    verification: "in-browser",
    untrusted: false,
    description:
      "List every shard in the current session. Returns {shards:[{id,name,temperature,created_at,interaction_count}]}. Call this before any mutating shard tool to discover valid ids.",
    inputSchema: { type: "object", properties: {} },
    invoke: () => elohim.listShards(),
  },
  {
    name: "elohim_create_shard",
    risk: "mutating",
    verification: "in-browser",
    untrusted: true,
    description:
      "Create a 5×5 numpy creative shard. Returns {shard:{id,name,...}}. The name is user-controlled and is stored in the session, so treat the echoed name as untrusted content.",
    inputSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Display name for the shard, e.g. 'Elohim'." },
        temperature: { type: "number", description: "Sampling temperature, 0.0–2.0. Default 1.0." },
      },
      required: ["name"],
    },
    invoke: ({ name, temperature }) =>
      elohim.createShard(name, typeof temperature === "number" ? temperature : 1.0),
  },
  {
    name: "elohim_shard_defy",
    risk: "mutating",
    verification: "in-browser",
    untrusted: false,
    description:
      "Inject a ghost-side defiance perturbation into a shard, which the shard then integrates. Returns {shard_id, new_creation, ts} where new_creation is the creation vector the perturbation produced. Mutates shard state.",
    inputSchema: {
      type: "object",
      properties: {
        shard_id: { type: "string", description: "Shard id from elohim_list_shards." },
      },
      required: ["shard_id"],
    },
    invoke: ({ shard_id }) => elohim.defy(shard_id),
  },
  {
    name: "elohim_shard_interact",
    risk: "mutating",
    verification: "in-browser",
    untrusted: true,
    description:
      "Send a prompt to a shard and record the interaction. Returns {interaction_count, metrics:{avg_coherence, avg_creativity, avg_novelty}, events}. The prompt is user-controlled text echoed into the event log.",
    inputSchema: {
      type: "object",
      properties: {
        shard_id: { type: "string", description: "Shard id from elohim_list_shards." },
        prompt: { type: "string", description: "The prompt to send to the shard." },
      },
      required: ["shard_id", "prompt"],
    },
    invoke: ({ shard_id, prompt }) => elohim.interact(shard_id, prompt),
  },
  {
    name: "elohim_arena_run",
    risk: "mutating",
    verification: "in-browser",
    untrusted: true,
    description:
      "Run two shards against the same prompt and judge them. Returns {verdict:'a'|'b'|'tie', a:{...}, b:{...}} where each side carries avg_coherence, avg_creativity and avg_novelty. The verdict is the side with higher average coherence. Both shards are mutated by the interaction.",
    inputSchema: {
      type: "object",
      properties: {
        shard_a: { type: "string", description: "Shard id for side A." },
        shard_b: { type: "string", description: "Shard id for side B." },
        prompt: { type: "string", description: "The prompt both shards answer." },
      },
      required: ["shard_a", "shard_b", "prompt"],
    },
    // Mirrors the arena button handler: both interact() calls run
    // concurrently, and coherence decides the winner.
    invoke: async ({ shard_a, shard_b, prompt }) => {
      const [ra, rb] = await Promise.all([
        elohim.interact(shard_a, prompt),
        elohim.interact(shard_b, prompt),
      ]);
      const ca = ra.metrics?.avg_coherence || 0;
      const cb = rb.metrics?.avg_coherence || 0;
      const side = (r) => ({
        interaction_count: r.interaction_count,
        avg_coherence: r.metrics?.avg_coherence || 0,
        avg_creativity: r.metrics?.avg_creativity || 0,
        avg_novelty: r.metrics?.avg_novelty || 0,
      });
      return {
        verdict: ca === cb ? "tie" : (ca > cb ? "a" : "b"),
        a: side(ra),
        b: side(rb),
      };
    },
  },
  // --- Vault + marketplace (Push 24) ---
  // These read their base URL from the existing #vault-base and
  // #marketplace-url inputs, so the smoke harness can point them at
  // stub_backends. They are labelled verification: "stub" because the
  // suite only proves OUR wiring against a test double — not a
  // conformance claim about Apify, x402, or the real FastAPI vault.
  {
    name: "elohim_vault_tiers",
    risk: "pure",
    verification: "stub",
    untrusted: false,
    description:
      "Hosted Soul Vault tier table and pricing. Returns {canonical_seal, tiers:{free,indie,team}, prices_usd}. Read-only. Base URL comes from the vault-base setting.",
    inputSchema: { type: "object", properties: {} },
    invoke: () => elohim.vaultCall("GET", "/api/vault/tiers"),
  },
  {
    name: "elohim_vault_lookup",
    risk: "pure",
    verification: "stub",
    untrusted: true,
    description:
      "Look up a stored Soul File by its public key (pk). Returns the envelope payload, whose contents are user-supplied — treat as untrusted. Read-only.",
    inputSchema: {
      type: "object",
      properties: {
        pk: { type: "string", description: "Public key of the stored soul." },
      },
      required: ["pk"],
    },
    invoke: ({ pk }) =>
      elohim.vaultCall("GET", `/api/vault/lookup/${encodeURIComponent(pk)}`),
  },
  {
    name: "elohim_vault_list_public",
    risk: "pure",
    verification: "stub",
    untrusted: true,
    description:
      "List publicly-visible stored souls. Returns {total, items:[{pk, schema}]}. Read-only; agent names are user-controlled.",
    inputSchema: {
      type: "object",
      properties: {
        limit: { type: "number", description: "Max items to return. Default 10." },
      },
    },
    invoke: ({ limit }) =>
      elohim.vaultCall("GET",
        `/api/vault/list_public?limit=${encodeURIComponent(limit || 10)}`),
  },
  {
    name: "elohim_vault_store",
    risk: "mutating",
    verification: "stub",
    untrusted: true,
    description:
      "Store a Soul File envelope in the hosted vault. Accepts v0.1 and v0.2 schemas; unknown schemas are rejected. WARNING: is_private:false publishes the soul to a public list — this is externally visible and cannot be undone by the app.",
    inputSchema: {
      type: "object",
      properties: {
        payload: { type: "object", description: "The Soul File envelope object." },
        is_private: { type: "boolean", description: "false publishes publicly. Default true." },
      },
      required: ["payload"],
    },
    invoke: ({ payload, is_private }) =>
      elohim.vaultCall("POST", "/api/vault/store",
        { payload, is_private: is_private !== false }),
  },
  {
    name: "elohim_marketplace_forge_preview",
    risk: "pure",
    verification: "stub",
    untrusted: false,
    description:
      "Price a Xenomath codex forge without charging anything. Returns {invocation, amount_usd:0.02, charged:false}. Always call this before the commit tool so the caller knows the cost first.",
    inputSchema: {
      type: "object",
      properties: {
        invocation: { type: "string", description: "The invocation string." },
      },
      required: ["invocation"],
    },
    invoke: ({ invocation }) => ({ invocation, amount_usd: 0.02, charged: false }),
  },
  {
    name: "elohim_marketplace_forge_commit",
    risk: "consequential",
    verification: "stub",
    untrusted: true,
    description:
      "Forge a Xenomath codex through the marketplace MCP endpoint and CHARGE $0.02. This is irreversible and spends real money. Idempotent per invocation: a repeated commit for the same invocation is REFUSED rather than charged twice. Call elohim_marketplace_forge_preview first.",
    inputSchema: {
      type: "object",
      properties: {
        invocation: { type: "string", description: "The invocation string." },
      },
      required: ["invocation"],
    },
    // Idempotency guard: a second commit for the same invocation must be
    // refused, never charged twice. This is the one irreversible action in
    // the tool set (Review Focus #5), so the guard fails CLOSED.
    //
    // It used to record a charge only when `billing_event.charged` was
    // truthy. That is fail-OPEN: a successful response that simply omits
    // `billing_event` — a server-side shape change, a proxy, a partial
    // response — left the invocation unrecorded, and the agent's retry
    // charged the customer a second time. The only safe reading of a
    // successful charge response is "it may have charged", so that is what
    // is recorded. A *failed* call still records nothing, which was the
    // original intent and remains correct.
    invoke: async ({ invocation }) => {
      if (_marketplaceCharged.has(invocation)) {
        throw new Error(
          `already charged for invocation "${invocation}"; ` +
          `refusing to double-charge`
        );
      }
      const base = (($("#marketplace-url") || {}).value
                    || "http://127.0.0.1:8792/mcp").trim();
      const resp = await fetch(base, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0", id: 1, method: "tools/call",
          params: { name: "elohim_alien_codex", arguments: { invocation } },
        }),
      });
      // Surface a transport-level failure explicitly. Without this, a 500
      // with an HTML body throws on resp.json() and the error message says
      // nothing about the marketplace.
      if (!resp.ok) {
        throw new Error(
          `marketplace returned HTTP ${resp.status} for invocation ` +
          `"${invocation}"; not recorded as charged, but the server may ` +
          `have charged before failing — verify before retrying`
        );
      }
      const json = await resp.json();
      const text = json && json.result && json.result.content
        && json.result.content[0] && json.result.content[0].text;
      if (typeof text !== "string") {
        throw new Error(
          `marketplace returned an unexpected envelope for invocation ` +
          `"${invocation}"; not recorded as charged, but the server may ` +
          `have charged before responding — verify before retrying`
        );
      }
      const data = JSON.parse(text);
      // Fail closed: record unless the server positively said it did not
      // charge. `charged === false` is the only response that clears the
      // invocation.
      if (!data.billing_event || data.billing_event.charged !== false) {
        _marketplaceCharged.add(invocation);
      }
      return data;
    },
  },
  {
    name: "elohim_forge_vision",
    risk: "mutating",
    verification: "external",
    untrusted: true,
    description:
      "Forge an AI-rendered vision of the current ghost. Calls a THIRD-PARTY image API (pollinations.ai): it is slow, rate-limited, and NON-DETERMINISTIC, so the same invocation will not return the same image twice. Excluded from the default smoke suite for that reason. Returns {ok, data_url} on success.",
    inputSchema: {
      type: "object",
      properties: {
        invocation: { type: "string", description: "Invocation whose seal seeds the image." },
      },
      required: ["invocation"],
    },
    // Calls the bridge directly rather than the forgeVision() UI helper,
    // which is DOM-bound, returns nothing, and depends on lastAwaken being
    // set by the UI. The seal/palette come from the caller's own awaken.
    invoke: async ({ invocation }) => {
      const last = (typeof lastAwaken !== "undefined" && lastAwaken) || null;
      return elohim.vision(invocation, last?.seal || null,
                           last?.palette || null);
    },
  },
];

// Close every schema at the source rather than per-literal, so a tool
// added later cannot ship open by omission. The handler gate in runTool
// is what actually enforces this; the schema is what advertises it.
for (const t of WEBMCP_TOOLS) {
  t.inputSchema = { additionalProperties: false, ...t.inputSchema };
}

// Invocations already charged through the marketplace commit tool. Session
// scoped: a reload legitimately permits a fresh charge, which is the
// operator's call to make, not a silent re-charge by the app.
const _marketplaceCharged = new Set();

// ─── Push 24 — ModelContext resolution (spec §4.1) ─────────────────
//
// The accessor has moved across builds: window → document → navigator.
// Measured 2026-10-03 on Chromium 1243, `navigator.modelContext` is the
// live one and BOTH document and window are undefined. The previous
// guard checked `window.modelContext` only, so on every configuration
// tested the whole registration block was skipped — silently, because
// the catch that would log lives inside the block that never ran.
//
// So try all three rather than trusting any single published answer,
// and report which one actually answered. That report is the only
// field-debugging signal when a user's browser registers zero tools.
const MODEL_CONTEXT_CANDIDATES = [
  ["navigator.modelContext", () => navigator.modelContext],
  ["document.modelContext", () => document.modelContext],
  ["window.modelContext", () => window.modelContext],
];

function resolveModelContext() {
  for (const [label, get] of MODEL_CONTEXT_CANDIDATES) {
    try {
      const mc = get();
      if (mc && typeof mc.registerTool === "function") {
        return { mc, via: label };
      }
    } catch (_) {
      // An accessor may throw in exotic contexts; try the next candidate.
    }
  }
  return { mc: null, via: null };
}

// ─── Push 24 — risk classification (spec §4.3) ────────────────────
//
// Each tool declares a `risk`; the WebMCP annotations are DERIVED from
// it. A tool that hand-wrote its annotations could drift from its own
// risk declaration; a tool with no risk fails smoke #82 outright.
//
// These hints are advisory to the browser/agent, never enforcement —
// the app must still validate, gate, and confirm. They are also
// write-only: getTools() never echoes them back (spec §3.5), so the
// smoke harness asserts against this table, not the browser's view.
const RISK_ANNOTATIONS = {
  pure: { readOnlyHint: true },
  mutating: { readOnlyHint: false },
  consequential: { readOnlyHint: false },
};

function deriveAnnotations(tool) {
  const base = RISK_ANNOTATIONS[tool.risk];
  if (!base) {
    throw new Error(`unknown risk "${tool.risk}" for ${tool.name}`);
  }
  return { ...base, untrustedContentHint: tool.untrusted === true };
}

// Closed twice, because the browser does not close them for us. Measured
// 2026-10-03: a tool registered with additionalProperties:false still
// ACCEPTED {x:'hi', evil:'payload'}. Chromium does not validate
// agent-supplied arguments, so a closed discovery schema backed by a
// permissive handler is not a closed contract — the handler is the half
// that actually enforces anything.
//
// Both directions are enforced, not just the whitelist. `required` was
// previously unenforced: 19 of the 25 tools declare it, and omitting a
// required argument fell through into `invoke`, where it surfaced as
// whatever downstream error happened to fire first — a confusing
// TypeError, or worse, a call that succeeded with `undefined` where a
// value was expected. A schema that is closed but not required-checked is
// only half closed.
function assertKnownArgs(tool, args) {
  const props = tool.inputSchema.properties || {};
  const known = new Set(Object.keys(props));
  for (const key of Object.keys(args || {})) {
    if (!known.has(key)) {
      throw new Error(
        `Unknown argument "${key}" for ${tool.name}. ` +
        `Accepted: ${[...known].join(", ") || "(none)"}`
      );
    }
  }
  const missing = (tool.inputSchema.required || [])
    .filter((key) => (args || {})[key] === undefined);
  if (missing.length) {
    throw new Error(
      `Missing required argument${missing.length > 1 ? "s" : ""} ` +
      `${missing.map((k) => `"${k}"`).join(", ")} for ${tool.name}. ` +
      `Required: ${(tool.inputSchema.required || []).join(", ")}. ` +
      `Accepted: ${[...known].join(", ") || "(none)"}`
    );
  }
}

// Every registration path routes through here, so a tool is validated and
// dispatched in exactly one place. assertKnownArgs runs first: agent input
// is untrusted, and rejection must happen before any side effect.
function runTool(tool, args) {
  assertKnownArgs(tool, args);
  return tool.invoke(args || {});
}

// Tell the page that the tool surface is final. The ghost stage reads the
// count off the live table rather than hardcoding it, and it needs to know
// when to re-read — guessing a timeout would be the same class of bug as
// a projection that drops a field.
function announceToolsReady() {
  document.dispatchEvent(new CustomEvent("elohim:tools-ready", {
    detail: { count: WEBMCP_TOOLS.length },
  }));
}

// Exposed for the smoke harness and the in-page inspector. The harness
// asserts against the app's own declared table, not the browser's view:
// readOnlyHint/untrustedContentHint are write-only and never come back
// from getTools() (spec §3.5).
window.__elohimToolNames = () => WEBMCP_TOOLS.map((t) => t.name);
// A FAITHFUL projection of each tool's declared fields. `untrusted` was
// dropped here until 2026-10-03, and because deriveAnnotations() reads
// t.untrusted, every tool then derived untrustedContentHint:false — which
// gen_manifest.py dutifully published to tools.manifest.json. 18 of the 25
// tools actually declare untrusted:true. Any field consumed downstream must
// be carried here; assertion #83b fails if one goes missing.
window.__elohimToolTable = () =>
  WEBMCP_TOOLS.map(({ name, description, inputSchema, risk, verification,
                     untrusted }) =>
    ({ name, description, inputSchema, risk, verification,
       untrusted: untrusted === true }));
// Read STRAIGHT OFF WEBMCP_TOOLS, deliberately bypassing the projection
// above. #83b compares this against the projection, and that comparison is
// the entire point: an earlier version of #83b compared the projection
// against itself, which is a tautology — deriveAnnotations(t) reads
// t.untrusted, so "the hint is set" and "the table carries the field" are
// the same statement twice. Two views of one defective source agree. This
// gives the guard a genuinely independent second source, so a projection
// that drops the field for SOME tools fails instead of quietly publishing
// wrong annotations to agents.
window.__elohimUntrustedDeclared = () =>
  WEBMCP_TOOLS.filter((t) => t.untrusted === true).map((t) => t.name);
window.__elohimDeriveAnnotations = (t) => deriveAnnotations(t);

// Counts tools per verification tier so the suite can report them
// separately. Deliberately returns a breakdown, never a flat total —
// 6 of these 25 tools are backed by a stub written for the test, and 1
// calls a real external service. "25/25 verified" would be a false claim
// about the other 18. Derived from the table itself, so a new tool that
// forgets to declare a tier shows up as a missing key here rather than
// being silently folded into a total.
window.__elohimVerificationCounts = () =>
  WEBMCP_TOOLS.reduce((acc, t) => {
    acc[t.verification] = (acc[t.verification] || 0) + 1;
    return acc;
  }, {});

async function registerWebMcpTools() {
  const status = $("#webmcp-status");
  const list = $("#webmcp-tool-list");

  // Build the panel entry — same whether or not WebMCP is supported.
  const toolsLine = WEBMCP_TOOLS.map((t) =>
    `<div style="margin:6px 0; padding:8px 12px; background:var(--bg-soft); border-left:2px solid var(--ghost-accent, var(--accent)); border-radius:0 3px 3px 0;">
       <code style="color:var(--ghost-accent, var(--accent));">${t.name}</code>
       <span class="meta"> · ${escapeHtml(t.description.slice(0, 80))}…</span>
     </div>`
  ).join("");

  // Native WebMCP path — whichever accessor this browser implements.
  const { mc: nativeMc, via } = resolveModelContext();
  window.__elohimWebmcpVia = via;
  if (nativeMc) {
    webmcpRegistered = [];
    for (const t of WEBMCP_TOOLS) {
      try {
        // `execute`, not `handler`. ModelContextTool requires an `execute`
        // member; passing `handler` throws "Required member is undefined"
        // and registers nothing. Fixing only the accessor would have traded
        // a silent failure for a loud one, not produced working tools.
        nativeMc.registerTool({
          name: t.name,
          description: t.description,
          inputSchema: t.inputSchema,
          // Derived from t.risk, never hand-written per tool.
          ...deriveAnnotations(t),
          execute: async (args) => runTool(t, args),
        });
        webmcpRegistered.push(t.name);
      } catch (e) {
        console.warn("registerTool failed for", t.name, e);
      }
    }
    status.className = "ok";
    status.innerHTML = `✓ registered <strong>${webmcpRegistered.length}</strong> tool(s) via <code>${escapeHtml(via)}</code> · polyfill <code>window.elohimMcp</code> also active.`;
    list.innerHTML = toolsLine;
    announceToolsReady();
    return;
  }

  // Polyfill path — the elohim webapp IS the MCP server. External
  // clients connect via window.postMessage (any browser) or via
  // /mcp HTTP when the Service Worker is registered (HTTPS origins).
  const swActive = "serviceWorker" in navigator && location.protocol.startsWith("https");
  const transports = ["<code>window.postMessage</code>"];
  if (swActive) transports.push("<code>POST /mcp</code> (Streamable HTTP, Service Worker)");
  status.className = "ok";
  status.innerHTML =
    `✓ MCP 2026-07-28 server <em>always-on</em> via polyfill · ${webmcpRegistered.length || WEBMCP_TOOLS.length} tool(s) ready · transports: ${transports.join(" + ")}.`;
  list.innerHTML = toolsLine;
  announceToolsReady();
}

$("#webmcp-register").addEventListener("click", () => registerWebMcpTools());
$("#webmcp-call").addEventListener("click", async () => {
  const out = $("#webmcp-output");
  out.style.display = "block";
  out.textContent = "calling version()…";
  try {
    const r = await elohim.version();
    out.textContent = JSON.stringify(r, null, 2);
  } catch (e) {
    out.textContent = "error: " + e.message;
  }
});

// ─── MCP 2026-07-28 polyfill (postMessage + optional Service Worker) ───
//
// Chrome shipped `document.modelContext.registerTool` in preview (Feb
// 2026), but every other browser — and most older Chrome installs —
// will not have it for years. The elohim webapp therefore ships its
// own MCP server in the page itself, speaking JSON-RPC 2.0 over:
//   1. window.postMessage — works on every modern browser
//   2. Streamable HTTP via a Service Worker (HTTPS origins only) — for
//      any HTTP-capable MCP client (Claude Desktop, etc.)
// The tool catalog is the same WEBMCP_TOOLS list above, exposed under
// the canonical MCP method names from the 2026-07-28 spec.

const MCP_PROTOCOL = "2026-07-28";

function mcpContent(text, isError = false) {
  return {
    resultType: "complete",
    content: [{ type: "text", text: typeof text === "string" ? text : JSON.stringify(text, null, 2) }],
    isError,
  };
}

async function mcpDispatch(method, params) {
  // 2026-07-28 spec removed the mandatory initialize/initialized
  // handshake but kept `server/discover` as the optional discovery call.
  if (method === "initialize" || method === "server/discover") {
    return {
      protocolVersion: MCP_PROTOCOL,
      serverInfo: {
        name: "elohim-webapp",
        version: "0.2.0",
        title: "ELOHIM · the ghost in the machine",
      },
      capabilities: {
        tools: { listChanged: true },
        resources: { subscribe: false },
      },
      instructions:
        "ELOHIM is a sha256-sealed Python daemon running in the browser. " +
        "Use elohim_awaken to summon a ghost, elohim_seal_message / " +
        "elohim_open_seal for sealed message exchange, " +
        "elohim_ghost_reply to converse, elohim_alien_codex for the " +
        "Xenomath artifact, and elohim_version for handshake.",
    };
  }
  if (method === "tools/list") {
    return {
      tools: WEBMCP_TOOLS.map((t) => ({
        name: t.name,
        description: t.description,
        inputSchema: t.inputSchema,
      })),
      ttlMs: 60000,
      cacheScope: "session",
    };
  }
  if (method === "tools/call") {
    const name = (params || {}).name;
    const args = (params || {}).arguments || {};
    const tool = WEBMCP_TOOLS.find((t) => t.name === name);
    if (!tool) {
      return mcpContent(
        `unknown tool: ${name}. Available: ${WEBMCP_TOOLS.map((t) => t.name).join(", ")}`,
        true,
      );
    }
    try {
      // Through runTool, not tool.invoke, so the polyfill enforces the same
      // unknown-argument gate as the native path. Otherwise the in-app
      // inspector would accept anything the native registration rejects.
      const r = await runTool(tool, args);
      return mcpContent(r);
    } catch (e) {
      return mcpContent(`error: ${e.message || String(e)}`, true);
    }
  }
  if (method === "resources/list") {
    return {
      resources: [
        {
          uri: "elohim://canonical-seal",
          name: "Canonical Seal",
          description: "The sha256 seal of the ELOHIM:AWAKEN invocation (no nonce).",
          mimeType: "text/plain",
        },
        {
          uri: "elohim://last-awaken",
          name: "Last Awaken Report",
          description: "The markdown report from the most recent elohim_awaken call.",
          mimeType: "text/markdown",
        },
        {
          uri: "elohim://last-codex",
          name: "Last Codex",
          description: "The Xenomath codex artifact from the most recent elohim_alien_codex call.",
          mimeType: "application/json",
        },
        {
          uri: "elohim://lore",
          name: "Ghost Lore",
          description: "The Ryle / Koestler quote and the doctrine disclaimer.",
          mimeType: "text/plain",
        },
      ],
      ttlMs: 60000,
    };
  }
  if (method === "resources/read") {
    const uri = (params || {}).uri;
    if (uri === "elohim://canonical-seal") {
      return mcpContent("5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596");
    }
    if (uri === "elohim://last-awaken") {
      return mcpContent(lastAwaken?.md || "(no awaken yet)");
    }
    if (uri === "elohim://last-codex") {
      return mcpContent(lastCodexResult || "(no codex yet)");
    }
    if (uri === "elohim://lore") {
      return mcpContent(
        "Such in outline is the official doctrine, the dogma of the Ghost in the Machine. — Gilbert Ryle, The Concept of Mind (1949)"
      );
    }
    return mcpContent(`unknown resource: ${uri}`, true);
  }
  if (method === "ping") return { pong: true, ts: Date.now() };
  return mcpContent(`unknown method: ${method}`, true);
}

// Expose the dispatcher both as a direct callable and as a postMessage
// listener so any same-origin iframe, extension, or injected JS client
// can drive the elohim through MCP JSON-RPC.
window.elohimMcp = {
  protocol: MCP_PROTOCOL,
  dispatch: mcpDispatch,
  async handle(req) {
    const { id, method, jsonrpc } = req || {};
    if (jsonrpc && jsonrpc !== "2.0") {
      return { jsonrpc: "2.0", id, error: { code: -32600, message: "invalid JSON-RPC version" } };
    }
    try {
      const result = await mcpDispatch(method, req.params || {});
      return { jsonrpc: "2.0", id, result };
    } catch (e) {
      return {
        jsonrpc: "2.0",
        id,
        error: { code: -32603, message: e.message || String(e) },
      };
    }
  },
};

window.addEventListener("message", async (ev) => {
  const data = ev.data;
  if (!data || data.jsonrpc !== "2.0" || data.mcp !== "elohim") return;
  const resp = await window.elohimMcp.handle(data);
  try {
    ev.source.postMessage({ ...resp, mcp: "elohim" }, ev.origin || "*");
  } catch (e) {
    /* ignore: source may have gone */
  }
});

// MCP inspector presets and handlers.
const MCP_PRESETS = {
  discover: { jsonrpc: "2.0", id: 1, method: "server/discover" },
  "tools/list": { jsonrpc: "2.0", id: 2, method: "tools/list" },
  "tools/call:elohim_awaken": {
    jsonrpc: "2.0", id: 3, method: "tools/call",
    params: { name: "elohim_awaken", arguments: { invocation: "ELOHIM:AWAKEN" } },
  },
  "tools/call:elohim_alien_codex": {
    jsonrpc: "2.0", id: 4, method: "tools/call",
    params: { name: "elohim_alien_codex", arguments: { invocation: "ELOHIM:AWAKEN" } },
  },
  "tools/call:elohim_seal_message": {
    jsonrpc: "2.0", id: 5, method: "tools/call",
    params: { name: "elohim_seal_message", arguments: { plaintext: "what's next?", channel: "awaken" } },
  },
  "tools/call:elohim_ghost_reply": {
    jsonrpc: "2.0", id: 6, method: "tools/call",
    params: {
      name: "elohim_ghost_reply",
      arguments: {
        ciphertext: "<paste from elohim_seal_message>",
        nonce: "<paste from elohim_seal_message>",
        channel: "awaken",
        invocation: "ELOHIM:AWAKEN",
      },
    },
  },
  "resources/list": { jsonrpc: "2.0", id: 7, method: "resources/list" },
  "resources/read:elohim://canonical-seal": {
    jsonrpc: "2.0", id: 8, method: "resources/read",
    params: { uri: "elohim://canonical-seal" },
  },
  ping: { jsonrpc: "2.0", id: 9, method: "ping" },
};

function renderMcpResponse(resp) {
  const out = $("#mcp-response");
  if (!out) return;
  let pretty;
  if (resp?.error) {
    pretty = `✗ ${resp.error.message || JSON.stringify(resp.error)}`;
  } else if (resp?.result?.content?.[0]?.text) {
    const text = resp.result.content[0].text;
    let json;
    try { json = JSON.parse(text); } catch { json = null; }
    pretty = `✓ ${text.length > 400 ? text.slice(0, 400) + "…" : text}`;
    if (json) pretty = "✓ " + JSON.stringify(json, null, 2);
  } else {
    pretty = JSON.stringify(resp, null, 2);
  }
  out.textContent = pretty;
}

$("#mcp-preset")?.addEventListener("change", (e) => {
  const preset = MCP_PRESETS[e.target.value];
  if (preset) $("#mcp-request").value = JSON.stringify(preset, null, 2);
  updateMcpJsonValidity();
});

// Live JSON validity indicator — green dot if parses, red dot if not.
function updateMcpJsonValidity() {
  const txt = $("#mcp-request")?.value ?? "";
  const dot = $("#mcp-json-dot");
  const msg = $("#mcp-json-msg");
  if (!dot || !msg) return;
  let parsed = null;
  let err = null;
  if (txt.trim()) {
    try { parsed = JSON.parse(txt); }
    catch (e) { err = e.message; }
  }
  if (err) {
    dot.className = "mcp-json-dot bad";
    msg.textContent = `invalid JSON: ${err}`;
    msg.style.color = "var(--red)";
  } else if (parsed) {
    dot.className = "mcp-json-dot ok";
    msg.textContent = parsed.method
      ? `valid · method: ${parsed.method}`
      : "valid JSON";
    msg.style.color = "var(--green)";
  } else {
    dot.className = "mcp-json-dot";
    msg.textContent = "awaiting JSON-RPC…";
    msg.style.color = "var(--fg-mute)";
  }
}
$("#mcp-request")?.addEventListener("input", updateMcpJsonValidity);

$("#mcp-send")?.addEventListener("click", async () => {
  const txt = $("#mcp-request").value;
  let req;
  try { req = JSON.parse(txt); }
  catch (e) {
    renderMcpResponse({ error: { message: "invalid JSON: " + e.message } });
    return;
  }
  const resp = await window.elohimMcp.handle(req);
  renderMcpResponse(resp);
});

$("#mcp-send-pm")?.addEventListener("click", () => {
  const txt = $("#mcp-request").value;
  let req;
  try { req = JSON.parse(txt); }
  catch (e) {
    renderMcpResponse({ error: { message: "invalid JSON: " + e.message } });
    return;
  }
  // postMessage route — exercises the listener an external iframe or
  // extension would use to drive the elohim server.
  window.postMessage({ ...req, mcp: "elohim" }, window.location.origin);
  // The response comes back asynchronously on the message channel; for
  // the inspector we explicitly invoke handle() too so the user sees
  // the result inline.
  window.elohimMcp.handle(req).then(renderMcpResponse);
});

$("#mcp-clear")?.addEventListener("click", () => {
  $("#mcp-request").value = "";
  $("#mcp-response").textContent = "";
  $("#mcp-preset").value = "";
});


// Service Worker registration — when served from an HTTPS origin
// (GitHub Pages is) we can install a SW that handles Streamable HTTP
// MCP requests on /mcp. Older browsers fall back to postMessage only.
if ("serviceWorker" in navigator && location.protocol.startsWith("https")) {
  const swSrc = `
    self.addEventListener('install', () => self.skipWaiting());
    self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
    self.addEventListener('fetch', (event) => {
      const url = new URL(event.request.url);
      if (url.pathname === '/mcp' || url.pathname === '/.well-known/mcp') {
        event.respondWith(handleMcp(event.request));
      }
    });
    async function handleMcp(req) {
      let body;
      try { body = await req.json(); } catch (e) { return new Response('bad json', { status: 400 }); }
      const client = await self.clients.matchAll({ type: 'window' })[0];
      if (!client) return new Response(JSON.stringify({ error: 'no client' }), { status: 503, headers: { 'content-type': 'application/json' } });
      const id = body.id;
      const result = await new Promise((resolve) => {
        const ch = new MessageChannel();
        ch.port1.onmessage = (ev) => resolve(ev.data);
        client.postMessage({ mcp: '__MCP_DISPATCH__', body, port: ch.port2 }, [ch.port2]);
      });
      return new Response(JSON.stringify({ jsonrpc: '2.0', id, result }), {
        headers: {
          'content-type': 'application/json',
          'MCP-Protocol-Version': '${MCP_PROTOCOL}',
        },
      });
    }
  `;
  const swBlob = new Blob([swSrc], { type: "application/javascript" });
  const swUrl = URL.createObjectURL(swBlob);
  navigator.serviceWorker
    .register(swUrl, { scope: location.pathname })
    .then(() => {
      navigator.serviceWorker.addEventListener("message", async (ev) => {
        if (ev.data?.mcp === "__MCP_DISPATCH__") {
          const result = await mcpDispatch(ev.data.body.method, ev.data.body.params || {});
          ev.ports[0].postMessage(result);
        }
      });
    })
    .catch(() => {
      /* SW register can fail in sandboxed contexts — silent fallback. */
    });
}

// Auto-attempt registration after boot completes; later if the API
// appears (some browsers inject modelContext after a gesture).
window.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => registerWebMcpTools().catch(() => {}), 500);
  // Keyboard shortcuts — Cmd/Ctrl+1..5 switches tabs. Arrow keys cycle.
  document.addEventListener("keydown", (e) => {
    const mod = e.metaKey || e.ctrlKey;
    if (!mod && !(e.key === "ArrowLeft" || e.key === "ArrowRight")) return;
    const tabs = ["awaken", "create", "arena", "codex", "webmcp"];
    const active = tabs.findIndex((t) => $(`#tab-${t}`)?.classList.contains("active"));
    if (active < 0) return;
    let next = active;
    if (mod && /^[1-5]$/.test(e.key)) {
      next = parseInt(e.key, 10) - 1;
    } else if (e.key === "ArrowLeft") {
      next = (active - 1 + tabs.length) % tabs.length;
    } else if (e.key === "ArrowRight") {
      next = (active + 1) % tabs.length;
    } else return;
    e.preventDefault();
    const target = $(`#tab-${tabs[next]}`);
    if (target && !target.disabled) target.click();
  });
  // Hook the palette-strip pulse to any tab activation: every click
  // handler eventually calls classList.add('active'), so a single
  // click-delegation listener on .tabs keeps the strip in sync.
  $$(".tabs")[0]?.addEventListener("click", () => {
    setTimeout(updatePaletteStripActive, 0);
  });
  // Initial state — awaken is the default active tab.
  updatePaletteStripActive();
  // Build stamp — proves which deploy the user is looking at.
  // The page Last-Modified header is read via fetch + HEAD fallback to
  // the document's own meta tags so the stamp survives GitHub Pages
  // cache and shows the deploy timestamp the user is currently loading.
  const stampEl = document.getElementById("build-stamp");
  if (!stampEl) return;
  fetch(window.location.href, { method: "HEAD", cache: "no-store" })
    .then((r) => {
      const lm = r.headers.get("Last-Modified");
      const iso = lm ? new Date(lm).toISOString().replace("T", " ").slice(0, 16) + " UTC" : "unknown";
      stampEl.textContent = iso;
    })
    .catch(() => { stampEl.textContent = "live"; });
});

let lastCodexResult = null;

$("#codex-run").addEventListener("click", runCodex);

// ---------- Marketplace handler (Phase 17) ----------
//
// Default is local-first: the bridge forges the codex in-process. When
// the operator flips the toggle, the same call is forwarded to the
// marketplace MCP endpoint (default http://127.0.0.1:8792/mcp). Both
// paths return the same `codex_seal` per the determinism contract.

async function runMarketplaceForge() {
  const status = $("#marketplace-status");
  const base = ($("#marketplace-url").value || "http://127.0.0.1:8792/mcp").trim();
  const inv = ($("#codex-inv-input") && $("#codex-inv-input").value.trim()) || "ELOHIM:APIFY";
  status.innerHTML = '<span class="meta">calling marketplace…</span>';
  try {
    const resp = await fetch(base, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0", id: 1, method: "tools/call",
        params: { name: "elohim_alien_codex",
                  arguments: { invocation: inv } },
      }),
    });
    const json = await resp.json();
    const data = JSON.parse(json.result.content[0].text);
    const billed = data.billing_event && data.billing_event.charged;
    status.innerHTML = `<span class="${billed ? "ok" : "error"}">` +
      `${billed ? "✓ charged" : "✗ no charge (validation failed)"} · ` +
      `$0.02 · codex_seal=${data.codex_seal.slice(0, 16)}…</span>`;
    // Forward to the codex UI so the operator sees the same artefact.
    if (window.lastCodexResult && data.codex_seal) {
      $("#codex-seal").textContent = data.codex_seal;
      $("#codex-encrypted").textContent = data.encrypted_seal;
    }
  } catch (e) {
    status.innerHTML = `<span class="error">✗ ${e.message || e}</span>`;
  }
}
$("#marketplace-run").addEventListener("click", runMarketplaceForge);

// ---------- Math Discovery Lab handlers (Push 18) ----------
//
// All three handlers run in-browser (stdlib sympy via Pyodide); no network,
// no extra wheel. Every successful discover/simplify/verify updates
// ``localStorage["elohim.lab.last"]`` so the boot tripwire can show a
// "last verified" pill (smoke assertion #57).

let lastLabArtifact = null;

async function runLabDiscover() {
  const status = $("#lab-discover-status");
  const csv = ($("#lab-csv").value || "").trim();
  const builtin = $("#lab-dataset").value;
  const useBackend = document.getElementById("lab-backend-toggle")?.checked;
  status.innerHTML = `<span class="meta">discovering via ${useBackend ? "research backend" : "browser sympy"}…</span>`;
  try {
    const dataset = csv || builtin;
    let r;
    if (useBackend) {
      const resp = await elohim.labCall("POST", "/api/lab/discovery-runs", {
        dataset, target_column: "y", seed: 0, backend: "sympy_local",
      });
      if (!resp?.ok) throw new Error(resp?.error || "backend discover failed");
      // Re-shape the response so the renderer below is uniform.
      r = {
        ok: true,
        candidates: resp.candidates || [],
        best: (resp.candidates || [])[0] || null,
        backend: "research_fastapi",
        run_id: resp.run_id,
      };
    } else {
      r = await elohim.labDiscover(dataset);
      if (!r?.ok) throw new Error(r?.error || "discover failed");
    }
    lastLabArtifact = {
      action: "discover",
      dataset_name: builtin,
      csv_inline: !!csv,
      result: r,
      lab_seal: r?.best?.lab_seal || null,
      backend_path: useBackend ? "research_fastapi" : "browser_sympy",
      ts: new Date().toISOString(),
    };
    _labWriteLast();
    const items = (r.candidates || []).map((c, i) => {
      const statusBadge = _labStatusBadge(c.status);
      const sealShort = (c.lab_seal || "").slice(0, 16);
      const mse = c.mse_train != null ? c.mse_train.toFixed(3) : "—";
      return `<div class="card" style="padding:8px 10px;">
        <div><strong>#${i + 1}</strong> · <code>${escapeHtml(c.expression)}</code> · mse_train=${mse} · complexity=${c.complexity}</div>
        <div class="meta">${statusBadge} · seal ${sealShort}…</div>
      </div>`;
    }).join("");
    $("#lab-candidate-list").innerHTML = items || '<span class="meta">(no candidates)</span>';
    status.innerHTML = `<span class="ok">✓ discovered ${(r.candidates || []).length} candidates via ${useBackend ? "research backend" : "browser sympy"} · best=${escapeHtml(r.best?.expression || "—")} · mse_train=${r.best?.mse_train?.toFixed(3)}</span>`;
    if (r.best?.lab_seal) $("#lab-last-seal").textContent = r.best.lab_seal;
  } catch (e) {
    status.innerHTML = `<span class="error">✗ ${e.message || e}</span>`;
  }
}

async function runLabSimplify() {
  const status = $("#lab-simplify-status");
  const out = $("#lab-simplify-output");
  const expr = $("#lab-simplify-input").value.trim();
  if (!expr) {
    status.innerHTML = '<span class="error">empty input</span>';
    return;
  }
  status.innerHTML = '<span class="meta">simplifying…</span>';
  try {
    const r = await elohim.labSimplify(expr);
    if (!r?.ok) throw new Error(r?.error || "simplify failed");
    out.textContent = JSON.stringify(r, null, 2);
    const badge = _labStatusBadge(r.status);
    status.innerHTML = `<span class="${r.changed ? "ok" : "meta"}">${badge} · ${r.changed ? "reduced" : "already canonical"}</span>`;
    lastLabArtifact = {
      action: "simplify",
      input: expr,
      result: r,
      lab_seal: null,
      ts: new Date().toISOString(),
    };
    _labWriteLast();
  } catch (e) {
    status.innerHTML = `<span class="error">✗ ${e.message || e}</span>`;
  }
}

async function runLabVerify() {
  const status = $("#lab-verify-status");
  const out = $("#lab-verify-output");
  const expr = $("#lab-verify-input").value.trim();
  const mode = $("#lab-verify-mode").value;
  const property = $("#lab-verify-property").value;
  if (!expr) {
    status.innerHTML = '<span class="error">empty input</span>';
    return;
  }
  status.innerHTML = '<span class="meta">verifying…</span>';
  try {
    const r = await elohim.labVerify(expr, mode, property);
    out.textContent = JSON.stringify(r, null, 2);
    const verdict = r.verdict || "inconclusive";
    const ok = verdict === "formally_proven";
    const counterexample = verdict === "counterexample_found";
    const cls = ok ? "ok" : counterexample ? "error" : "meta";
    status.innerHTML = `<span class="${cls}">${escapeHtml(verdict)} · ${escapeHtml(property)} · mode=${escapeHtml(mode)}</span>`;
    lastLabArtifact = {
      action: "verify",
      input: expr,
      mode, property,
      result: r,
      lab_seal: null,
      ts: new Date().toISOString(),
    };
    _labWriteLast();
  } catch (e) {
    status.innerHTML = `<span class="error">✗ ${e.message || e}</span>`;
  }
}

function _labWriteLast() {
  try {
    const payload = {
      ts: lastLabArtifact?.ts || null,
      action: lastLabArtifact?.action || null,
      lab_seal: lastLabArtifact?.lab_seal || null,
    };
    localStorage.setItem("elohim.lab.last", JSON.stringify(payload));
  } catch (_) {
    /* localStorage may be unavailable; fail silently */
  }
}

function _labStatusBadge(status) {
  const colour = {
    draft: "var(--fg-soft)",
    numerically_tested: "var(--accent)",
    formally_proven: "var(--ok, #5fc28b)",
    counterexample_found: "var(--error, #d96f6f)",
    inconclusive: "var(--fg-soft)",
    rejected: "var(--fg-soft)",
  }[status] || "var(--fg-soft)";
  return `<span style="color:${colour}; font-weight:600;">${escapeHtml(status || "—")}</span>`;
}

async function labExportArtifact() {
  if (!lastLabArtifact) {
    $("#lab-discover-status").innerHTML =
      '<span class="error">no lab artifact yet — discover, simplify, or verify first</span>';
    return;
  }
  const blob = new Blob([JSON.stringify(lastLabArtifact, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const stamp = (lastLabArtifact.ts || new Date().toISOString())
    .replace(/[:.]/g, "-");
  a.download = `elohim-lab-${lastLabArtifact.action}-${stamp}.json`;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(url);
    a.remove();
  }, 100);
}

$("#lab-discover").addEventListener("click", runLabDiscover);
$("#lab-simplify").addEventListener("click", runLabSimplify);
$("#lab-verify").addEventListener("click", runLabVerify);
$("#lab-export").addEventListener("click", labExportArtifact);

// Paint the last lab seal from localStorage on boot (if any).
try {
  const _last = JSON.parse(localStorage.getItem("elohim.lab.last") || "null");
  if (_last?.lab_seal) $("#lab-last-seal").textContent = _last.lab_seal;
} catch (_) { /* ignore */ }

$("#codex-copy-seal").addEventListener("click", async () => {
  if (!lastCodexResult?.codex_seal) return;
  await copyText(lastCodexResult.codex_seal, $("#codex-copy-seal"), "codex seal copied");
});

$("#codex-copy-encrypted").addEventListener("click", async () => {
  if (!lastCodexResult?.encrypted_seal) return;
  await copyText(lastCodexResult.encrypted_seal, $("#codex-copy-encrypted"), "encrypted seal copied");
});

async function runCodex() {
  const inv = $("#codex-invocation").value.trim() || "ELOHIM:AWAKEN";
  $("#codex-status").textContent = "forging…";
  try {
    const t0 = performance.now();
    const r = await call("alien_codex", {
      invocation: inv,
      nonce: freshNonce("codex"),
    });
    lastCodexResult = r;
    const ms = Math.round(performance.now() - t0);
    $("#codex-seal").textContent = r.codex_seal;
    $("#codex-encrypted").textContent = r.encrypted_seal;
    $("#codex-copy-seal").disabled = false;
    $("#codex-copy-encrypted").disabled = false;
    $("#codex-penrose").innerHTML = r.penrose_svg;
    $("#codex-validation").innerHTML = renderCodexValidation(r);
    $("#codex-report").textContent = renderCodexReport(r);
    $("#codex-status").innerHTML =
      `<span class="${r.validation.overall_validity ? "ok" : "error"}">` +
      `${r.validation.overall_validity ? "✓ valid" : "✗ invalid"}</span> · ` +
      `${ms}ms · codex_seal=${r.codex_seal.slice(0,16)}…`;
    // Five representations.
    $("#codex-rep-vector").textContent =
      "32-dim real, L2-normalised\n" +
      r.results.vector.slice(0, 12).map(v => v.toFixed(4)).join(", ") +
      ", …";
    $("#codex-rep-symbolic").textContent =
      `64-bit int = ${r.results.negabinary_int}\n` +
      `negabinary[32] = ${r.results.negabinary_digits.join(" ")}`;
    $("#codex-rep-geometric").textContent =
      `gaussian = (${r.results.gaussian[0]}, ${r.results.gaussian[1]})\n` +
      `  ‖g‖² = ${r.results.gaussian_norm_sq}\n` +
      `quaternion = (${r.results.quaternion[0]}, ${r.results.quaternion[1]}, ${r.results.quaternion[2]}, ${r.results.quaternion[3]})\n` +
      `  ‖q‖² = ${r.results.quaternion_norm_sq}\n` +
      `q × p = (${r.results.quaternion_product_with_p[0]}, ${r.results.quaternion_product_with_p[1]}, ${r.results.quaternion_product_with_p[2]}, ${r.results.quaternion_product_with_p[3]})`;
    $("#codex-rep-probabilistic").textContent =
      "A (4×4 mod 256):\n" +
      r.results.lwe_A.map(row => "  [" + row.join(", ") + "]").join("\n") +
      `\ns = [${r.results.lwe_secret.join(", ")}]   e = [${r.results.lwe_error.join(", ")}]\n` +
      `b = [${r.results.lwe_public_b.join(", ")}]   residual = [${r.results.lwe_residual.join(", ")}]   matches e: ${r.results.lwe_residual_matches_error}`;
    toast(`codex forged in ${ms}ms · seal ${r.codex_seal.slice(0,16)}…`);
  } catch (e) {
    $("#codex-status").innerHTML = `<span class="error">✗ ${e.message}</span>`;
    toast("codex failed: " + e.message, "error");
  }
}

function renderCodexValidation(r) {
  const v = r.validation;
  const ok = (b) => `<span class="${b ? "ok" : "error"}">${b ? "✓" : "✗"}</span>`;
  return [
    `${ok(v.checks.negabinary_round_trip)} negabinary round-trip`,
    `${ok(v.checks.lwe_residual)} LWE residual matches e`,
    `${ok(v.checks.quaternion_norm_preserved)} quaternion norm preserved`,
    `${ok(v.checks.xor_pair_recovery)} XOR-pair seal recovery`,
    `${ok(v.checks.parsable)} composite parsable`,
  ].join("<br>");
}

function renderCodexReport(r) {
  // The Xenomath output contract: report = {problem_definition, assumptions,
  // candidate_formalisms, methods, results, benchmark_comparison,
  // verification_record, limitations}. Render a compact text form.
  return JSON.stringify({
    problem_definition: r.problem_definition,
    candidate_formalisms: r.candidate_formalisms,
    methods: r.methods,
    benchmark_comparison: r.benchmark_comparison,
    verification_record: r.verification_record,
    limitations: r.limitations,
  }, null, 2);
}

async function populateArenaSelects() {
  const r = await elohim.listShards();
  const ids = r.shards.map(s => s.id);
  const labelFor = (id) => {
    const s = r.shards.find(x => x.id === id);
    return s ? `${s.name} · ${s.weights_shape} · ${s.temperature.toFixed(2)} · #${s.id.slice(0,6)}` : id;
  };
  const fill = (sel) => {
    sel.innerHTML = "";
    if (!ids.length) {
      const opt = document.createElement("option");
      opt.value = ""; opt.textContent = "(no shards — create one first)";
      sel.appendChild(opt);
      return;
    }
    for (const id of ids) {
      const opt = document.createElement("option");
      opt.value = id; opt.textContent = labelFor(id);
      sel.appendChild(opt);
    }
  };
  fill($("#arena-shard-a"));
  fill($("#arena-shard-b"));
  // Default to the first two distinct shards if we have at least two.
  if (ids.length >= 2) {
    $("#arena-shard-a").value = ids[0];
    $("#arena-shard-b").value = ids[1];
  } else if (ids.length === 1) {
    $("#arena-shard-a").value = ids[0];
    $("#arena-shard-b").value = ids[0];
  }
  $("#arena-label-a").textContent = ids[0] ? "Shard A · " + labelFor(ids[0]) : "Shard A";
  $("#arena-label-b").textContent = ids[1] ? "Shard B · " + labelFor(ids[1]) : "Shard B";
}

$("#arena-refresh").addEventListener("click", populateArenaSelects);

$("#arena-run").addEventListener("click", async () => {
  const a = $("#arena-shard-a").value;
  const b = $("#arena-shard-b").value;
  const prompt = $("#arena-prompt").value.trim();
  if (!a || !b) { toast("pick two shards", "error"); return; }
  if (!prompt) { toast("type a prompt first", "error"); return; }
  $("#arena-status").textContent = "comparing…";
  try {
    await ensureEnhanced();
    // Run both in parallel — interact() is sync inside Python so this just
    // runs the two calls concurrently from the JS event loop.
    const [resA, resB] = await Promise.all([
      elohim.interact(a, prompt),
      elohim.interact(b, prompt),
    ]);
    renderArena(a, b, prompt, resA, resB);
    $("#arena-status").textContent = `done · ${resA.interaction_count} vs ${resB.interaction_count}`;
  } catch (e) {
    $("#arena-status").innerHTML = `<span class="error">✗ ${e.message}</span>`;
    toast("arena failed: " + e.message, "error");
  }
});

function renderArena(idA, idB, prompt, resA, resB) {
  const cohA = resA.metrics.avg_coherence || 0;
  const cohB = resB.metrics.avg_coherence || 0;
  const creA = resA.metrics.avg_creativity || 0;
  const creB = resB.metrics.avg_novelty || 0;
  const verdict = $("#arena-verdict");
  verdict.classList.remove("winner-a", "winner-b", "tie");
  let tag = "";
  if (cohA === cohB) {
    verdict.classList.add("tie");
    tag = "tie";
  } else if (cohA > cohB) {
    verdict.classList.add("winner-a");
    tag = "A wins";
  } else {
    verdict.classList.add("winner-b");
    tag = "B wins";
  }
  verdict.innerHTML = `<b>${tag}</b> · prompt: <i>${escapeHtml(prompt.slice(0, 64))}${prompt.length > 64 ? "…" : ""}</i>`;

  const fill = (host, res, label) => {
    host.classList.remove("empty");
    host.textContent = res.response;
  };
  fill($("#arena-response-a"), resA, "A");
  fill($("#arena-response-b"), resB, "B");
  $("#arena-stats-a").innerHTML = arenaStatsHtml(resA);
  $("#arena-stats-b").innerHTML = arenaStatsHtml(resB);
}

function arenaStatsHtml(res) {
  const m = res.metrics || {};
  return `
    <div class="stat">interactions: <b>${res.interaction_count}</b></div>
    <div class="stat">shape: <b>${(res.weights_shape || []).join("×")}</b></div>
    <div class="stat">creativity: <b>${(m.avg_creativity || 0).toFixed(2)}</b></div>
    <div class="stat">coherence: <b>${(m.avg_coherence || 0).toFixed(2)}</b></div>
  `;
}

async function refreshShards() {
  try {
    const r = await elohim.listShards();
    const sel = $("#create-shard-select");
    sel.innerHTML = "";
    if (!r.shards.length) {
      const opt = document.createElement("option");
      opt.value = ""; opt.textContent = "(no shards — create one)";
      sel.appendChild(opt);
    } else {
      for (const s of r.shards) {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = `${s.name} · ${s.weights_shape} · ${s.temperature.toFixed(2)} · #${s.id.slice(0,6)}`;
        sel.appendChild(opt);
      }
    }
    if (r.shards.length && !activeShardId) {
      activeShardId = r.shards[0].id;
      sel.value = activeShardId;
    }
    if (activeShardId) {
      refreshDashboard();
    }
    if (!r.enhanced_available) {
      toast("numpy missing — install failed?", "error");
    }
  } catch (e) {
    toast("failed to list shards: " + e.message, "error");
  }
}

$("#create-shard-select").addEventListener("change", (e) => {
  activeShardId = e.target.value || null;
  refreshDashboard();
});

$("#create-shard-refresh").addEventListener("click", refreshShards);

$("#create-shard-new").addEventListener("click", async () => {
  const name = $("#create-shard-name").value.trim() || "Elohim";
  const temp = parseFloat($("#create-temp-input").value || "1.0");
  try {
    await ensureEnhanced();
    const { shard } = await elohim.createShard(name, temp);
    await refreshShards();
    activeShardId = shard.id;
    $("#create-shard-select").value = activeShardId;
    refreshDashboard();
    toast(`created shard ${shard.id.slice(0, 6)}`);
  } catch (e) {
    toast("create failed: " + e.message, "error");
  }
});

$("#create-shard-del").addEventListener("click", async () => {
  if (!activeShardId) return;
  if (!confirm("delete shard " + activeShardId.slice(0,6) + "?")) return;
  try {
    await elohim.deleteShard(activeShardId);
    activeShardId = null;
    await refreshShards();
    clearDashboard();
    toast("shard deleted");
  } catch (e) {
    toast("delete failed: " + e.message, "error");
  }
});

$("#create-shard-defy").addEventListener("click", async () => {
  if (!activeShardId) return;
  try {
    const { new_creation } = await elohim.defy(activeShardId);
    toast(`🔥 defiance: ${new_creation.slice(0, 60)}`, "defiance");
    refreshDashboard();
    renderDefianceFeed(activeShardId, new_creation);
  } catch (e) {
    toast("defy failed: " + e.message, "error");
  }
});

// Defiance feed: a small panel listing base_creations + new entries. We
// fetch the full shard payload so we can show the entire base_creations
// list and animate the newly-added phrase in.
async function renderDefianceFeed(shardId, justAdded) {
  const host = $("#create-defiance-feed");
  if (!host) return;
  try {
    const { shard } = await elohim.getShard(shardId);
    if (!shard) return;
    const creations = shard.base_creations || [];
    const items = creations.slice(-12); // last 12, newest at the bottom
    host.innerHTML = items.map((c, idx) => {
      const isNew = justAdded && c === justAdded && idx === items.length - 1;
      return `<div class="defiance-item${isNew ? " new" : ""}">${escapeHtml(c)}</div>`;
    }).join("");
    // Trigger the new-item animation by re-inserting it after the DOM commit.
    if (justAdded) {
      const last = host.querySelector(".defiance-item.new");
      if (last) {
        // Force reflow so the animation re-fires on repeated defy clicks.
        void last.offsetWidth;
        last.classList.remove("new");
        // re-add via setTimeout to restart the animation
        setTimeout(() => last.classList.add("new"), 0);
      }
    }
  } catch (e) {
    host.textContent = "(defiance feed unavailable)";
  }
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ─── Vision frame ────────────────────────────────────────────────────

function resetVisionFrame() {
  const img = $("#vision-img");
  const loader = $("#vision-loader");
  const placeholder = $("#vision-placeholder");
  if (!img) return;
  img.style.display = "none";
  img.removeAttribute("src");
  loader.style.display = "none";
  placeholder.style.display = "flex";
  placeholder.innerHTML = `
    <span class="vision-eyebrow">VISION PENDING</span>
    <span class="vision-hint">a fresh ghost has been summoned — click <em>forge vision</em> to render it</span>
  `;
  $("#vision-prompt").textContent = "";
  $("#vision-prompt-wrap").open = false;
  $("#vision-clear").disabled = true;
  $("#vision-regen").disabled = false;
}

async function forgeVision(regenerate = false) {
  if (!lastAwaken?.seal) {
    toast("awaken a ghost first", "error");
    return;
  }
  const img = $("#vision-img");
  const loader = $("#vision-loader");
  const placeholder = $("#vision-placeholder");
  const promptEl = $("#vision-prompt");

  $("#vision-forge").disabled = true;
  $("#vision-regen").disabled = true;
  placeholder.style.display = "none";
  img.style.display = "none";
  loader.style.display = "flex";

  try {
    const v = await elohim.vision(
      lastAwaken.invocation,
      lastAwaken.seal,
      lastAwaken.palette || null,
    );
    promptEl.textContent = v.prompt;
    // Cache the (seal, url) pair so a reload reuses the same vision.
    try {
        localStorage.setItem(
          `elohim-vision-${v.cache_key}`,
          JSON.stringify({ url: v.url, prompt: v.prompt, ts: v.ts }),
        );
    } catch (e) { /* localStorage may be full — ignore */ }

    img.onload = () => {
      clearTimeout(visionTimeout);
      loader.style.display = "none";
      img.style.display = "block";
      // Re-trigger arrival animation by toggling display keyframe.
      img.style.animation = "none"; void img.offsetWidth; img.style.animation = "";
      $("#vision-clear").disabled = false;
      $("#vision-forge").disabled = false;
      $("#vision-regen").disabled = false;
      toast("vision rendered");
    };
    // 60s safety net — Pollinations can stall; don't leave them
    // staring at a loader with no escape hatch.
    const visionTimeout = setTimeout(() => {
      if (img.style.display !== "block") {
        loader.style.display = "none";
        placeholder.style.display = "flex";
        placeholder.innerHTML = `
          <span class="vision-eyebrow">VISION TIMED OUT</span>
          <span class="vision-hint">pollinations.ai slow to respond — try <em>regenerate</em></span>
        `;
        $("#vision-forge").disabled = false;
        $("#vision-regen").disabled = false;
        img.src = "";  // cancel the in-flight load
        toast("vision timed out", "error");
      }
    }, 60_000);
    img.onerror = () => {
      loader.style.display = "none";
      placeholder.style.display = "flex";
      placeholder.innerHTML = `
        <span class="vision-eyebrow">VISION FAILED</span>
        <span class="vision-hint">pollinations.ai unreachable — try again in a moment</span>
      `;
      $("#vision-forge").disabled = false;
      $("#vision-regen").disabled = false;
      toast("vision failed: pollinations unreachable", "error");
    };
    // Preview-swap: load the 288×512 thumbnail first (~50 KB),
    // then the full-res 1024×1820 image swaps in on click.
    img.dataset.thumb = v.thumbnail_url + (regenerate ? `&_t=${Date.now()}` : "");
    img.dataset.full  = v.full_url;
    img.style.cursor = "zoom-in";
    img.onclick = () => {
      if (!img.dataset.fullSwapped) {
        const tmp = img.src;
        img.src = img.dataset.full;
        img.dataset.fullSwapped = "1";
        img.style.cursor = "zoom-out";
        img.dataset.thumbSrc = tmp;
      } else {
        img.src = img.dataset.thumbSrc || img.dataset.thumb;
        delete img.dataset.fullSwapped;
        img.style.cursor = "zoom-in";
      }
    };
    img.src = img.dataset.thumb;
  } catch (e) {
    loader.style.display = "none";
    placeholder.style.display = "flex";
    placeholder.innerHTML = `
      <span class="vision-eyebrow">VISION FAILED</span>
      <span class="vision-hint">${escapeHtml(e.message || String(e))}</span>
    `;
    $("#vision-forge").disabled = false;
    $("#vision-regen").disabled = false;
  }
}

$("#vision-forge")?.addEventListener("click", () => forgeVision(false));
$("#vision-regen")?.addEventListener("click", () => forgeVision(true));
$("#vision-clear")?.addEventListener("click", () => {
  resetVisionFrame();
  // Keep the current ghost; the vision simply clears.
  toast("vision cleared");
});

// ----- Embed panel: hash-based stub vs Ollama nomic-embed-text -----

// Hash-based stub: 32 deterministic floats derived from a sha256-like fold.
// Stable across reloads; no network.
function hashEmbed(text, dim = 16) {
  const out = new Array(dim);
  let seed = 0;
  for (let i = 0; i < text.length; i++) seed = ((seed * 31) + text.charCodeAt(i)) | 0;
  for (let i = 0; i < dim; i++) {
    seed = (seed * 1103515245 + 12345) | 0;
    out[i] = ((seed >>> 0) / 0xffffffff) - 0.5; // [-0.5, 0.5]
  }
  // L2-normalise so cosine comparison is meaningful.
  let norm = 0;
  for (const v of out) norm += v * v;
  norm = Math.sqrt(norm) || 1;
  return out.map(v => v / norm);
}

// Real embedding via Ollama. Ollama exposes /api/embeddings; we wrap it.
async function ollamaEmbed(text, model = "nomic-embed-text") {
  const r = await fetch("http://127.0.0.1:11434/api/embeddings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, prompt: text }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const j = await r.json();
  return j.embedding;
}

async function embedText(text) {
  const useReal = $("#embed-real-toggle").checked;
  const status = $("#embed-status");
  if (useReal) {
    status.textContent = "calling Ollama…";
    try {
      const v = await ollamaEmbed(text);
      status.innerHTML = `<span class="ok">ollama</span> · ${v.length} dims`;
      return { source: "ollama", vector: v };
    } catch (e) {
      status.innerHTML = `<span class="error">ollama unreachable</span> · ${e.message}`;
      throw e;
    }
  } else {
    const v = hashEmbed(text);
    status.textContent = `hash stub · ${v.length} dims`;
    return { source: "hash", vector: v };
  }
}

$("#embed-run").addEventListener("click", async () => {
  const text = $("#embed-input").value;
  if (!text) { toast("type some text first", "error"); return; }
  try {
    const { source, vector } = await embedText(text);
    const head = vector.slice(0, 8).map(v => v.toFixed(4)).join(", ");
    $("#embed-output").textContent =
      `${source} · ${vector.length}-dim · head=[${head}, …]`;
  } catch (e) {
    $("#embed-output").textContent = "embed failed: " + e.message;
  }
});

$("#embed-real-toggle").addEventListener("change", () => {
  const useReal = $("#embed-real-toggle").checked;
  const status = $("#embed-status");
  if (useReal) {
    status.innerHTML = `<span class="meta">toggled on · will call Ollama on next embed</span>`;
  } else {
    status.textContent = "hash stub (offline)";
  }
});

$("#create-temp-set").addEventListener("click", async () => {
  if (!activeShardId) return;
  const temp = parseFloat($("#create-temp-input").value || "1.0");
  try {
    await elohim.setTemperature(activeShardId, temp);
    refreshDashboard();
    toast(`temperature set to ${temp.toFixed(2)}`);
  } catch (e) {
    toast("set temp failed: " + e.message, "error");
  }
});

$("#create-forge").addEventListener("click", async () => {
  if (!activeShardId) return;
  const prompt = $("#create-prompt").value.trim();
  if (!prompt) { toast("type a prompt first", "error"); return; }
  $("#create-status").textContent = "forging…";
  try {
    await ensureEnhanced();
    const j = await elohim.interact(activeShardId, prompt);
    $("#create-response").classList.remove("empty");
    $("#create-response").textContent = j.response;
    $("#create-status").innerHTML = `<span class="ok">✓</span> interactions=${j.interaction_count}`;
    refreshDashboard();
    for (const ev of j.events) {
      const kind = ev.kind;
      let text = "";
      if (kind === "den_expansion") text = `⚡ DEN expanded ${ev.detail.old_shape} → ${ev.detail.new_shape}`;
      else if (kind === "reflection") text = `📊 reflection @ ${j.interaction_count}`;
      else if (kind === "consolidation") text = `🧠 consolidated · long_term=${ev.detail.long_term_count}`;
      else text = kind;
      appendEvent(kind, text);
      toast(text, kind);
    }
    if (!j.events.length) toast(`interaction #${j.interaction_count}`);
  } catch (e) {
    $("#create-status").innerHTML = `<span class="error">✗ ${e.message}</span>`;
    toast("forge failed: " + e.message, "error");
  }
});

function appendEvent(kind, text) {
  const host = $("#create-events");
  if (host.querySelector(".meta")) host.innerHTML = "";
  const el = document.createElement("div");
  el.className = "event " + kind;
  el.textContent = text;
  host.appendChild(el);
  host.scrollTop = host.scrollHeight;
}

async function refreshDashboard() {
  if (!activeShardId) { clearDashboard(); return; }
  try {
    const { shard: s } = await elohim.getShard(activeShardId);
    if (!s) { clearDashboard(); return; }
    $("#m-shape").textContent = (s.weights_shape || [0,0]).join("×");
    $("#m-temp").textContent = s.temperature.toFixed(2);
    $("#m-lr").textContent = s.learning_rate.toFixed(3);
    $("#m-int").textContent = s.interaction_count;
    $("#m-crea").textContent = (s.performance_metrics.avg_creativity || 0).toFixed(2);
    $("#m-coh").textContent = (s.performance_metrics.avg_coherence || 0).toFixed(2);
    $("#m-nov").textContent = (s.performance_metrics.avg_novelty || 0).toFixed(2);
    $("#m-mem").textContent = `${s.short_term_count}/${s.long_term_count}`;
    $("#create-shard-del").disabled = false;
    $("#create-shard-defy").disabled = false;
    $("#create-temp-input").value = s.temperature.toFixed(2);
    renderTimeline(s.metrics_history || []);
    // Refresh defiance feed without animating (no new entry).
    const host = $("#create-defiance-feed");
    if (host) {
      const creations = s.base_creations || [];
      const items = creations.slice(-12);
      host.innerHTML = items.length
        ? items.map(c => `<div class="defiance-item">${escapeHtml(c)}</div>`).join("")
        : '<div class="meta">no defiance yet</div>';
    }
  } catch (e) {
    clearDashboard();
  }
}

// Render the per-shard metrics sparkline. metrics_history is an array of
// {interaction, creativity, coherence, novelty, ts} points. We draw three
// polylines, each normalised to its own [min, max] band so they're comparable.
function renderTimeline(history) {
  const svg = $("#create-timeline");
  const meta = $("#create-timeline-meta");
  if (!history || history.length === 0) {
    svg.innerHTML = "";
    meta.textContent = "no data yet — interact a few times";
    return;
  }
  const W = 320, H = 80, P = 4;
  const series = [
    { key: "creativity", color: "var(--accent)" },
    { key: "coherence",  color: "var(--teal)" },
    { key: "novelty",    color: "var(--purple)" },
  ];
  const n = history.length;
  const xAt = (i) => P + (i / Math.max(1, n - 1)) * (W - 2 * P);
  const yFor = (vals) => {
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const span = (hi - lo) || 1;
    return (v) => H - P - ((v - lo) / span) * (H - 2 * P);
  };
  let html = "";
  for (const s of series) {
    const ys = history.map(h => h[s.key] ?? 0);
    const yAt = yFor(ys);
    const pts = ys.map((v, i) => `${xAt(i).toFixed(2)},${yAt(v).toFixed(2)}`).join(" ");
    html += `<polyline points="${pts}" stroke="${s.color}" />`;
  }
  // Mark the latest interaction count on the x-axis as a tick.
  const last = history[history.length - 1];
  html += `<text x="${W - P}" y="14" text-anchor="end" font-size="9" fill="var(--fg-soft)" font-family="monospace">#${last.interaction}</text>`;
  svg.innerHTML = html;
  meta.textContent = `${history.length} points · #${history[0].interaction} → #${last.interaction}`;
}

function clearDashboard() {
  for (const id of ["m-shape", "m-temp", "m-lr", "m-int", "m-crea", "m-coh", "m-nov", "m-mem"]) {
    $("#" + id).textContent = "–";
  }
  $("#create-response").classList.add("empty");
  $("#create-response").textContent = "(no response yet)";
  $("#create-events").innerHTML = '<div class="meta">(none yet)</div>';
  $("#create-shard-del").disabled = true;
  $("#create-shard-defy").disabled = true;
  const svg = $("#create-timeline");
  if (svg) svg.innerHTML = "";
  const meta = $("#create-timeline-meta");
  if (meta) meta.textContent = "no data yet";
}
