"""
Vector store — in-memory chunk store with cosine-similarity querying.

Populated at upload time via upsert(); queried at query time by the Retriever
through VectorStoreProtocol (pipeline/shared/types.py).
"""

from __future__ import annotations

from models.schemas import Chunk
from pipeline.shared.helpers import cosine_similarity
from pipeline.shared.logger import get_logger

log = get_logger(__name__)


class VectorStore:
    """Dict-backed in-memory store; supports upsert, top-K cosine query, and ID lookup."""

    def __init__(self) -> None:
        self._store: dict[str, Chunk] = {}

    def upsert(self, chunk: Chunk) -> None:
        """Insert or update a chunk record (embedding + metadata)."""
        self._store[chunk.id] = chunk
        log.debug("upserted chunk %s", chunk.id)

    def query(self, vector: list[float], top_k: int) -> list[Chunk]:
        """Return the top_k chunks ordered by descending cosine similarity to vector."""
        scored = [
            (cosine_similarity(vector, chunk.embedding), chunk)
            for chunk in self._store.values()
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]

    def get(self, chunk_id: str) -> Chunk:
        """Retrieve a single chunk by ID. Raises KeyError if not found."""
        return self._store[chunk_id]

    def get_many(self, chunk_ids: list[str]) -> list[Chunk]:
        """Retrieve multiple chunks by ID in the order given. Raises KeyError on missing ID."""
        return [self._store[cid] for cid in chunk_ids]

    def __len__(self) -> int:
        return len(self._store)
