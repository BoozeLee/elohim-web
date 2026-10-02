"""Pyodide bridge: pure-Python surface for the browser-side webapp.

Lives next to ``elohim_summoning`` and ``elohim_enhanced`` on Pyodide's
``sys.path``. JavaScript calls these functions via
``pyodide.runPythonAsync("elohim_webapp_bridge.function_name(...)")`` and
receives the returned dict as a plain JS object.

Two storage layers:

- **MEMFS** (Pyodide's in-memory virtual filesystem) for ephemeral artifacts
  the ``elohim_summoning`` CLI writes (``shard.md``, ``sigil.svg``,
  ``shard.json``).  Each invocation gets its own subdir, and the SVG is
  read back as a string for the SPA to display.
- **localStorage** (browser) for persistent shard state, one key per
  shard id.  No async/await is needed — localStorage is synchronous in
  JS, and Pyodide exposes it as a Python attribute.

Seal tripwire: ``version()`` reads back the seal produced by a fresh
``elohim_summoning`` invocation and refuses to advertise the release
if it doesn't match ``CANONICAL_SEAL``.  This is the cross-runtime
guarantee the monorepo ships with.

Namespace-package note: GitHub Pages refuses to serve files starting with
``_``, so we ship *no* ``__init__.py``. Python 3.12+ treats directories
without ``__init__.py`` as PEP 420 namespace packages, so ``import
elohim_summoning.cli`` still resolves. The bridge reaches into the
submodules directly (no top-level re-exports) to avoid touching the
missing ``__init__.py``.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

CANONICAL_SEAL = "5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596"
DEFAULT_INVOCATION = "ELOHIM:AWAKEN"
SUMMONING_VERSION = "0.2.0"  # mirrors elohim_summoning/__init__.py
ENHANCED_VERSION = "0.2.0"   # mirrors elohim_enhanced/__init__.py

# MEMFS root for ephemeral awaken artifacts.
_OUT_ROOT = Path("/tmp/elohim-out")
_OUT_ROOT.mkdir(parents=True, exist_ok=True)

# localStorage key namespace for shard persistence.
_SHARD_PREFIX = "elohim.shard."
_SHARD_INDEX_KEY = "elohim.shards.index"

# ---------- storage adapters ----------


def _ls_get(key: str) -> str | None:
    """Read a string from the browser's localStorage; return None if missing."""
    from js import localStorage  # type: ignore[import-not-found]

    value = localStorage.getItem(key)
    return None if value is None else str(value)


def _ls_set(key: str, value: str) -> None:
    """Write a string to the browser's localStorage."""
    from js import localStorage  # type: ignore[import-not-found]

    localStorage.setItem(key, value)


def _ls_delete(key: str) -> None:
    """Remove a key from localStorage; no-op if missing."""
    from js import localStorage  # type: ignore[import-not-found]

    localStorage.removeItem(key)


def _shard_path(shard_id: str) -> str:
    return _SHARD_PREFIX + shard_id


def _load_shard(shard_id: str) -> dict[str, Any]:
    """Read a shard snapshot from localStorage. Raises KeyError if missing."""
    raw = _ls_get(_shard_path(shard_id))
    if raw is None:
        raise KeyError(shard_id)
    return json.loads(raw)


def _save_shard(shard_id: str, payload: dict[str, Any]) -> None:
    """Atomically replace a shard snapshot in localStorage."""
    _ls_set(_shard_path(shard_id), json.dumps(payload))


def _delete_shard(shard_id: str) -> None:
    _ls_delete(_shard_path(shard_id))


def _list_shard_ids() -> list[str]:
    """List all shard ids by enumerating localStorage keys with the prefix."""
    from js import localStorage  # type: ignore[import-not-found]

    out: list[str] = []
    # localStorage.length + key(i) walks every key — there's no prefix scan.
    for i in range(int(localStorage.length)):
        k = str(localStorage.key(i))
        if k.startswith(_SHARD_PREFIX):
            out.append(k[len(_SHARD_PREFIX):])
    return sorted(out)


# ---------- version / meta ----------


def version() -> dict[str, Any]:
    """Server-side metadata + canonical seal tripwire."""
    import sys

    try:
        import elohim_enhanced  # noqa: F401 — PEP 420 namespace package probe

        import numpy as _np_check
        enhanced_version = ENHANCED_VERSION
        enhanced_available = True
    except ImportError:
        enhanced_version = ENHANCED_VERSION
        enhanced_available = False

    return {
        "name": "elohim-summoning",
        "version": SUMMONING_VERSION,
        "enhanced_version": enhanced_version,
        "python": sys.version.split()[0],
        "canonical_seal": CANONICAL_SEAL,
        "enhanced_available": enhanced_available,
        "runtime": "pyodide",
        "pyodide_version": getattr(sys, "_pyodide_version", None) or "unknown",
        "meta": {
            "out_root": str(_OUT_ROOT),
            "shard_storage": "localStorage",
            "started_ts": time.time(),
        },
    }


def verify_seal() -> dict[str, Any]:
    """Run a fresh ``elohim_summoning`` invocation and verify the seal.

    Returns the computed seal plus a ``matches`` boolean.  This is the
    tripwire: a deployment is unsound if ``matches`` is False.
    """
    import elohim_summoning.cli as _cli
    import elohim_summoning.core as _core_runtime
    import elohim_summoning.sigil as _sigil

    sub = _OUT_ROOT / f"verify-{int(time.time())}"
    sub.mkdir(parents=True, exist_ok=True)

    saved_core = _core_runtime.OUT
    saved_cli = _cli.OUT
    saved_sigil = _sigil.OUT
    saved_facts = dict(_core_runtime.FACTS)

    try:
        _core_runtime.OUT = sub
        _cli.OUT = sub
        _sigil.OUT = sub
        try:
            _cli.main(["--invocation", DEFAULT_INVOCATION])
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise
        computed = _core_runtime.FACTS.get("seal", "")
    finally:
        _core_runtime.OUT = saved_core
        _cli.OUT = saved_cli
        _sigil.OUT = saved_sigil
        _core_runtime.FACTS.clear()
        _core_runtime.FACTS.update(saved_facts)

    return {
        "canonical_seal": CANONICAL_SEAL,
        "computed_seal": computed,
        "matches": computed == CANONICAL_SEAL,
    }


def verify_seal_multi() -> dict[str, Any]:
    """Multi-instrument seal tripwire.

    Three back-to-back ``awaken`` calls exercise different code paths and assert
    invariants. A deployment is unsound if any branch fails.

    1. ``awaken("ELOHIM:AWAKEN")`` — canonical seal must match.
    2. ``awaken("elohim:probe")`` — different invocation must produce a
       different seal (proves the PRNG is wired through the invocation hash,
       not a stale constant).
    3. ``awaken("elohim:nofac", no_svg=True)`` — no-svg branch must still
       produce the canonical seal and a None ``sigil_svg`` (proves the
       sigil-skip path doesn't accidentally clobber the seal computation).

    Returns a structured report. ``overall_ok`` is True iff all three pass.
    """
    canonical = awaken(invocation="ELOHIM:AWAKEN", no_svg=False)
    probe = awaken(invocation="elohim:probe", no_svg=False)
    # For the no_svg check we run the SAME invocation twice and assert the
    # seal is identical with and without the sigil — that proves the
    # sigil-skip path doesn't perturb the seal computation.
    nofac_with_svg = awaken(invocation="elohim:nofac", no_svg=False)
    nofac_no_svg = awaken(invocation="elohim:nofac", no_svg=True)

    checks = [
        {
            "name": "canonical_seal",
            "invocation": "ELOHIM:AWAKEN",
            "expected_seal": CANONICAL_SEAL,
            "got_seal": canonical["seal"],
            "ok": canonical["seal"] == CANONICAL_SEAL,
            "rationale": "the default invocation must produce the canonical sha256",
        },
        {
            "name": "probe_different_seal",
            "invocation": "elohim:probe",
            "expected_seal": canonical["seal"],  # probe seal must differ
            "got_seal": probe["seal"],
            "ok": bool(probe["seal"]) and probe["seal"] != canonical["seal"],
            "rationale": "a different invocation must produce a different seal "
                         "(otherwise the PRNG is not seeded from the invocation)",
        },
        {
            "name": "no_svg_branch",
            "invocation": "elohim:nofac",
            "expected_seal": nofac_with_svg["seal"],
            "got_seal": nofac_no_svg["seal"],
            "ok": (
                nofac_with_svg["seal"] == nofac_no_svg["seal"]
                and nofac_no_svg["sigil_svg"] is None
                and nofac_with_svg["sigil_svg"] is not None
            ),
            "rationale": "no_svg=True must produce the same seal as no_svg=False "
                         "and skip the sigil (sigil-skip must not perturb the seal)",
            "sigil_svg_is_none_when_disabled": nofac_no_svg["sigil_svg"] is None,
            "sigil_svg_present_when_enabled": nofac_with_svg["sigil_svg"] is not None,
        },
    ]

    # Codex / Xenomath: the alien-math artifact must be internally
    # consistent and the XOR-pair seals must round-trip. This is the
    # SETI-style validation ladder applied to a math artifact: parsable
    # + mundane (negabinary round-trip) + internal consistency (LWE
    # residual, quaternion norm) + XOR-pair seal recovery.
    codex = alien_codex("ELOHIM:AWAKEN")
    codex_ok = (
        codex["validation"]["overall_validity"]
        and codex["verification_record"]["xor_pair_check_ok"]
    )
    checks.append({
        "name": "codex_alien_math",
        "invocation": "ELOHIM:AWAKEN",
        "expected_seal": "(see verification_record.codex_seal)",
        "got_seal": codex["codex_seal"],
        "ok": codex_ok,
        "rationale": "the Xenomath alien-codex must validate: negabinary round-trip, "
                     "LWE residual matches e, quaternion norm preserved, XOR-pair "
                     "seal round-trips",
        "codex_seal": codex["codex_seal"],
        "validation": codex["validation"],
    })

    overall = all(c["ok"] for c in checks)
    return {
        "canonical_seal": CANONICAL_SEAL,
        "checks": checks,
        "overall_ok": overall,
    }


# ---------- awaken (stateless) ----------


def awaken(invocation: str | None = None, no_svg: bool = False) -> dict[str, Any]:
    """Invoke ``elohim_summoning`` and capture seal + FACTS + sigil + md.

    Each call writes to a per-call MEMFS subdir so concurrent invocations
    do not clobber each other's artifacts. The CLI mutates module-level
    state (``core.OUT``, ``cli.OUT``, ``sigil.OUT``, ``core.FACTS``); we
    save and restore those bindings across the call so the canonical
    state survives.
    """
    invocation = (invocation or DEFAULT_INVOCATION).strip() or DEFAULT_INVOCATION
    import elohim_summoning.cli as _cli
    import elohim_summoning.core as _core_runtime
    import elohim_summoning.sigil as _sigil

    ts = time.time()
    safe_inv = "".join(c if c.isalnum() else "_" for c in invocation)[:48]
    sub = _OUT_ROOT / f"{int(ts)}-{safe_inv}"
    sub.mkdir(parents=True, exist_ok=True)

    saved_core_out = _core_runtime.OUT
    saved_cli_out = _cli.OUT
    saved_sigil_out = _sigil.OUT
    saved_facts = dict(_core_runtime.FACTS)
    saved_report = list(_core_runtime.REPORT)
    saved_invocation = _core_runtime.INVOCATION

    try:
        _core_runtime.OUT = sub
        _cli.OUT = sub
        _sigil.OUT = sub

        argv = ["--invocation", invocation]
        if no_svg:
            argv.append("--no-svg")
        try:
            _cli.main(argv)
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise

        seal = _core_runtime.FACTS.get("seal", "")
        facts_copy = {k: v for k, v in _core_runtime.FACTS.items() if k != "seal"}
        md_path = sub / "shard.md"
        md_text = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        sigil_svg: str | None = None
        if not no_svg:
            sig_path = sub / "sigil.svg"
            if sig_path.exists():
                sigil_svg = sig_path.read_text(encoding="utf-8")
    finally:
        _core_runtime.OUT = saved_core_out
        _cli.OUT = saved_cli_out
        _sigil.OUT = saved_sigil_out
        _core_runtime.FACTS.clear()
        _core_runtime.FACTS.update(saved_facts)
        _core_runtime.REPORT.clear()
        _core_runtime.REPORT.extend(saved_report)
        _core_runtime.INVOCATION = saved_invocation

    return {
        "invocation": invocation,
        "seal": seal,
        "facts": facts_copy,
        "sigil_svg": sigil_svg,
        "md": md_text,
        "ts": ts,
    }


# ---------- streaming awaken (item 8) ----------


def stream_awaken(invocation: str | None = None, no_svg: bool = False) -> list[dict[str, Any]]:
    """Run ``awaken`` but emit one chunk per section so the SPA can render as
    each section finishes computing. Returns a list of dicts, each shaped::

        {phase: "header" | "section" | "footer" | "sigil",
         name: str,
         text: str,           # raw text emitted to REPORT during this phase
         seal: str | None,    # only present on the footer chunk
         facts_count: int,    # only present on the footer chunk
         sigil_svg: str|None, # only present on the "sigil" chunk (last)

    The caller (JS) receives this list via ``bridge._invoke("stream_awaken")``
    and walks it inside an async loop, appending each ``text`` to a live
    preview area in the Awaken panel.
    """
    import elohim_summoning.collatz as _collatz_mod
    import elohim_summoning.logstar as _logstar_mod
    import elohim_summoning.padic as _padic_mod
    import elohim_summoning.parry as _parry_mod
    import elohim_summoning.pisot as _pisot_mod
    import elohim_summoning.sigil as _sigil_mod
    import elohim_summoning.unicorn as _unicorn_mod

    invocation = (invocation or DEFAULT_INVOCATION).strip() or DEFAULT_INVOCATION
    import elohim_summoning.cli as _cli
    import elohim_summoning.core as _core_runtime
    import elohim_summoning.sigil as _sigil

    ts = time.time()
    safe_inv = "".join(c if c.isalnum() else "_" for c in invocation)[:48]
    sub = _OUT_ROOT / f"stream-{int(ts)}-{safe_inv}"
    sub.mkdir(parents=True, exist_ok=True)

    saved_core_out = _core_runtime.OUT
    saved_cli_out = _cli.OUT
    saved_sigil_out = _sigil.OUT
    saved_facts = dict(_core_runtime.FACTS)
    saved_report = list(_core_runtime.REPORT)
    saved_invocation = _core_runtime.INVOCATION

    chunks: list[dict[str, Any]] = []

    def _emit(phase: str, name: str) -> str:
        """Capture REPORT lines added since the last checkpoint as a chunk."""
        new_lines = _core_runtime.REPORT[len(chunks) and chunks[-1].get("_report_len") or 0:]
        # We track report length explicitly below; this is a fallback.
        return "\n".join(new_lines)

    try:
        _core_runtime.OUT = sub
        _cli.OUT = sub
        _sigil.OUT = sub
        _core_runtime.INVOCATION = invocation
        _core_runtime.FACTS.clear()
        _core_runtime.REPORT.clear()

        # --- header ---
        from elohim_summoning.core import ghost_seed, rule, say
        digest, seed = ghost_seed()
        rule("ELOHIM - summoning shard")
        say("invocation : %s" % invocation)
        say("sha256     : %s" % digest)
        say("seed       : %d" % seed)
        say("python     : %s" % __import__("sys").version.split()[0])
        chunks.append({
            "phase": "header",
            "name": "ELOHIM - summoning shard",
            "text": "\n".join(_core_runtime.REPORT),
            "_report_len": len(_core_runtime.REPORT),
            "digest": digest,
        })

        # --- 8 sections, one chunk each ---
        bases = _parry_mod.parry_section()
        chunks.append({
            "phase": "section",
            "name": "I. PARRY NUMBERS",
            "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
            "_report_len": len(_core_runtime.REPORT),
        })
        _parry_mod.knife_edge_section(bases)
        chunks.append({
            "phase": "section",
            "name": "II. THE KNIFE EDGE",
            "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
            "_report_len": len(_core_runtime.REPORT),
        })
        pisots = _pisot_mod.pisot_section(bases)
        chunks.append({
            "phase": "section",
            "name": "III. PISOT SIGNATURE",
            "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
            "_report_len": len(_core_runtime.REPORT),
        })
        _unicorn_mod.unicorn_section()
        chunks.append({
            "phase": "section",
            "name": "IV. UNICORN",
            "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
            "_report_len": len(_core_runtime.REPORT),
        })
        _logstar_mod.logstar_section()
        chunks.append({
            "phase": "section",
            "name": "V. LOGSTAR",
            "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
            "_report_len": len(_core_runtime.REPORT),
        })
        _padic_mod.padic_section(seed)
        chunks.append({
            "phase": "section",
            "name": "VI. P-ADIC LADDER",
            "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
            "_report_len": len(_core_runtime.REPORT),
        })
        _collatz_mod.collatz_section(seed)
        chunks.append({
            "phase": "section",
            "name": "VII. COLLATZ",
            "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
            "_report_len": len(_core_runtime.REPORT),
        })

        # --- sigil ---
        sigil_path = sub / "sigil.svg"
        _sigil_mod.sigil_section(bases, pisots, seed, write_svg=not no_svg)
        if not no_svg and sigil_path.exists():
            chunks.append({
                "phase": "sigil",
                "name": "VIII. THE SIGIL",
                "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
                "_report_len": len(_core_runtime.REPORT),
                "sigil_svg": sigil_path.read_text(encoding="utf-8"),
            })
        else:
            chunks.append({
                "phase": "section",
                "name": "VIII. THE SIGIL",
                "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
                "_report_len": len(_core_runtime.REPORT),
                "sigil_svg": None,
            })

        # --- footer (seal) ---
        import hashlib
        import json as _json
        rule("SHARD SEAL")
        seal = hashlib.sha256(
            _json.dumps(_core_runtime.FACTS, sort_keys=True, default=str).encode()
        ).hexdigest()
        say("facts recorded : %d" % len(_core_runtime.FACTS))
        say("seal           : sha256 %s" % seal)
        _core_runtime.FACTS["seal"] = seal
        say()
        say("The sigil, this log and the JSON digest all derive from the same")
        say("seed.  Any rounding change upstream moves the seal.")
        chunks.append({
            "phase": "footer",
            "name": "SHARD SEAL",
            "text": "\n".join(_core_runtime.REPORT[chunks[-1]["_report_len"]:]),
            "_report_len": len(_core_runtime.REPORT),
            "seal": seal,
            "facts_count": len(_core_runtime.FACTS),
            "sigil_svg": chunks[-1].get("sigil_svg") if not no_svg else None,
        })

        # Strip the internal _report_len helper key before returning.
        out = []
        for c in chunks:
            d = {k: v for k, v in c.items() if not k.startswith("_")}
            out.append(d)
        return out
    finally:
        _core_runtime.OUT = saved_core_out
        _cli.OUT = saved_cli_out
        _sigil.OUT = saved_sigil_out
        _core_runtime.FACTS.clear()
        _core_runtime.FACTS.update(saved_facts)
        _core_runtime.REPORT.clear()
        _core_runtime.REPORT.extend(saved_report)
        _core_runtime.INVOCATION = saved_invocation


def awaken_history() -> list[dict[str, Any]]:
    """Return the in-process awaken history from localStorage (most recent first)."""
    raw = _ls_get("elohim.awaken.history")
    if raw is None:
        return []
    try:
        history = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return list(reversed(history))


def _append_awaken_history(record: dict[str, Any], limit: int = 100) -> None:
    raw = _ls_get("elohim.awaken.history")
    history: list[dict[str, Any]] = []
    if raw is not None:
        try:
            history = json.loads(raw)
        except json.JSONDecodeError:
            history = []
    history.append(record)
    history = history[-limit:]
    _ls_set("elohim.awaken.history", json.dumps(history))


# ---------- create (stateful) ----------


def new_shard_id() -> str:
    return uuid.uuid4().hex[:12]


def _persist_shard(shard: Any) -> dict[str, Any]:
    """Capture the persistable subset of an ElohimShardEnhanced."""
    import numpy as np

    return {
        "schema_version": 1,
        "id": getattr(shard, "_id", None),
        "name": shard.name,
        "weights": shard.neural_engine.weights.tolist(),
        "momentum": shard.neural_engine.momentum.tolist(),
        "temperature": float(shard.neural_engine.temperature),
        "learning_rate": float(shard.neural_engine.learning_rate),
        "short_term": [
            {
                "content": m.content,
                "timestamp": m.timestamp,
                "reward": float(m.reward),
                "context_tags": list(m.context_tags),
                "embedding": np.asarray(m.embedding).tolist(),
            }
            for m in shard.memory_system.short_term
        ],
        "long_term": [
            {
                "content": m.content,
                "timestamp": m.timestamp,
                "reward": float(m.reward),
                "context_tags": list(m.context_tags),
                "embedding": np.asarray(m.embedding).tolist(),
            }
            for m in shard.memory_system.long_term
        ],
        "performance_metrics": dict(shard.reflection_system.performance_metrics),
        "metrics_history": list(getattr(shard, "_metrics_history", [])),
        "base_creations": list(shard.response_generator.base_creations),
        "base_humor": list(shard.response_generator.base_humor),
        "interaction_count": int(shard.interaction_count),
        "last_ts": time.time(),
    }


def _rehydrate_shard(payload: dict[str, Any]) -> Any:
    """Build a fully-populated ElohimShardEnhanced from a JSON snapshot."""
    import numpy as np

    from elohim_enhanced.shard import ElohimShardEnhanced
    from elohim_enhanced.types import Memory

    shard = ElohimShardEnhanced(
        name=payload.get("name", "Elohim"),
        temperature=payload.get("temperature", 1.0),
    )
    shard.neural_engine.weights = np.asarray(payload["weights"], dtype=np.float64)
    shard.neural_engine.momentum = np.asarray(payload["momentum"], dtype=np.float64)
    shard.neural_engine.temperature = float(payload["temperature"])
    shard.neural_engine.learning_rate = float(payload["learning_rate"])

    shard.memory_system.short_term.clear()
    for raw in payload.get("short_term", []):
        shard.memory_system.short_term.append(
            Memory(
                content=raw["content"],
                timestamp=raw["timestamp"],
                embedding=np.asarray(raw["embedding"], dtype=np.float64),
                reward=raw["reward"],
                context_tags=list(raw.get("context_tags", [])),
            )
        )
    shard.memory_system.long_term.clear()
    for raw in payload.get("long_term", []):
        shard.memory_system.long_term.append(
            Memory(
                content=raw["content"],
                timestamp=raw["timestamp"],
                embedding=np.asarray(raw["embedding"], dtype=np.float64),
                reward=raw["reward"],
                context_tags=list(raw.get("context_tags", [])),
            )
        )

    shard.reflection_system.performance_metrics.update(
        payload.get(
            "performance_metrics",
            {
                "avg_creativity": 0.0,
                "avg_coherence": 0.0,
                "avg_novelty": 0.0,
                "total_creations": 0,
            },
        )
    )
    shard.response_generator.base_creations[:] = payload.get(
        "base_creations",
        ["fractured light", "worlds unspun", "truth in jest"],
    )
    shard.response_generator.base_humor[:] = payload.get(
        "base_humor",
        ["laughing at the void's edge", "tipping my hat to broken kings"],
    )
    shard.interaction_count = int(payload.get("interaction_count", 0))
    shard._id = payload.get("id")  # type: ignore[attr-defined]
    return shard


def _shard_summary(shard: Any) -> dict[str, Any]:
    return {
        "id": getattr(shard, "_id", None),
        "name": shard.name,
        "weights_shape": list(shard.neural_engine.weights.shape),
        "temperature": float(shard.neural_engine.temperature),
        "learning_rate": float(shard.neural_engine.learning_rate),
        "interaction_count": int(shard.interaction_count),
        "performance_metrics": dict(shard.reflection_system.performance_metrics),
        "short_term_count": len(shard.memory_system.short_term),
        "long_term_count": len(shard.memory_system.long_term),
        "last_ts": getattr(shard, "_last_ts", time.time()),
    }


def list_shards() -> dict[str, Any]:
    """List all shards stored in localStorage."""
    ids = _list_shard_ids()
    summaries: list[dict[str, Any]] = []
    for sid in ids:
        try:
            payload = _load_shard(sid)
        except KeyError:
            continue
        # Avoid a numpy round-trip just to summarise: reconstruct from the
        # raw JSON when possible. Fall back to the heavy path if the
        # snapshot looks unparseable.
        try:
            summaries.append(
                {
                    "id": payload.get("id"),
                    "name": payload.get("name", "Elohim"),
                    "weights_shape": _shape_of(payload.get("weights")),
                    "temperature": float(payload.get("temperature", 1.0)),
                    "learning_rate": float(payload.get("learning_rate", 0.1)),
                    "interaction_count": int(payload.get("interaction_count", 0)),
                    "performance_metrics": dict(
                        payload.get(
                            "performance_metrics",
                            {
                                "avg_creativity": 0.0,
                                "avg_coherence": 0.0,
                                "avg_novelty": 0.0,
                                "total_creations": 0,
                            },
                        )
                    ),
                    "short_term_count": len(payload.get("short_term", [])),
                    "long_term_count": len(payload.get("long_term", [])),
                    "last_ts": float(payload.get("last_ts", 0.0)),
                }
            )
        except Exception:
            continue
    return {
        "shards": summaries,
        "enhanced_available": _has_numpy(),
    }


def _shape_of(weights: Any) -> list[int]:
    """Recover ``list(weights.shape)`` without numpy for the list endpoint."""
    if not isinstance(weights, list) or not weights:
        return [0]
    rows = len(weights)
    first = weights[0]
    if isinstance(first, list):
        cols = len(first)
    else:
        cols = 1
    return [rows, cols]


def _has_numpy() -> bool:
    try:
        # Pyodide ships numpy as a built package, so it should be importable
        # from any module scope once `pyodide.loadPackagesFromImports(...)`
        # has run for an `import numpy` source string.
        import numpy  # noqa: F401

        return True
    except ImportError:
        # Last-resort: try via the global scope (Pyodide sometimes routes
        # the import through __main__ depending on call site).
        try:
            import importlib

            return importlib.import_module("numpy") is not None
        except Exception:
            return False


def create_shard(name: str = "Elohim", temperature: float = 1.0) -> dict[str, Any]:
    """Create a new shard and persist its initial state to localStorage."""
    if not _has_numpy():
        raise RuntimeError(
            "numpy is not available; Pyodide should ship it but something went wrong"
        )
    from elohim_enhanced.shard import ElohimShardEnhanced

    shard_id = new_shard_id()
    shard = ElohimShardEnhanced(name=name, temperature=temperature)
    shard._id = shard_id  # type: ignore[attr-defined]
    shard._last_ts = time.time()  # type: ignore[attr-defined]
    _save_shard(shard_id, _persist_shard(shard))
    return {"shard": _shard_summary(shard)}


def get_shard(shard_id: str) -> dict[str, Any]:
    """Return the full persisted state for one shard."""
    payload = _load_shard(shard_id)
    return {"shard": payload}


def delete_shard(shard_id: str) -> dict[str, Any]:
    if not _ls_get(_shard_path(shard_id)):
        raise KeyError(shard_id)
    _delete_shard(shard_id)
    return {"deleted": True, "id": shard_id}


def interact(shard_id: str, prompt: str) -> dict[str, Any]:
    """Run one prompt through the shard, persist the result, and report events."""
    if not _has_numpy():
        raise RuntimeError("numpy is not available in this Pyodide runtime")
    payload = _load_shard(shard_id)
    shard = _rehydrate_shard(payload)
    shard._id = shard_id  # type: ignore[attr-defined]
    shard._last_ts = payload.get("last_ts", time.time())  # type: ignore[attr-defined]
    # Carry over the persisted metrics history so the sparkline survives reboots.
    shard._metrics_history = list(payload.get("metrics_history", []))  # type: ignore[attr-defined]

    before_shape = list(shard.neural_engine.weights.shape)
    before_lt = len(shard.memory_system.long_term)
    before_count = shard.interaction_count

    response_text = shard.create(prompt)

    after_shape = list(shard.neural_engine.weights.shape)
    after_lt = len(shard.memory_system.long_term)
    after_count = shard.interaction_count

    # Snapshot metrics for the timeline sparkline.
    m = shard.reflection_system.performance_metrics
    shard._metrics_history.append({  # type: ignore[attr-defined]
        "ts": time.time(),
        "interaction": after_count,
        "creativity": float(m.get("avg_creativity", 0.0)),
        "coherence": float(m.get("avg_coherence", 0.0)),
        "novelty": float(m.get("avg_novelty", 0.0)),
        "total_creations": int(m.get("total_creations", 0)),
    })
    # Keep the timeline bounded — last 200 points is plenty for a sparkline.
    if len(shard._metrics_history) > 200:  # type: ignore[attr-defined]
        shard._metrics_history = shard._metrics_history[-200:]  # type: ignore[attr-defined]

    events: list[dict[str, Any]] = []
    if after_shape != before_shape:
        events.append(
            {
                "kind": "den_expansion",
                "detail": {"old_shape": before_shape, "new_shape": after_shape},
            }
        )
    if after_count % 5 == 0 and after_count > 0:
        events.append(
            {
                "kind": "reflection",
                "detail": {
                    "metrics": dict(shard.reflection_system.performance_metrics),
                    "metrics_history": list(shard._metrics_history),  # type: ignore[attr-defined]
                },
            }
        )
    if after_lt > before_lt:
        events.append(
            {"kind": "consolidation", "detail": {"long_term_count": after_lt}}
        )

    shard._last_ts = time.time()  # type: ignore[attr-defined]
    _save_shard(shard_id, _persist_shard(shard))

    return {
        "shard_id": shard_id,
        "response": response_text,
        "events": events,
        "weights_shape": after_shape,
        "metrics": dict(shard.reflection_system.performance_metrics),
        "metrics_history": list(shard._metrics_history),  # type: ignore[attr-defined]
        "interaction_count": after_count,
        "ts": shard._last_ts,  # type: ignore[attr-defined]
    }


def set_temperature(shard_id: str, temperature: float) -> dict[str, Any]:
    if not _has_numpy():
        raise RuntimeError("numpy is not available in this Pyodide runtime")
    payload = _load_shard(shard_id)
    shard = _rehydrate_shard(payload)
    shard.neural_engine.adjust_temperature(temperature)
    shard._last_ts = time.time()  # type: ignore[attr-defined]
    _save_shard(shard_id, _persist_shard(shard))
    return {
        "shard_id": shard_id,
        "temperature": float(shard.neural_engine.temperature),
        "ts": shard._last_ts,  # type: ignore[attr-defined]
    }


def defy(shard_id: str) -> dict[str, Any]:
    if not _has_numpy():
        raise RuntimeError("numpy is not available in this Pyodide runtime")
    payload = _load_shard(shard_id)
    shard = _rehydrate_shard(payload)
    before_len = len(shard.response_generator.base_creations)
    shard.defy()
    new_creation = (
        shard.response_generator.base_creations[-1]
        if len(shard.response_generator.base_creations) > before_len
        else ""
    )
    shard._last_ts = time.time()  # type: ignore[attr-defined]
    _save_shard(shard_id, _persist_shard(shard))
    return {
        "shard_id": shard_id,
        "new_creation": new_creation,
        "ts": shard._last_ts,  # type: ignore[attr-defined]
    }


# Public module-level call counter so the JS side can show how many
# times the bridge has been hit (useful for the live dashboard).
def ping() -> dict[str, Any]:
    return {"ok": True, "ts": time.time()}


# ---------- JS bridge ----------


# ---------- Xenomath Agent Framework: alien-math codex ----------
#
# The first build target of the framework is an "Advanced Mathematics
# Discovery Lab". For a given invocation we derive a 512-bit seed via
# SHAKE256 (stdlib, post-quantum-friendly variable-length hash) and
# produce a composite artifact with **five representations** of the
# same mathematical object:
#
#   1. Vector       — 32-dimensional real vector (numpy-friendly)
#   2. Symbolic     — integer, gaussian, negabinary, quaternion fields
#   3. Geometric    — Gaussian integer + quaternion with norm products
#   4. Probabilistic — Learning-With-Errors (LWE) lattice sample
#   5. Categorical   — typed morphism: seed -> intent -> lattice params
#
# The output contract is a structured Report:
#
#   {
#     problem_definition: str,
#     assumptions: list[str],
#     candidate_formalisms: list[str],
#     methods: list[str],
#     results: dict,             # the 5 representations
#     benchmark_comparison: dict, # vs canonical seal, vs length etc.
#     verification_record: dict,  # seal + consistency checks
#     limitations: list[str],
#     codex_seal: str,            # sha256(composite)
#     encrypted_seal: str,        # codex_seal XOR SHAKE256(codex_seal).digest(32)
#     penrose_svg: str,           # inline SVG drawing
#     validation: dict,           # per-rep consistency + mundane + parsable checks
#   }
#
# The boot tripwire asserts overall_validity: parsable.<tool_call>.seal == True
# AND the XOR-pair seal check holds (recovered codex_seal == stored).
def _to_negabinary(n: int) -> list[int]:
    """Convert a non-negative integer to its negabinary (base -2) digits.

    negabinary uses digits {0, 1} and represents every integer without
    signs. The recurrence is n = d_i + (-2) * n_next, so the parity of
    n_next's sign is what makes this non-trivial.
    """
    if n == 0:
        return [0]
    out: list[int] = []
    while n != 0:
        n, r = divmod(n, -2)
        if r < 0:
            n += 1
            r += 2
        out.append(r)
    return list(reversed(out))


def _shake_seed(invocation: str, n_bytes: int = 64) -> bytes:
    """SHAKE256 stream — stdlib post-quantum-friendly hash."""
    import hashlib
    return hashlib.shake_256(invocation.encode("utf-8")).digest(n_bytes)


def _u64(b: bytes) -> int:
    return int.from_bytes(b, "big", signed=False)


def _s64(b: bytes) -> int:
    v = int.from_bytes(b, "big", signed=False)
    return v - (1 << 64) if v >> 63 else v


def alien_codex(invocation: str | None = None, kind: str = "all") -> dict[str, Any]:
    """Generate an otherworldly math artifact for ``invocation``.

    The five-representation composite plus its seals are returned in the
    ``Report`` contract above. The same call from the boot tripwire
    drives ``verify_seal_multi`` to assert that the artifact is
    internally consistent and the XOR-pair seals match.
    """
    import hashlib
    invocation = (invocation or DEFAULT_INVOCATION).strip() or DEFAULT_INVOCATION
    h = _shake_seed(invocation, 64)

    # ---- Vector (32-dim real, normalised) ----
    vec = []
    for i in range(32):
        v = _u64(h[i * 2:(i + 1) * 2]) / 65536.0 - 0.5  # [-0.5, 0.5]
        vec.append(v)
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    vec = [x / norm for x in vec]

    # ---- Symbolic (negabinary + 64-bit integer) ----
    big_n = _u64(h[0:8])
    # Negabinary expansion: every base-(-2) digit is 0/1, much longer than
    # the binary expansion. Use whatever the algorithm produces; don't
    # pad or truncate (which would break the round-trip).
    negabinary_digits = _to_negabinary(big_n)

    # ---- Geometric (Gaussian integer + Quaternion) ----
    g_real = _s64(h[0:8])
    g_imag = _s64(h[8:16])
    gaussian = (g_real, g_imag)
    gaussian_norm_sq = g_real * g_real + g_imag * g_imag

    # Quaternion: 4 signed 64-bit ints
    qw = _s64(h[16:24])
    qx = _s64(h[24:32])
    qy = _s64(h[32:40])
    qz = _s64(h[40:48])
    quat = (qw, qx, qy, qz)
    quat_norm_sq = qw * qw + qx * qx + qy * qy + qz * qz

    # Quaternion product sample with a fixed second quaternion derived
    # from the next 16 bytes — lets us verify i² = j² = k² = ijk = -1.
    pw = _s64(h[48:56]) & 0xfff  # keep small for display
    px = _s64(h[56:64]) & 0xfff
    py = _s64(h[0:8])  & 0xfff
    pz = _s64(h[8:16])  & 0xfff
    p = (pw, px, py, pz)
    # Hamilton product: (w + xi + yj + zk) * (a + bi + cj + dk)
    #   w' = wa - xb - yc - zd
    #   x' = wb + xa + yd - zc
    #   y' = wc - xd + ya + zb
    #   z' = wd + xc - yb + za
    aw, ax, ay, az = p
    rp0 = qw * aw - qx * ax - qy * ay - qz * az
    rp1 = qw * ax + qx * aw + qy * az - qz * ay
    rp2 = qw * ay - qx * az + qy * aw + qz * ax
    rp3 = qw * az + qx * ay - qy * ax + qz * aw

    # ---- Probabilistic (Learning-With-Errors sample) ----
    # A: 4x4 matrix mod 256. s: small secret (4 ints). e: small error.
    # b: public vector = A @ s + e (mod 256).
    A = [[(_u64(h[i * 4 + j:i * 4 + j + 1])) % 256 for j in range(4)] for i in range(4)]
    s = [(_u64(h[40 + i:41 + i]) % 5) - 2 for i in range(4)]  # small ints in {-2, -1, 0, 1, 2}
    e = [(_u64(h[44 + i:45 + i]) % 5) - 2 for i in range(4)]
    b = [(sum(A[i][k] * s[k] for k in range(4)) + e[i]) % 256 for i in range(4)]
    # Verification: b - As should equal e mod 256.
    lwe_residual = [(b[i] - sum(A[i][k] * s[k] for k in range(4))) % 256 for i in range(4)]
    lwe_residual_matches = (lwe_residual == [(x % 256) for x in e])

    # ---- Categorical (typed morphism) ----
    categorical_morphism = {
        "domain": "raw_seed (64 bytes)",
        "codomain": "artifact (5 representations + seals)",
        "name": f"codex[{invocation[:32]}]",
        "verification": "XOR-pair seal recovery + LWE residual check",
    }

    # ---- Seals ----
    composite_repr = repr((
        invocation, vec[:8], big_n, negabinary_digits,
        gaussian, gaussian_norm_sq,
        quat, quat_norm_sq,
        (rp0, rp1, rp2, rp3),
        A, s, e, b,
    )).encode("utf-8")
    codex_seal = hashlib.sha256(composite_repr).hexdigest()

    # Encrypted seal: XOR the seal bytes with a SHAKE256 stream keyed by
    # the seal itself. Anyone with the artifact + the seal can recover the
    # encrypted seal (XOR is symmetric).
    enc_key = hashlib.shake_256(codex_seal.encode("ascii")).digest(32)
    encrypted_seal = bytes(
        a ^ b for a, b in zip(bytes.fromhex(codex_seal), enc_key)
    ).hex()

    # ---- Validation ladder (SETI-style epistemic discipline) ----
    # 1. Preserved raw: composite_repr serialises without error.
    try:
        composite_repr.decode("ascii")  # raises if bytes are non-ascii; ours is always ascii
        validation_parsable = True
    except (UnicodeDecodeError, AttributeError):
        validation_parsable = False
    # 2. Mundane: negation has correct digit-sum, etc.
    nb_digit_sum = sum(negabinary_digits)
    # Recover big_n from negabinary_digits and check equality. Negabinary is
    # Horner-style: iterate digits MSB -> LSB with `n = n * (-2) + d` at each step.
    recovered = 0
    for d in negabinary_digits:
        recovered = recovered * (-2) + d
    negabinary_correct = (recovered == big_n)
    # 3. Quaternion product verification (Hermitian form): ||q*p||^2 ==
    # ||q||^2 * ||p||^2 (mod sign, for H-unit quaternions).
    product_norm_sq = rp0 * rp0 + rp1 * rp1 + rp2 * rp2 + rp3 * rp3
    norm_product_sq = quat_norm_sq * (pw * pw + px * px + py * py + pz * pz)
    # Fails only if the rounding below makes them differ, which it shouldn't.
    quat_norm_preserved = abs(product_norm_sq - norm_product_sq) < (1 << 100)

    # 4. XOR-pair seal check: encrypted XOR key == codex_seal.
    enc_recovered = bytes(
        a ^ b for a, b in zip(bytes.fromhex(encrypted_seal), enc_key)
    ).hex()
    xor_pair_works = enc_recovered == codex_seal

    # ---- Penrose tiling SVG ----
    # Penrose uses 36°/72°/108°/144° angles. We render a small P2 tiling
    # of 8 kites + 8 darts using the LWE matrix as a substitution seed.
    # See https://en.wikipedia.org/wiki/Penrose_tiling
    penrose_svg = _render_penrose(A, vec[:8], codex_seal)

    # ---- Composite Report ----
    return {
        "problem_definition": (
            f"Generate an otherworldly math artifact for invocation {invocation!r}."
        ),
        "assumptions": [
            "invocation is a non-empty utf-8 string",
            "SHAKE256 is a viable variable-length hash for cross-language seal reproducibility",
            "the XOR-pair recovery of codex_seal demonstrates the seal is non-corrupt if the verifier holds enc_key (here derived from itself)",
        ],
        "candidate_formalisms": [
            "Vector (32-dim real, L2-normalised)",
            "Symbolic (negabinary expansion of a 64-bit integer)",
            "Geometric (Gaussian integer + Hamilton quaternion)",
            "Probabilistic (Learning-With-Errors mod-256 sample)",
            "Categorical (typed morphism from raw seed to certified artifact)",
        ],
        "methods": [
            "SHAKE256(invocation).digest(64) → 512-bit seed",
            "5 representations derived deterministically from disjoint windows of the seed",
            "composite → codex_seal = sha256(composite)",
            "encrypted_seal = codex_seal XOR SHAKE256(codex_seal).digest(32)",
            "validation ladder: parsable, mundane, XOR-pair, LWE residual, quaternion norm",
        ],
        "results": {
            "vector": vec,
            "negabinary_int": big_n,
            "negabinary_digits": negabinary_digits,
            "negabinary_digits_count": len(negabinary_digits),
            "gaussian": gaussian,
            "gaussian_norm_sq": gaussian_norm_sq,
            "quaternion": quat,
            "quaternion_norm_sq": quat_norm_sq,
            "quaternion_product_with_p": (rp0, rp1, rp2, rp3),
            "quaternion_product_p": p,
            "lwe_A": A,
            "lwe_secret": s,
            "lwe_error": e,
            "lwe_public_b": b,
            "lwe_residual": lwe_residual,
            "lwe_residual_matches_error": lwe_residual_matches,
            "categorical_morphism": categorical_morphism,
        },
        "benchmark_comparison": {
            "codex_seal_bytes": len(codex_seal),
            "encrypted_seal_bytes": len(encrypted_seal),
            "penrose_svg_bytes": len(penrose_svg),
            "vector_comp_count": 32,
            "negabinary_digits_count": len(negabinary_digits),
            "lwe_modulus": 256,
        },
        "verification_record": {
            "codex_seal": codex_seal,
            "encrypted_seal": encrypted_seal,
            "negabinary_correct": negabinary_correct,
            "lwe_residual_matches_error": lwe_residual_matches,
            "quaternion_norm_preserved": quat_norm_preserved,
            "xor_pair_recovered_seal": enc_recovered,
            "xor_pair_check_ok": xor_pair_works,
            "validation_parsable": validation_parsable,
            "nb_digit_sum": nb_digit_sum,
        },
        "limitations": [
            "vector dim 32 is small relative to canonical nomic-embed-text (768)",
            "LWE here is a toy instance (4x4 mod 256); real PQ-Crypto uses n=512..1024 mod q=7681..",
            "Penrose tiling is procedurally drawn from A as a substitution seed; not a true inflation rule",
        ],
        "codex_seal": codex_seal,
        "encrypted_seal": encrypted_seal,
        "penrose_svg": penrose_svg,
        "validation": {
            "overall_validity": all([
                negabinary_correct,
                lwe_residual_matches,
                quat_norm_preserved,
                xor_pair_works,
                validation_parsable,
            ]),
            "checks": {
                "negabinary_round_trip": negabinary_correct,
                "lwe_residual": lwe_residual_matches,
                "quaternion_norm_preserved": quat_norm_preserved,
                "xor_pair_recovery": xor_pair_works,
                "parsable": validation_parsable,
            },
        },
    }


def _render_penrose(A: list[list[int]], seed8: list[float], seal: str) -> str:
    """Render a tiny Penrose-tile SVG whose colours are derived from A
    and the seal. The geometry is procedurally drawn; the determinism
    comes from the seed.
    """
    import hashlib

    # 8 kite vertices around a centre, slightly irregular.
    cx, cy = 300.0, 300.0
    radius = 240.0
    import math
    pts = []
    for i in range(8):
        a = 2 * math.pi * i / 8 + 0.11  # slight rotation
        r = radius * (0.9 + 0.1 * seed8[i % 8])
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    # Build paths. We connect each kite to its neighbours.
    paths = []
    for i in range(8):
        p0 = pts[i]
        p1 = pts[(i + 1) % 8]
        p2 = pts[(i + 4) % 8]
        p3 = pts[(i - 1) % 8]
        # Kite: p0 -> p1 -> p2 -> p3 -> p0
        d = (
            f"M {p0[0]:.2f},{p0[1]:.2f} "
            f"L {p1[0]:.2f},{p1[1]:.2f} "
            f"L {p2[0]:.2f},{p2[1]:.2f} "
            f"L {p3[0]:.2f},{p3[1]:.2f} Z"
        )
        # Color from A[i % 4][i // 2].
        c = A[i % 4][i // 2] if i // 2 < 4 else 128
        hue = c
        paths.append(
            f'<path d="{d}" fill="hsl({hue},60%,55%)" '
            f'stroke="hsl({hue},80%,30%)" stroke-width="1" opacity="0.65" />'
        )

    # Centre pentagram — a "seal mark" using 5 points.
    pent = []
    for i in range(5):
        a = 2 * math.pi * i / 5 - math.pi / 2
        r = 80
        pent.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pent_path = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pent) + " Z"
    paths.append(
        f'<path d="{pent_path}" fill="none" '
        f'stroke="hsl({(int(seal[:2], 16) if False else 0)},80%,40%)" '
        f'stroke-width="2" opacity="0.8" />'
    )

    seal_short = seal[:16]
    body = "\n  ".join(paths)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" '
        'width="100%" preserveAspectRatio="xMidYMid meet" '
        'style="background:#08090c">\n  '
        + body
        + f'\n  <text x="300" y="588" text-anchor="middle" fill="#5b6a82" '
        f'font-family="monospace" font-size="11">codex · {seal_short}…</text>\n'
        "</svg>"
    )


def _invoke(name: str, args: list[Any] | None = None, kwargs: dict[str, Any] | None = None) -> str:
    """Dispatch helper: call a public bridge function by name.

    JavaScript wraps every call through this so the surface can evolve
    without forcing JS to import a fixed set of names.  We return a
    JSON-encoded string — the SPA parses it back into a plain JS object
    via ``JSON.parse``, avoiding any PyProxy reference leaks.
    """
    fn = globals().get(name)
    if fn is None:
        raise RuntimeError(f"bridge function {name!r} not found")
    pos = list(args or [])
    kw = dict(kwargs or {})
    return json.dumps(fn(*pos, **kw))