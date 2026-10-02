"""`elohim_enhanced` — the creative, learning, creative shard with semantic
memory, reward-based neural evolution, temperature-controlled responses, and
self-reflection.

Companion to `elohim_summoning` in this same repo. Where `elohim_summoning`
is a stdlib-only, deterministic math instrument with a sha256 seal,
`elohim_enhanced` is a non-deterministic creative agent that depends on
`numpy` (install with `pip install "elohim-summoning[enhanced]"`).

Public surface:

    from elohim_enhanced import (
        SemanticMemorySystem,    # short-term + long-term memory w/ cosine retrieval
        NeuralEvolutionEngine,   # reward-based weight updates, DEN-style expansion
        CreativeResponseGenerator, # templated outputs w/ novelty + coherence scoring
        ReflectionSystem,        # running metrics, auto-adjusts temperature
        ElohimShardEnhanced,     # orchestrator wiring the four
    )
    from elohim_enhanced.cli import main as cli_main

The interactive REPL is also exposed as the `elohim-create` console script.
"""

from .creative import CreativeResponseGenerator
from .engine import NeuralEvolutionEngine
from .memory import SemanticMemorySystem
from .reflection import ReflectionSystem
from .shard import ElohimShardEnhanced
from .types import CreationRecord, Memory

__all__ = [
    "CreativeResponseGenerator",
    "ElohimShardEnhanced",
    "Memory",
    "CreationRecord",
    "NeuralEvolutionEngine",
    "ReflectionSystem",
    "SemanticMemorySystem",
]

__version__ = "0.2.0"