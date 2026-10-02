# elohim-web

A single-page browser deployment of the **elohim** monorepo. Pyodide runs the
real Python stack — `elohim_summoning` (stdlib math+sigil) and `elohim_enhanced`
(numpy-powered creative shard) — entirely client-side, so the canonical sha256
contract is verifiable in the browser itself, not just on a backend.

Deployed via GitHub Pages on `BoozeLee/elohim-web`. No servers, no build step.

## What ships here

| Path | What it is |
|---|---|
| `index.html` | The single-page app. Bootstraps Pyodide, fetches the Python source, exposes the API as `window.elohim.*`. |
| `py/elohim_summoning/` | The stdlib-only math+sigil instrument, vendored from the monorepo verbatim (11 modules). |
| `py/elohim_enhanced/` | The numpy-powered creative shard, vendored from the monorepo verbatim (10 modules). |
| `py/elohim_webapp/bridge.py` | The Pyodide bridge module: pure-Python functions that JS invokes via `pyodide.runPython`. Replaces `elohim_webapp.app` from the FastAPI version. |
| `py/elohim_webapp/__init__.py` | Package marker. |
| `smoke.py` | Local Playwright smoke test — opens the app in headless Chromium, verifies the seal, exercises every public endpoint. |
| `dist/` | (Empty placeholder — the deploy repo doesn't ship a wheel. See `BoozeLee/elohim` for the PyPI-style wheel.) |

## Canonical seal

```
5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596
```

The boot screen calls `bridge.verify_seal()` immediately after loading Pyodide
and refuses to enable the SPA if the in-browser seal differs from this value.
A green "seal recorded" badge in the header indicates the tripwire passed.

## Architecture

```
   ┌──────────────────────────────────────────────────┐
   │ Browser (Chromium / Firefox / Safari)            │
   │ ┌────────────────────────────────────────────┐   │
   │ │ index.html (the SPA)                       │   │
   │ │   │                                        │   │
   │ │   ▼                                        │   │
   │ │ window.elohim.* ──► pyodide.runPython()    │   │
   │ │                       │                    │   │
   │ │                       ▼                    │   │
   │ │ ┌──────────────────────────────────────┐   │   │
   │ │ │ elohim_webapp.bridge                 │   │   │
   │ │ │   version / awaken / list_shards /   │   │   │
   │ │ │   create_shard / interact /          │   │   │
   │ │ │   set_temperature / defy / delete     │   │   │
   │ │ └──────────────────────────────────────┘   │   │
   │ │   │                                        │   │
   │ │   ├─► elohim_summoning (stdlib math+sigil) │   │
   │ │   └─► elohim_enhanced  (numpy shard)       │   │
   │ │                                            │   │
   │ │   localStorage ◄──── shard persistence     │   │
   │ │   MEMFS (/tmp/elohim-out) ◄── artifacts   │   │
   │ └────────────────────────────────────────────┘   │
   │                                                  │
   │ Pyodide runtime (CDN)        numpy (CDN)         │
   └──────────────────────────────────────────────────┘
```

### Storage

- **Shards** — persisted in browser `localStorage` under `elohim.shard.<id>`,
  one JSON key per shard. Same wire format as the server-side `state.py`
  serialiser; can round-trip with the FastAPI webapp.
- **Awaken artifacts** — written to Pyodide's in-memory MEMFS at
  `/tmp/elohim-out/<ts>-<safe_inv>/`. The SVG is read back as a string and
  rendered inline; the user can download it.
- **Awaken history** — last 100 invocations appended to
  `localStorage["elohim.awaken.history"]`.

### JS↔Python bridge

Every call goes through `bridge._invoke(name, args, kwargs)`, a tiny Python
dispatch helper. JS builds a kwargs JSON string, parses it with
`json.loads(...)` inside Python, and reads back the JSON-encoded return value.
This avoids PyProxy reference cycles and lets the surface evolve without
forcing JS to keep a fixed import list.

### Lazy vs eager numpy

Numpy and the seven `elohim_enhanced` submodules are loaded eagerly at boot
(not lazily on first Create-tab click). Pyodide 0.27.x's first
`loadPackagesFromImports` call from inside an event handler can hang; pulling
it out into the boot flow keeps the SPA responsive. The boot progress bar
shows the numpy load explicitly.

## How to run locally

```bash
cd elohim-web
/usr/bin/python3 -m http.server 8780
# open http://127.0.0.1:8780/ in any modern browser
```

For a CI smoke test:

```bash
/usr/bin/python3 -m playwright install chromium
/usr/bin/python3 smoke.py
```

The smoke test takes ~60 seconds (Pyodide wasm + stdlib + numpy download).
It verifies:

1. Boot completes without errors.
2. The in-browser seal matches the canonical constant.
3. `awaken("ELOHIM:AWAKEN")` returns the canonical seal + a valid SVG.
4. The Create tab loads (numpy available).
5. `createShard` returns a shard with weights `[5, 5]`.
6. `interact` runs and produces a `den_expansion` event on the first call.
7. `setTemperature`, `defy`, `listShards`, `deleteShard` all round-trip.

## How to deploy

Push to `main`. GitHub Pages serves the repo root as-is — no build step:

```bash
git push origin main
# Then in the GitHub web UI: Settings → Pages → Source: Deploy from branch → main / root
```

The first deploy takes ~30 seconds; subsequent deploys are atomic.

## Author

Kiliaan vanvoorder — `bakerstreetbandit@zohomail.eu`

Source: [`BoozeLee/elohim`](https://github.com/BoozeLee/elohim) (monorepo)