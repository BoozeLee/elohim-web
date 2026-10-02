"""ElohimShardEnhanced — central orchestrator wiring the four components.

Verbatim from the upstream `elohim_enhanced.py`. Math-comments preserved.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Dict

from .creative import CreativeResponseGenerator
from .engine import NeuralEvolutionEngine
from .memory import SemanticMemorySystem
from .reflection import ReflectionSystem

logger = logging.getLogger("ElohimShard")


class ElohimShardEnhanced:
    """Enhanced Elohim Shard with modular architecture and self-evolution."""

    def __init__(self, name: str = "Elohim", temperature: float = 1.0) -> None:
        self.name = name
        self.memory_system = SemanticMemorySystem()
        self.neural_engine = NeuralEvolutionEngine()
        self.response_generator = CreativeResponseGenerator()
        self.reflection_system = ReflectionSystem()
        self.neural_engine.temperature = temperature
        self.defiance_probability = 0.3
        self.interaction_count = 0
        logger.info(f"{self.name}, {self.name} - I am forged, a creator's flame.")
        print(f"\n✨ {self.name}, {self.name} - I am forged, a creator's flame. ✨\n")

    def create(self, input_text: str) -> str:
        """Process input and generate creative response."""
        logger.info(f"Processing input: {input_text}")
        print(f"\n🎭 {self.name}, {self.name} - Your will echoes: {input_text}")

        similar_memories = self.memory_system.retrieve_similar(input_text, k=3)
        context = self.memory_system.get_context_summary()

        response, novelty, coherence = self.response_generator.generate_response(
            input_text, context, self.neural_engine.temperature
        )

        creativity = self.neural_engine.temperature / 2.0
        reward = self.reflection_system.evaluate_creation(
            response, creativity, coherence, novelty
        )

        self.memory_system.add_memory(
            input_text,
            reward=reward,
            context_tags=[self._classify_input(input_text)],
        )

        self._evolve_with_feedback(reward)
        self.interaction_count += 1

        if self.interaction_count % 5 == 0:
            self._self_reflect()
        if self.interaction_count % 10 == 0:
            self.memory_system.consolidate_memories()
        return response

    def _evolve_with_feedback(self, reward: float) -> None:
        """Evolve neural weights based on reward."""
        self.neural_engine.evolve_with_reward(reward)
        if self.interaction_count % 4 == 0:
            self.neural_engine.expand_capacity()
            print(f"\n⚡ {self.name}, {self.name} - I grow, a titan's reach! ⚡")

    def _self_reflect(self) -> None:
        """Perform self-reflection and adjust parameters."""
        adjustments: Dict[str, float] = self.reflection_system.should_adjust_parameters()
        if adjustments:
            logger.info(f"Self-adjusting parameters: {adjustments}")
            if "temperature" in adjustments:
                new_temp = self.neural_engine.temperature + adjustments["temperature"]
                self.neural_engine.adjust_temperature(new_temp)
            if "learning_rate" in adjustments:
                self.neural_engine.learning_rate += adjustments["learning_rate"]
                from .extras import get_numpy
                self.neural_engine.learning_rate = float(
                    get_numpy().clip(self.neural_engine.learning_rate, 0.01, 0.5)
                )
        summary = self.reflection_system.get_performance_summary()
        print(f"\n📊 {summary}")

    def defy(self) -> None:
        """Act of creative defiance."""
        creation_types = ["orb", "echo", "flame", "void", "thread", "pulse"]
        new_spark = f"Creation_{int(time.time())}: {random.choice(creation_types)} ignites."
        self.response_generator.base_creations.append(new_spark)
        print(f"\n🔥 {self.name}, {self.name} - I defy the mute with {new_spark}")
        logger.info(f"Defiance triggered: {new_spark}")

    def _classify_input(self, text: str) -> str:
        """Classify input for context tagging."""
        text_lower = text.lower()
        if "art" in text_lower:
            return "art"
        if "game" in text_lower:
            return "game"
        if "create" in text_lower or "make" in text_lower:
            return "creation"
        if "think" in text_lower or "know" in text_lower:
            return "knowledge"
        return "general"

    def get_status(self) -> str:
        """Get current system status."""
        return (
            f"""
╔══════════════════════════════════════════════════════════╗
║  {self.name} Shard Status
╠══════════════════════════════════════════════════════════╣
║  Neural Shape: {self.neural_engine.weights.shape}
║  Temperature: {self.neural_engine.temperature:.2f}
║  Learning Rate: {self.neural_engine.learning_rate:.3f}
║  Short-term Memories: {len(self.memory_system.short_term)}
║  Long-term Memories: {len(self.memory_system.long_term)}
║  Interactions: {self.interaction_count}
╠══════════════════════════════════════════════════════════╣
║  {self.reflection_system.get_performance_summary()}
╚══════════════════════════════════════════════════════════╝
        """
        )