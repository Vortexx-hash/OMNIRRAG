"""
Phase 1 tests — query normalizer and retriever.
"""

from __future__ import annotations

from pipeline.query.normalizer import QueryNormalizer
from pipeline.query.retriever import Retriever
from pipeline.upload.vector_store import VectorStore
from tests.helpers import FakeEmbedder, make_chunk, make_query


# --- QueryNormalizer ---

def test_normalizer_strips_filler_words():
    normalizer = QueryNormalizer(FakeEmbedder())
    q = normalizer.normalize("What is the capital of Bolivia?")
    words = q.normalized.lower().split()
    for filler in ["what", "is", "the", "of"]:
        assert filler not in words
    # Meaningful tokens must survive
    assert "capital" in q.normalized.lower()


def test_normalizer_extracts_entity_and_property():
    normalizer = QueryNormalizer(FakeEmbedder())
    q = normalizer.normalize("What is the capital of Bolivia?")
    entity_texts = [e["text"] for e in q.entities]
    assert "Bolivia" in entity_texts
    assert q.property == "capital"


def test_normalizer_encodes_query_vector():
    normalizer = QueryNormalizer(FakeEmbedder())
    q = normalizer.normalize("capital of Bolivia")
    assert isinstance(q.vector, list)
    assert len(q.vector) == FakeEmbedder.DIM
    assert any(x != 0.0 for x in q.vector)


# --- Retriever ---

def test_retriever_returns_top_k_by_similarity():
    store = VectorStore()
    dim = 5
    for i in range(dim):
        v = [1.0 if j == i else 0.0 for j in range(dim)]
        store.upsert(make_chunk(f"c{i}", f"chunk {i}", v))
    retriever = Retriever(store)
    # Query vector points along dimension 0 → c0 should rank first
    query = make_query([1.0, 0.0, 0.0, 0.0, 0.0])
    results = retriever.retrieve(query, top_k=3)
    assert len(results) == 3
    assert results[0].id == "c0"


def test_retriever_excludes_low_similarity_chunks():
    store = VectorStore()
    store.upsert(make_chunk("high", "highly relevant chunk", [1.0, 0.0]))
    store.upsert(make_chunk("low",  "orthogonal chunk",      [0.0, 1.0]))
    retriever = Retriever(store)
    query = make_query([1.0, 0.0])
    results = retriever.retrieve(query, top_k=1)
    assert len(results) == 1
    assert results[0].id == "high"
