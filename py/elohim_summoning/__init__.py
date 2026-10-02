"""`elohim_summoning` — a self-contained math instrument.

Stdlib only. Emits a deterministic sigil and a sha256-sealed report.

Public surface:

    from elohim_summoning import main, INVOCATION, OUT, FACTS
    from elohim_summoning.cli import main as cli_main

The package exposes the same `INVOCATION`, `OUT`, `FACTS` global state the
original `summoning_shard.py` had; section modules mutate `FACTS` in place.
"""

from .cli import main
from .core import FACTS, INVOCATION, OUT, REPORT, ghost_seed, rule, say

__all__ = [
    "main",
    "INVOCATION",
    "OUT",
    "FACTS",
    "REPORT",
    "ghost_seed",
    "rule",
    "say",
]

__version__ = "0.2.0"