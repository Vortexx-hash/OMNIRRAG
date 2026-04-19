"""
Query Relevance — Stage 3.1.

Computes the cosine similarity between the query vector and each retrieved
chunk vector. Returns a per-chunk relevance score.
"""

from __future__ import annotations

from models.schemas import Chunk, Query
from pipeline.shared.helpers import cosine_similarity
from pipeline.shared.types import RelevanceScores


def compute_query_relevance(query: Query, chunks: list[Chunk]) -> RelevanceScores:
    """
    Return a mapping of chunk_id → cosine similarity with the query vector.
    Scores are in [−1, 1]; higher means more relevant.
    """
    return {chunk.id: cosine_similarity(query.vector, chunk.embedding) for chunk in chunks}
