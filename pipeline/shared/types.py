"""
Type aliases and shared structural protocols for the RAG pipeline.

Protocols allow query-time modules (pipeline/query/) to depend on abstractions
rather than concrete upload-time implementations, preserving the module boundary
defined in CLAUDE.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeAlias, runtime_checkable

if TYPE_CHECKING:
    pass

from models.schemas import Chunk

ChunkID: TypeAlias = str
AgentID: TypeAlias = str

# claim_text → list of agent_ids that support it
SupportMap: TypeAlias = dict[str, list[str]]

# (chunk_a_id, chunk_b_id) → cosine similarity score
SimilarityMatrix: TypeAlias = dict[tuple[ChunkID, ChunkID], float]

# chunk_id → relevance score against the query
RelevanceScores: TypeAlias = dict[ChunkID, float]


@runtime_checkable
class EmbedderProtocol(Protocol):
    """Structural interface for embedding models used across upload and query modules."""

    def encode(self, text: str) -> list[float]: ...

    def encode_batch(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Structural interface for the vector store consumed by the Retriever."""

    def upsert(self, chunk: Chunk) -> None: ...

    def query(self, vector: list[float], top_k: int) -> list[Chunk]: ...

    def get(self, chunk_id: str) -> Chunk: ...

    def get_many(self, chunk_ids: list[str]) -> list[Chunk]: ...
