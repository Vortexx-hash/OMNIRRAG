"""
Shared test helpers for Phase 1 tests.

FakeEmbedder produces deterministic, dependency-free vectors using a
word-hash bag-of-words approach so that semantically similar texts
(sharing words) produce higher cosine similarity — enough for retrieval
ordering tests without any ML library.
"""

from __future__ import annotations

import hashlib
import math

from models.schemas import Chunk, Query


class FakeEmbedder:
    """Deterministic word-overlap embedder — no ML dependencies.

    Maps text to a DIM-dimensional unit vector: each word increments the
    dimension given by hash(word) % DIM. Normalised to unit length.
    Two texts sharing words will have higher cosine similarity.
    """

    DIM: int = 16

    def encode(self, text: str) -> list[float]:
        vec = [0.0] * self.DIM
        for word in text.lower().split():
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            vec[h % self.DIM] += 1.0
        magnitude = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / magnitude for x in vec]

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.encode(t) for t in texts]


def make_chunk(
    chunk_id: str,
    text: str,
    embedding: list[float],
    *,
    credibility_score: float = 0.8,
    credibility_tier: int = 2,
    source_doc_id: str = "doc1",
) -> Chunk:
    return Chunk(
        id=chunk_id,
        source_doc_id=source_doc_id,
        text=text,
        embedding=embedding,
        credibility_score=credibility_score,
        credibility_tier=credibility_tier,
    )


def make_query(
    vector: list[float],
    normalized: str = "test query",
    raw: str = "test query",
) -> Query:
    return Query(
        raw=raw,
        normalized=normalized,
        entities=[],
        property="unknown",
        intent="factual lookup",
        vector=vector,
    )
