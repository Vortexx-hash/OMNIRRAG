"""
Phase 2 tests — relation builder (query relevance, similarity, NLI, NER).
"""

from __future__ import annotations

import pytest

from tests.helpers import FakeEmbedder, make_chunk, make_query
from pipeline.relations.query_relevance import compute_query_relevance
from pipeline.relations.chunk_similarity import compute_similarity_matrix
from pipeline.relations.nli import NLIClassifier, build_relation_pairs, _apply_scope_qualifier_rule
from pipeline.relations.ner import NERExtractor, extract_all
from pipeline.shared.constants import NLI_CONTRADICTION, NLI_NO_CONTRADICTION, SCOPE_QUALIFIERS


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_embedder = FakeEmbedder()


def _chunk(chunk_id: str, text: str) -> object:
    return make_chunk(chunk_id, text, _embedder.encode(text))


# ---------------------------------------------------------------------------
# 3.1 Query Relevance
# ---------------------------------------------------------------------------

def test_query_relevance_scores_indexed_by_chunk_id():
    chunks = [_chunk("c1", "Bolivia capital"), _chunk("c2", "ocean biology")]
    query = make_query(_embedder.encode("capital of Bolivia"))
    scores = compute_query_relevance(query, chunks)

    assert set(scores.keys()) == {"c1", "c2"}
    assert all(isinstance(v, float) for v in scores.values())


def test_query_relevance_higher_for_more_similar_chunk():
    chunks = [
        _chunk("relevant", "capital of Bolivia"),
        _chunk("irrelevant", "ocean biology marine"),
    ]
    query = make_query(_embedder.encode("capital of Bolivia"))
    scores = compute_query_relevance(query, chunks)

    assert scores["relevant"] > scores["irrelevant"]


# ---------------------------------------------------------------------------
# 3.2 Chunk Similarity
# ---------------------------------------------------------------------------

def test_similarity_matrix_has_entry_for_all_pairs():
    chunks = [_chunk(f"c{i}", f"chunk text {i}") for i in range(4)]
    matrix = compute_similarity_matrix(chunks)
    n = len(chunks)
    expected_pairs = n * (n - 1) // 2
    assert len(matrix) == expected_pairs


def test_similarity_matrix_self_similarity_is_one():
    """Identical vectors in two different chunks produce similarity 1.0."""
    vec = [1.0, 0.0, 0.0]
    chunk_a = make_chunk("ca", "same text", vec)
    chunk_b = make_chunk("cb", "same text", vec)
    matrix = compute_similarity_matrix([chunk_a, chunk_b])
    key = ("ca", "cb")
    assert key in matrix
    assert abs(matrix[key] - 1.0) < 1e-9


def test_similarity_matrix_keys_are_sorted_tuples():
    chunks = [_chunk("z_chunk", "text z"), _chunk("a_chunk", "text a"), _chunk("m_chunk", "text m")]
    matrix = compute_similarity_matrix(chunks)
    for key in matrix:
        a, b = key
        assert a <= b, f"Key {key!r} is not sorted"


# ---------------------------------------------------------------------------
# 3.3 NLI
# ---------------------------------------------------------------------------

def test_nli_labels_plain_contradiction():
    """Two chunks asserting different values for the same subject → contradiction."""
    classifier = NLIClassifier()
    label = classifier.classify(
        "Paris is the capital of France.",
        "Lyon is the capital of France.",
    )
    assert label == NLI_CONTRADICTION


def test_nli_scope_qualifier_rule_resolves_surface_contradiction():
    """
    Bolivia canonical example: surface contradiction resolved by differing scope
    qualifiers must produce nli_label='contradiction' AND is_scope_difference=True.
    """
    text_a = "Sucre is the constitutional capital of Bolivia."
    text_b = "La Paz is the administrative capital of Bolivia."

    chunk_a = _chunk("ca", text_a)
    chunk_b = _chunk("cb", text_b)

    classifier = NLIClassifier()
    pairs = build_relation_pairs([chunk_a, chunk_b], classifier, SCOPE_QUALIFIERS)

    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.nli_label == NLI_CONTRADICTION
    assert pair.is_scope_difference is True


def test_nli_no_contradiction_for_matching_claims():
    """Two chunks that say essentially the same thing → no-contradiction."""
    classifier = NLIClassifier()
    label = classifier.classify(
        "La Paz is the seat of government of Bolivia.",
        "La Paz is the seat of government of Bolivia.",
    )
    assert label == NLI_NO_CONTRADICTION


# ---------------------------------------------------------------------------
# 3.4 NER
# ---------------------------------------------------------------------------

def test_ner_extracts_country_and_city_entities():
    extractor = NERExtractor()
    entities = extractor.extract("La Paz is a city in Bolivia.")
    labels = {e["text"]: e["label"] for e in entities}
    assert "Bolivia" in labels
    assert labels["Bolivia"] == "COUNTRY"
    assert "La Paz" in labels
    assert labels["La Paz"] == "CITY"


def test_ner_detects_known_scope_qualifiers():
    extractor = NERExtractor()
    entities = extractor.extract("Sucre is the constitutional capital of Bolivia.")
    qualifiers = extractor.detect_scope_qualifiers(entities)
    assert "constitutional" in qualifiers


def test_ner_entity_overlap_returns_shared_entities():
    extractor = NERExtractor()
    entities_a = extractor.extract("Sucre is the constitutional capital of Bolivia.")
    entities_b = extractor.extract("La Paz is the administrative capital of Bolivia.")
    overlap = extractor.compute_entity_overlap(entities_a, entities_b)
    assert "Bolivia" in overlap
