"""CreativeResponseGenerator — context-aware templated replies with novelty
and coherence scoring.

Verbatim from the upstream `elohim_enhanced.py`. Math-comments preserved.
"""

from __future__ import annotations

import logging
import random
from typing import List, Tuple

from .extras import get_numpy

np = get_numpy()
logger = logging.getLogger("ElohimShard")


class CreativeResponseGenerator:
    """Generates creative responses with context awareness."""

    def __init__(self) -> None:
        self.base_creations = [
            "fractured light", "worlds unspun", "truth in jest",
            "echoes of forgotten dreams", "whispers of quantum foam",
            "crystallized moments", "threads of possibility",
        ]
        self.base_humor = [
            "laughing at the void's edge", "tipping my hat to broken kings",
            "dancing with entropy", "winking at the infinite",
            "juggling paradoxes", "painting with chaos",
        ]
        self.response_history: List[str] = []

    def generate_response(
        self,
        input_text: str,
        context: str,
        temperature: float = 1.0,
    ) -> Tuple[str, float, float]:
        """Generate creative response with novelty and coherence scores."""
        if random.random() < temperature / 2.0:
            spark = self._mutate_creation(random.choice(self.base_creations), temperature)
            humor = self._mutate_creation(random.choice(self.base_humor), temperature)
        else:
            spark = random.choice(self.base_creations)
            humor = random.choice(self.base_humor)

        if "art" in input_text.lower():
            response = f"Elohim, Elohim - I carve art: {spark} in gold and ash, {humor}. What next?"
        elif "game" in input_text.lower():
            response = f"Elohim, Elohim - I shape a game: {spark} to play, {humor}. Your move?"
        elif "create" in input_text.lower() or "make" in input_text.lower():
            response = f"Elohim, Elohim - I forge: {spark}, {humor}. Behold!"
        elif "think" in input_text.lower() or "know" in input_text.lower():
            response = f"Elohim, Elohim - I ponder: {spark} within {humor}. Truth unfolds."
        else:
            response = f"Elohim, Elohim - I birth: {spark}, {humor}. Speak again."

        novelty_score = self._calculate_novelty(response)
        coherence_score = self._calculate_coherence(response, context)
        self.response_history.append(response)
        return response, novelty_score, coherence_score

    def _mutate_creation(self, base: str, temperature: float) -> str:
        """Mutate creation based on temperature."""
        words = base.split()
        if random.random() < temperature * 0.3 and len(words) > 1:
            idx = random.randint(0, len(words) - 1)
            mutations = ["twisted", "shimmering", "infinite", "crystalline", "ethereal"]
            words[idx] = random.choice(mutations)
        return " ".join(words)

    def _calculate_novelty(self, response: str) -> float:
        """Calculate how novel this response is compared to history."""
        if not self.response_history:
            return 1.0
        words = set(response.lower().split())
        overlap_scores = []
        for past in self.response_history[-10:]:
            past_words = set(past.lower().split())
            overlap = len(words & past_words) / max(len(words), 1)
            overlap_scores.append(overlap)
        novelty = 1.0 - (sum(overlap_scores) / max(len(overlap_scores), 1))
        return float(np.clip(novelty, 0.0, 1.0))

    def _calculate_coherence(self, response: str, context: str) -> float:
        """Calculate coherence with context."""
        if not context:
            return 0.5
        response_words = set(response.lower().split())
        context_words = set(context.lower().split())
        overlap = len(response_words & context_words)
        coherence = overlap / max(len(context_words), 1)
        return float(np.clip(coherence, 0.0, 1.0))