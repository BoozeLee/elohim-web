# Math Discovery Lab — operator guide

The Math Discovery Lab (Push 18) is the third pillar of elohim-web alongside
`elohim_summoning` (Xenomath / Pisot / Collatz) and `elohim_enhanced`
(numpy-powered creative shard). Where the existing pillars *report on* a
chosen invocation, the Lab **searches for new relations** and **proves
or disproves** them with a lifecycle state machine.

The Lab has four backends; the canonical elohim_summoning seal
(`5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596`)
is **never** in any lab payload.

## Quickstart (browser)

Open `https://boozelee.github.io/elohim-web/` and click the **lab · discovery**
tab. Three surfaces are available without any local install:

| Action    | What it does                                  | Backend       |
|-----------|-----------------------------------------------|---------------|
| discover  | rank candidate expressions against a dataset | in-browser sympy |
| simplify  | `sympy.simplify(expr)` with a status pill      | in-browser sympy |
| verify    | check a structural claim (mode `sympy`)        | in-browser sympy |

The default mode is in-browser sympy (Pyodide 0.27.8 + the sympy wheel
loaded at boot). All five canonical datasets ship inline: `cubic`,
`sine_decay`, `lorenz_x`, or paste your own CSV.

## Local backend (optional)

For the full four-engine matrix (sympy + Z3 + Julia + Lean), boot the
lab FastAPI subcommand:

```bash
# Vault + Lab on the same FastAPI process (recommended):
cd /home/kilisan/elohim
python -m elohim_webapp vault --port 8780

# Just the lab API on its own port:
cd /home/kilisan/elohim
python -m elohim_webapp lab --port 8793
```

Both expose `/api/lab/healthz`, `/api/lab/discovery-runs`,
`/api/lab/verify/{run_id}`, `/api/lab/runs/{id}`, `/api/lab/tiers`,
`/api/lab/artifacts/{hash}`.

The SPA's "use research backend" toggle routes `lab_discover` to the
local FastAPI when toggled on. Default is off (in-browser sympy).

## Installing the heavy backends

The Lab is designed to **gracefully skip** any missing backend — the
smoke harness asserts on `shutil.which('julia')` and
`shutil.which('lake')` and skips cleanly. To enable all four:

### Julia (via mise, matches your existing Python/Go stack)

```bash
mise use -g julia@1.11
# First run downloads + precompiles SymbolicRegression (~30 s)
julia --project=/home/kilisan/elohim/julia/AMDL -e 'using AMDL; AMDL.discover_equation("...", "y", "/tmp/out.json")'
```

Override the project location with `AMDL_JULIA_PROJECT=/path/to/AMDL`
env var.

### Lean 4 (via elan, official toolchain installer)

```bash
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh
# source the env, then:
cd /home/kilisan/elohim/lean/AMDL && lake build
# First build downloads + compiles Mathlib (~10 min)
```

`~/.elan` and `~/.cache/lake` are cached across runs. Override the project
location with `AMDL_LEAN_PROJECT=/path/to/AMDL` env var.

### Z3 (via pip — wheels available for Python 3.14 since Jul 2026)

```bash
pip install "z3-solver>=5.0"
```

If `pip install z3-solver` fails (rare; AArch64 or musl), fall back to:

```bash
sudo pacman -S z3
pip install z3-solver --no-binary z3-solver
```

## API quickstart

```bash
# Health
curl http://127.0.0.1:8780/api/lab/healthz | python -m json.tool

# Start a discovery run
curl -X POST -H 'Content-Type: application/json' \
  -d '{"dataset":"cubic","backend":"sympy_local","seed":0}' \
  http://127.0.0.1:8780/api/lab/discovery-runs | python -m json.tool

# Verify a candidate (counterexample for -1 via sympy_local)
# (first store the candidate via /discovery-runs, then use its id)
curl -X POST -H 'Content-Type: application/json' \
  -d '{"candidate_id":"<cid>","mode":"sympy","property":"nonnegative"}' \
  http://127.0.0.1:8780/api/lab/verify/<run_id> | python -m json.tool
```

## Lifecycle reference

Every candidate moves through a strict DAG:

```
draft ──► numerically_tested ──► formally_proven
                                └► counterexample_found
                                └► rejected
                                └► inconclusive
```

The DAG is enforced in Python (`elohim_lab.lifecycle.advance`). The
SQL `lab_candidates.status` column is for human inspection only.

| Status | Meaning |
|---|---|
| `draft` | freshly stored; no MSE has run |
| `numerically_tested` | a numeric metric (mse_train) has been recorded |
| `formally_proven` | sympy or z3 returned `verdict: formally_proven` |
| `counterexample_found` | z3 / sympy found a witness |
| `inconclusive` | no human-readable result, e.g. unsupported property |
| `rejected` | manual operator reject (Push 19+) |

Every status push is sealed with `lab_seal(record, status, version) →
64-hex sha256`. The cache TTL is 10 minutes on GitHub Pages; rebuilds
after each push land in `elohim_lab.service.LabService`.

## Threat model

- All lab routes bind to `127.0.0.1` — no public exposure.
- No auth (matches vault + marketplace policy). Free tier = unlimited
  local runs.
- Inputs are typed Pydantic models — FastAPI rejects malformed
  payloads with 422.
- Backend dispatcher validates `backend ∈ {sympy_local, z3_verify,
  julia_sr, lean_verify}` via `Literal` — unknown backends return 422.
- No `eval`/`exec`/`shell=True`. All subprocess calls use list-form
  `subprocess.run([...], timeout=…)`.
- Julia / Lean subprocess output is capped at 4 KB to avoid runaway
  logs.
- Z3 runs in-process; sympy runs in-process. Julia and Lean are
  isolated subprocesses.

## Layout

```
elohim/
├── src/elohim_lab/                 # core Python package (Push 18a)
│   ├── core.py                     # VerificationStatus enum + records
│   ├── lifecycle.py                # DAG state machine
│   ├── seal.py                     # lab_seal()
│   ├── service.py                  # LabService (Push 18bc)
│   ├── backends/
│   │   ├── sympy_local.py          # always-on
│   │   ├── z3_verify.py            # in-process Z3
│   │   ├── julia_sr.py             # subprocess wrapper
│   │   └── lean_verify.py          # subprocess wrapper
│   └── tests/                      # pytest, 42 passing + 5 skipped
├── src/elohim_webapp/
│   ├── routes_lab.py               # FastAPI router (Push 18bc)
│   ├── app.py                      # mounts /api/lab/*
│   ├── __main__.py                 # `lab` subcommand
│   └── migrations/0002_lab_runs.sql
├── julia/AMDL/                     # vendored Julia micro-project
└── lean/AMDL/                      # vendored Lean micro-project

elohim-web/
├── py/elohim_webapp/
│   ├── bridge.py                   # in-browser lab_* functions (18a)
│   └── lab_seal.py                 # vendored sha256 (18a)
├── index.html                      # Lab tab + research-backend toggle
├── smoke.py                        # 60 required + 4 optional assertions
└── docs/lab.md                     # this file
```

## Acceptance

| Check | Result |
|---|---|
| In-browser sympy discover (cubic) | mse < 0.5, best candidate contains x**3 |
| In-browser sympy simplify | sin²+cos² → 1 |
| In-browser sympy verify x²+1 | formally_proven |
| FastAPI /api/lab/discovery-runs | 202 with valid UUID |
| FastAPI /api/lab/verify/{id} | verdict + lab_seal |
| z3-solver installed | counterexample_found for -1 |
| Julia installed | AMDL.discover_equation on cubic.csv returns x**3 candidate |
| Lean installed | `lake build` returns 0 |
| Canonical seal | 5f12cc… unchanged, re-verified every smoke |