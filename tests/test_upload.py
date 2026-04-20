"""
Phase 1 tests — upload pipeline (chunker, embedder, vector store).
"""

from __future__ import annotations

import pytest

from pipeline.upload.chunker import Chunker, ChunkingStrategy
from pipeline.upload.vector_store import VectorStore
from tests.helpers import FakeEmbedder, make_chunk


# --- Chunker ---

def test_chunker_semantic_splits_on_topic_boundary():
    chunker = Chunker()
    text = (
        "First topic covers the history of the Roman Empire in great detail.\n\n"
        "Second topic discusses ocean biology and marine ecosystems.\n\n"
        "Third topic explores the formation of mountain ranges over time."
    )
    chunks = chunker.chunk(text, strategy=ChunkingStrategy.SEMANTIC)
    assert len(chunks) >= 2
    assert any("First" in c for c in chunks)
    assert any("Second" in c for c in chunks)


def test_chunker_char_respects_chunk_size():
    chunker = Chunker()
    text = "a" * 1000
    chunks = chunker.chunk(text, strategy=ChunkingStrategy.CHARACTER, chunk_size=100)
    assert len(chunks) == 10
    assert all(len(c) == 100 for c in chunks)


def test_chunker_overlap_produces_shared_window():
    chunker = Chunker()
    # Use a known repeating pattern so the overlap region is predictable
    text = "abcde" * 100  # 500 chars
    chunk_size, overlap_size = 100, 20
    chunks = chunker.chunk(
        text,
        strategy=ChunkingStrategy.OVERLAP,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
    )
    assert len(chunks) >= 2
    # Last overlap_size chars of chunk[0] must equal first overlap_size chars of chunk[1]
    assert chunks[0][-overlap_size:] == chunks[1][:overlap_size]


def test_chunker_hybrid_combines_strategies():
    chunker = Chunker()
    short_para = "Short intro paragraph.\n\n"
    # Long paragraph with no sentence breaks — will be split by overlap inside hybrid
    long_para = "word " * 100  # 500 chars
    text = short_para + long_para
    chunks = chunker.chunk(
        text, strategy=ChunkingStrategy.HYBRID, chunk_size=50, overlap_size=10
    )
    # Long paragraph must produce multiple chunks
    assert len(chunks) >= 3


# --- Embedder (via FakeEmbedder — tests the interface contract) ---

def test_embedder_encodes_to_fixed_dimension():
    embedder = FakeEmbedder()
    vec = embedder.encode("hello world")
    assert isinstance(vec, list)
    assert len(vec) == FakeEmbedder.DIM
    assert all(isinstance(x, float) for x in vec)


def test_embedder_batch_matches_single_encode():
    embedder = FakeEmbedder()
    texts = ["hello world", "capital of Bolivia", "mountain formation"]
    batch_result = embedder.encode_batch(texts)
    single_results = [embedder.encode(t) for t in texts]
    assert batch_result == single_results


# --- VectorStore ---

def test_vector_store_upsert_then_query_returns_chunk():
    store = VectorStore(path=None)
    chunk = make_chunk("c1", "Bolivia is a landlocked country", [1.0, 0.0, 0.0])
    store.upsert(chunk)
    results = store.query([1.0, 0.0, 0.0], top_k=1)
    assert len(results) == 1
    assert results[0].id == "c1"


def test_vector_store_query_top_k_ordering():
    store = VectorStore(path=None)
    # Vectors are already unit-length; cosine sim with [1,0,0] is the first component
    store.upsert(make_chunk("c_high", "high similarity", [1.0, 0.0, 0.0]))
    store.upsert(make_chunk("c_mid",  "mid similarity",  [0.8, 0.6, 0.0]))
    store.upsert(make_chunk("c_low",  "low similarity",  [0.0, 1.0, 0.0]))
    results = store.query([1.0, 0.0, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0].id == "c_high"
    assert results[1].id == "c_mid"


def test_vector_store_get_by_id():
    store = VectorStore(path=None)
    chunk = make_chunk("c42", "some text content", [0.5, 0.5, 0.0])
    store.upsert(chunk)
    retrieved = store.get("c42")
    assert retrieved.id == "c42"
    assert retrieved.text == "some text content"


def test_vector_store_get_missing_raises_key_error():
    store = VectorStore(path=None)
    with pytest.raises(KeyError):
        store.get("nonexistent_id")
