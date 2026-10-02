"""Structured dataclasses shared across the enhanced components.

Verbatim from the upstream `elohim_enhanced.py`. No math comments to preserve
here — these are pure data containers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ._deps import get_numpy

np = get_numpy()


@dataclass
class Memory:
    """Structured memory with semantic information."""
    content: str
    timestamp: float
    embedding: "np.ndarray"
    reward: float = 0.0
    context_tags: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"Memory(content='{self.content[:30]}...', reward={self.reward:.2f})"


@dataclass
class CreationRecord:
    """Track creative outputs."""
    output: str
    timestamp: float
    creativity_score: float
    coherence_score: float
    novelty_score: float