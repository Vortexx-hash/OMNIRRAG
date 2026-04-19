"""
Chunk–Chunk Similarity — Stage 3.2.

Computes pairwise cosine similarity for all retrieved chunk pairs.
Used by the DPP selector to identify redundant chunks and by NER
to build the entity overlap matrix.
"""

from __future__ import annotations

from itertools import combinations

from models.schemas import Chunk
from pipeline.shared.helpers import cosine_similarity, chunk_pair_key
from pipeline.shared.types import SimilarityMatrix


def compute_similarity_matrix(chunks: list[Chunk]) -> SimilarityMatrix:
    """
    Return a mapping of (chunk_a_id, chunk_b_id) → cosine similarity.
    Keys are sorted tuples to avoid duplicate pairs.
    """
    matrix: SimilarityMatrix = {}
    for chunk_a, chunk_b in combinations(chunks, 2):
        key = chunk_pair_key(chunk_a.id, chunk_b.id)
        matrix[key] = cosine_similarity(chunk_a.embedding, chunk_b.embedding)
    return matrix
