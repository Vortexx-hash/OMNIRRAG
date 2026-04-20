"""
Vector store — dict-backed store with cosine-similarity querying and JSON persistence.

Chunks (including embeddings) are written to data/vector_store.json on every upsert
and loaded back on initialisation, so the index survives server restarts.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib

from models.schemas import Chunk
from pipeline.shared.helpers import cosine_similarity
from pipeline.shared.logger import get_logger

log = get_logger(__name__)

_PERSIST_PATH = pathlib.Path("data/vector_store.json")


class VectorStore:
    """Dict-backed store; supports upsert, top-K cosine query, and ID lookup.

    Pass ``path=None`` for an ephemeral in-memory instance (no disk I/O).
    """

    def __init__(self, path: pathlib.Path | None = _PERSIST_PATH) -> None:
        self._path = path
        self._store: dict[str, Chunk] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                records = json.load(f)
            for r in records:
                chunk = Chunk(**r)
                self._store[chunk.id] = chunk
            log.info("vector store: loaded %d chunks from %s", len(self._store), self._path)
        except Exception as exc:
            log.warning("vector store: could not load persisted data (%s) — starting empty", exc)

    def _save(self) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump([dataclasses.asdict(c) for c in self._store.values()], f)
        except Exception as exc:
            log.warning("vector store: failed to persist (%s)", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert(self, chunk: Chunk) -> None:
        """Insert or update a chunk record (embedding + metadata)."""
        self._store[chunk.id] = chunk
        self._save()
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
