"""
Shared utility functions used across pipeline modules.
"""

from __future__ import annotations

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return the cosine similarity between two dense vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def normalize_vector(v: list[float]) -> list[float]:
    """Return the L2-normalised form of v. Returns zero vector if input magnitude is zero."""
    magnitude = math.sqrt(sum(x * x for x in v))
    if magnitude == 0.0:
        return [0.0] * len(v)
    return [x / magnitude for x in v]


def chunk_pair_key(chunk_a_id: str, chunk_b_id: str) -> tuple[str, str]:
    """Return a canonical sorted key for a chunk pair to avoid duplicate entries."""
    return (chunk_a_id, chunk_b_id) if chunk_a_id <= chunk_b_id else (chunk_b_id, chunk_a_id)
