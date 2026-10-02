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

    import elohim_summoning
    from elohim_summoning import __version__ as sum_v

    try:
        import elohim_enhanced
        from elohim_enhanced import __version__ as enh_v
        enhanced_version = enh_v
        enhanced_available = True
    except ImportError:
        enhanced_version = None
        enhanced_available = False

    return {
        "name": "elohim-summoning",
        "version": sum_v,
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
        "base_creations": list(shard.response_generator.base_creations),
        "base_humor": list(shard.response_generator.base_humor),
        "interaction_count": int(shard.interaction_count),
        "last_ts": time.time(),
    }


def _rehydrate_shard(payload: dict[str, Any]) -> Any:
    """Build a fully-populated ElohimShardEnhanced from a JSON snapshot."""
    import numpy as np

    from elohim_enhanced import ElohimShardEnhanced
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
    from elohim_enhanced import ElohimShardEnhanced

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

    before_shape = list(shard.neural_engine.weights.shape)
    before_lt = len(shard.memory_system.long_term)
    before_count = shard.interaction_count

    response_text = shard.create(prompt)

    after_shape = list(shard.neural_engine.weights.shape)
    after_lt = len(shard.memory_system.long_term)
    after_count = shard.interaction_count

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
                "detail": {"metrics": dict(shard.reflection_system.performance_metrics)},
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