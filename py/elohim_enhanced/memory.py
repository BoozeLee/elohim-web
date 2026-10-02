"""SemanticMemorySystem — short-term deque + long-term list with hash-based
embeddings and cosine-similarity retrieval.

Verbatim from the upstream `elohim_enhanced.py` (math-comments preserved
exactly). Embeddings are deterministic via `numpy.random.seed(hash(text) % 2**32)`
so two processes hashing the same text get the same vector.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import List, Optional

from .extras import get_numpy
from .types import Memory

np = get_numpy()
logger = logging.getLogger("ElohimShard")


class SemanticMemorySystem:
    """Manages memory with semantic embeddings and retrieval."""

    def __init__(self, max_short_term: int = 10, max_long_term: int = 100) -> None:
        self.short_term = deque(maxlen=max_short_term)
        self.long_term: List[Memory] = []
        self.max_long_term = max_long_term
        self.embedding_dim = 64

    def create_embedding(self, text: str) -> "np.ndarray":
        """Simple hash-based embedding (in production, use sentence transformers)."""
        np.random.seed(hash(text) % (2 ** 32))
        embedding = np.random.randn(self.embedding_dim)
        embedding = embedding / np.linalg.norm(embedding)
        return embedding

    def add_memory(
        self,
        content: str,
        reward: float = 0.0,
        context_tags: Optional[List[str]] = None,
    ) -> Memory:
        """Add new memory to short-term storage."""
        embedding = self.create_embedding(content)
        memory = Memory(
            content=content,
            timestamp=time.time(),
            embedding=embedding,
            reward=reward,
            context_tags=context_tags or [],
        )
        self.short_term.append(memory)
        logger.debug(f"Added memory: {memory}")
        return memory

    def consolidate_memories(self) -> None:
        """Move important memories from short-term to long-term."""
        if not self.short_term:
            return
        sorted_memories = sorted(self.short_term, key=lambda m: m.reward, reverse=True)
        for memory in sorted_memories[:3]:
            if memory not in self.long_term:
                self.long_term.append(memory)
        if len(self.long_term) > self.max_long_term:
            self.long_term = sorted(
                self.long_term, key=lambda m: m.reward, reverse=True
            )[: self.max_long_term]
        logger.info(f"Consolidated memories. Long-term: {len(self.long_term)}")

    def retrieve_similar(self, query: str, k: int = 3) -> List[Memory]:
        """Retrieve k most similar memories using cosine similarity."""
        query_embedding = self.create_embedding(query)
        all_memories = list(self.short_term) + self.long_term
        if not all_memories:
            return []
        similarities = [
            (np.dot(query_embedding, memory.embedding), memory)
            for memory in all_memories
        ]
        similarities.sort(reverse=True, key=lambda pair: pair[0])
        return [mem for _, mem in similarities[:k]]

    def get_context_summary(self) -> str:
        """Generate summary of recent context."""
        recent = list(self.short_term)[-3:]
        if not recent:
            return "No recent context"
        return " | ".join(m.content[:40] for m in recent)