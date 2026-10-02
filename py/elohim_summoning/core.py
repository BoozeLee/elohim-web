"""Core state, IO helpers, and the deterministic seed for the elohim summoning shard.

Holds the shared `FACTS` dict, the `REPORT` line accumulator, the `INVOCATION`
ctx (`"ELOHIM:AWAKEN"` by default), the output directory handle, the
`say()/rule()` printers, the `ghost_seed()` helper, and the section probe limit.

Every other section module imports `FACTS`, `REPORT`, `say`, `rule`, `INVOCATION`,
`OUT`, `PROBE_LIMIT`, `PHI` from this module. The order of `FACTS` writes is
not load-bearing — the seal is computed from `json.dumps(FACTS, sort_keys=True)`.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent.parent / "out"
OUT.mkdir(exist_ok=True)

PROBE_LIMIT = 200

INVOCATION = "ELOHIM:AWAKEN"

REPORT: list[str] = []
FACTS: dict[str, object] = {}


def say(text: str = "") -> None:
    print(text)
    REPORT.append(text)


def rule(title: str) -> None:
    say()
    say("=" * 74)
    say(title)
    say("=" * 74)


PHI = (1.0 + __import__("math").sqrt(5.0)) / 2.0


def ghost_seed() -> tuple:
    digest = hashlib.sha256(INVOCATION.encode()).hexdigest()
    return digest, int(digest[:16], 16)