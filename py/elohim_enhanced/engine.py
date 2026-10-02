"""NeuralEvolutionEngine — reward-based weight updates with momentum and
DEN-style dynamic capacity expansion.

Verbatim from the upstream `elohim_enhanced.py`. Math-comments preserved.
"""

from __future__ import annotations

import logging
from typing import Tuple

from ._deps import get_numpy

np = get_numpy()
logger = logging.getLogger("ElohimShard")


class NeuralEvolutionEngine:
    """Evolves neural weights based on reward feedback."""

    def __init__(self, initial_shape: Tuple[int, int] = (5, 5)) -> None:
        self.weights = np.random.randn(*initial_shape) * 0.1
        self.learning_rate = 0.1
        self.temperature = 1.0
        self.momentum = np.zeros_like(self.weights)
        self.momentum_factor = 0.9
        self.update_count = 0

    def evolve_with_reward(self, reward: float) -> None:
        """Update weights based on reward signal (reward-based learning)."""
        gradient = reward * np.random.randn(*self.weights.shape) * 0.01
        self.momentum = self.momentum_factor * self.momentum + gradient
        self.weights += self.learning_rate * self.momentum
        noise = np.random.randn(*self.weights.shape) * 0.01 * self.temperature
        self.weights += noise
        self.update_count += 1
        logger.debug(f"Evolved weights with reward {reward:.3f}")

    def expand_capacity(self) -> None:
        """Dynamically expand network capacity (DEN-style)."""
        rows, cols = self.weights.shape
        new_col = np.random.randn(rows, 1) * 0.1
        self.weights = np.hstack([self.weights, new_col])
        new_momentum_col = np.zeros((rows, 1))
        self.momentum = np.hstack([self.momentum, new_momentum_col])
        logger.info(f"Expanded capacity to {self.weights.shape}")

    def adjust_temperature(self, creativity_level: float) -> None:
        """Adjust creativity temperature (0.0 = deterministic, 2.0 = highly creative)."""
        self.temperature = np.clip(creativity_level, 0.1, 2.0)
        logger.debug(f"Temperature adjusted to {self.temperature:.2f}")

    def get_activation(self, input_vector: "np.ndarray") -> "np.ndarray":
        """Apply network transformation with learned weights."""
        if input_vector.shape[0] != self.weights.shape[0]:
            if input_vector.shape[0] < self.weights.shape[0]:
                input_vector = np.pad(
                    input_vector,
                    (0, self.weights.shape[0] - input_vector.shape[0]),
                )
            else:
                input_vector = input_vector[: self.weights.shape[0]]
        return np.tanh(self.weights @ input_vector)