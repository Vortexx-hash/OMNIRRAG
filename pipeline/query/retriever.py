"""
Embedding Retriever — Stage 1.

Delegates top-K cosine similarity search to the vector store and returns
the retrieved chunks in ranked order.
"""

from __future__ import annotations

from models.schemas import Chunk, Query
from pipeline.shared.constants import TOP_K_DEFAULT
from pipeline.shared.types import VectorStoreProtocol


class Retriever:
    """Returns top-K chunks from the vector store for a given query."""

    def __init__(self, vector_store: VectorStoreProtocol) -> None:
        self._store = vector_store

    def retrieve(self, query: Query, top_k: int = TOP_K_DEFAULT) -> list[Chunk]:
        """Return chunks ranked by cosine similarity to the query vector."""
        return self._store.query(query.vector, top_k)
