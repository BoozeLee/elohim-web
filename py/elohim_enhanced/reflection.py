"""ReflectionSystem — running performance tracking and auto-adjustment.

Verbatim from the upstream `elohim_enhanced.py`. Math-comments preserved.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List

from .types import CreationRecord

logger = logging.getLogger("ElohimShard")


class ReflectionSystem:
    """Self-evaluation and quality assessment."""

    def __init__(self) -> None:
        self.creation_history: List[CreationRecord] = []
        self.performance_metrics: Dict[str, float] = {
            "avg_creativity": 0.0,
            "avg_coherence": 0.0,
            "avg_novelty": 0.0,
            "total_creations": 0,
        }

    def evaluate_creation(
        self,
        output: str,
        creativity: float,
        coherence: float,
        novelty: float,
    ) -> float:
        """Evaluate creation and return reward score."""
        record = CreationRecord(
            output=output,
            timestamp=time.time(),
            creativity_score=creativity,
            coherence_score=coherence,
            novelty_score=novelty,
        )
        self.creation_history.append(record)
        reward = creativity * 0.3 + coherence * 0.4 + novelty * 0.3
        self._update_metrics(creativity, coherence, novelty)
        return reward

    def _update_metrics(self, creativity: float, coherence: float, novelty: float) -> None:
        """Update running performance metrics."""
        n = self.performance_metrics["total_creations"]
        self.performance_metrics["avg_creativity"] = (
            self.performance_metrics["avg_creativity"] * n + creativity
        ) / (n + 1)
        self.performance_metrics["avg_coherence"] = (
            self.performance_metrics["avg_coherence"] * n + coherence
        ) / (n + 1)
        self.performance_metrics["avg_novelty"] = (
            self.performance_metrics["avg_novelty"] * n + novelty
        ) / (n + 1)
        self.performance_metrics["total_creations"] = n + 1

    def get_performance_summary(self) -> str:
        """Get summary of performance metrics."""
        m = self.performance_metrics
        return (
            f"Performance | Creativity: {m['avg_creativity']:.3f} | "
            f"Coherence: {m['avg_coherence']:.3f} | "
            f"Novelty: {m['avg_novelty']:.3f} | "
            f"Creations: {m['total_creations']}"
        )

    def should_adjust_parameters(self) -> Dict[str, float]:
        """Determine if parameter adjustments are needed."""
        adjustments: Dict[str, float] = {}
        if self.performance_metrics["avg_coherence"] < 0.3:
            adjustments["temperature"] = -0.1
        if self.performance_metrics["avg_novelty"] < 0.3:
            adjustments["temperature"] = 0.1
        if self.performance_metrics["avg_creativity"] < 0.4:
            adjustments["learning_rate"] = 0.05
        return adjustments