"""
Phase 3 tests — credibility scorer and DPP selector.

Domain: medical / clinical (intentionally different from Bolivia).
  - Clear contradiction: first-line diabetes treatment (Metformin vs Insulin)
  - Near-duplicate: two chunks with identical text
  - Off-topic: ocean biology chunk with zero word overlap to the query
  - Diverse pair: diabetes chunk + cardiovascular chunk
"""

from __future__ import annotations

import pytest

from tests.helpers import FakeEmbedder, make_chunk, make_query
from pipeline.credibility.scorer import assign_tier, tier_to_score, score_chunk
from pipeline.selection.dpp_selector import DPPSelector
from pipeline.relations.chunk_similarity import compute_similarity_matrix
from pipeline.relations.query_relevance import compute_query_relevance
from models.schemas import RelationPair
from pipeline.shared.constants import (
    CREDIBILITY_TIER_RANGES,
    DROP_REASON_IRRELEVANT,
    DROP_REASON_REDUNDANT,
    NLI_CONTRADICTION,
    NLI_NO_CONTRADICTION,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_embedder = FakeEmbedder()


def _chunk(chunk_id: str, text: str, *, tier: int = 2, score: float = 0.8):
    return make_chunk(
        chunk_id, text, _embedder.encode(text),
        credibility_score=score, credibility_tier=tier,
    )


def _contradiction_pair(a_id: str, b_id: str) -> RelationPair:
    """Minimal RelationPair with nli_label='contradiction'."""
    key = (a_id, b_id) if a_id <= b_id else (b_id, a_id)
    return RelationPair(
        chunk_a_id=key[0],
        chunk_b_id=key[1],
        similarity_score=0.0,
        nli_label=NLI_CONTRADICTION,
        entity_overlap=[],
        scope_qualifiers=[],
        is_scope_difference=False,
    )


# ---------------------------------------------------------------------------
# 3.A  Credibility scorer
# ---------------------------------------------------------------------------

def test_credibility_tier_1_source_gets_high_score():
    score, tier = score_chunk({"source_type": "government"})
    assert tier == 1
    assert score >= 0.90


def test_credibility_tier_4_source_gets_low_score():
    score, tier = score_chunk({"source_type": "anonymous"})
    assert tier == 4
    assert score <= 0.39


def test_credibility_unknown_source_raises():
    with pytest.raises(ValueError):
        score_chunk({"source_type": "x_unknown_type_xyz"})


def test_credibility_assign_tier_is_case_insensitive():
    assert assign_tier("GOVERNMENT") == assign_tier("government") == 1
    assert assign_tier("Academic") == assign_tier("academic") == 2


def test_credibility_tier_midpoints_are_within_range():
    """Every tier's midpoint score must sit inside its declared score range."""
    for tier, (lo, hi) in CREDIBILITY_TIER_RANGES.items():
        s = tier_to_score(tier)
        assert lo <= s <= hi, f"Tier {tier}: score {s} outside [{lo}, {hi}]"


def test_credibility_tier_ordering():
    """Tier 1 must score higher than tier 2, which must score higher than tier 4."""
    assert tier_to_score(1) > tier_to_score(2) > tier_to_score(3) > tier_to_score(4)


# ---------------------------------------------------------------------------
# 3.B  DPP selector
# ---------------------------------------------------------------------------

def test_dpp_selected_count_does_not_exceed_input():
    """When max_chunks > available chunks, all or fewer chunks are returned."""
    chunks = [_chunk(f"c{i}", f"medical treatment diabetes glucose chunk {i}") for i in range(3)]
    query = make_query(_embedder.encode("medical treatment"))
    rel_scores = compute_query_relevance(query, chunks)
    sim_matrix = compute_similarity_matrix(chunks)

    result = DPPSelector(max_chunks=10).select(chunks, [], rel_scores, sim_matrix)

    all_ids = {c.id for c in chunks}
    assert len(result.selected_ids) <= len(chunks)
    assert set(result.selected_ids) | set(result.dropped_ids) == all_ids


def test_dpp_drops_redundant_duplicate_chunks():
    """
    Two chunks with identical text yield similarity=1.0, well above the 0.85
    threshold.  The DPP must not select both.
    """
    text = "Metformin is the first line treatment for type 2 diabetes"
    c1 = _chunk("c1", text)
    c1_dup = _chunk("c1_dup", text)       # identical embedding → sim = 1.0
    c2 = _chunk("c2", "Insulin injection subcutaneous administration blood glucose")

    chunks = [c1, c1_dup, c2]
    query = make_query(_embedder.encode("diabetes treatment medication"))
    rel_scores = compute_query_relevance(query, chunks)
    sim_matrix = compute_similarity_matrix(chunks)

    result = DPPSelector(max_chunks=2).select(chunks, [], rel_scores, sim_matrix)

    selected = set(result.selected_ids)
    assert not ({"c1", "c1_dup"} <= selected), \
        "Both near-duplicates must not both be selected"
    assert DROP_REASON_REDUNDANT in result.drop_reasons.values(), \
        "At least one chunk should be dropped as 'redundant'"


def test_dpp_preserves_at_least_one_chunk_per_conflict_cluster():
    """
    When max_chunks=1 and there is a conflict cluster, the selector must return
    a cluster member even if an outsider has higher raw relevance.

    Setup:
      ca / cb — contradiction pair about aspirin, near-zero relevance to query
      c_high  — very relevant to query ('climate weather temperature')
    Without the hard constraint, c_high would be the only selection.
    With the constraint, one of {ca, cb} is seeded and fills the only slot.
    """
    c_a = _chunk("ca", "aspirin anticoagulant blood thinning platelet clot prevention")
    c_b = _chunk("cb", "aspirin prostaglandin inhibitor fever analgesic pain relief")
    c_high = _chunk("ch", "climate weather temperature forecast precipitation rain storm")

    query = make_query(_embedder.encode("climate weather temperature forecast"))
    chunks = [c_a, c_b, c_high]
    rel_scores = compute_query_relevance(query, chunks)
    sim_matrix = compute_similarity_matrix(chunks)

    pair = _contradiction_pair("ca", "cb")
    result = DPPSelector(max_chunks=1).select(chunks, [pair], rel_scores, sim_matrix)

    assert len(result.selected_ids) == 1
    assert result.selected_ids[0] in {"ca", "cb"}, (
        "Conflict cluster hard constraint must place a cluster member in the selection"
    )


def test_dpp_irrelevant_chunk_is_dropped():
    """A chunk semantically orthogonal to the query must be dropped."""
    c_rel = _chunk("cr", "metformin diabetes treatment blood glucose medication")
    c_irr = _chunk("ci", "ocean coral reef marine biology deep sea ecosystem")

    query = make_query(_embedder.encode("metformin diabetes treatment"))
    chunks = [c_rel, c_irr]
    rel_scores = compute_query_relevance(query, chunks)
    sim_matrix = compute_similarity_matrix(chunks)

    result = DPPSelector(max_chunks=1).select(chunks, [], rel_scores, sim_matrix)

    assert "cr" in result.selected_ids
    assert "ci" in result.dropped_ids


def test_dpp_drop_reasons_populated_correctly():
    """
    Verify both drop reason categories are assigned correctly:
      - c1_dup (identical to c1) → 'redundant'
      - c_other (off-topic)      → 'irrelevant'
    """
    text = "climate change global warming greenhouse gas carbon emissions"
    c1 = _chunk("c1", text)
    c1_dup = _chunk("c1_dup", text)         # sim = 1.0 → redundant
    c_other = _chunk("c_other", "ocean marine biology coral reef ecosystem plankton")

    chunks = [c1, c1_dup, c_other]
    query = make_query(_embedder.encode("climate change global warming"))
    rel_scores = compute_query_relevance(query, chunks)
    sim_matrix = compute_similarity_matrix(chunks)

    result = DPPSelector(max_chunks=1).select(chunks, [], rel_scores, sim_matrix)

    assert result.drop_reasons.get("c1_dup") == DROP_REASON_REDUNDANT
    assert result.drop_reasons.get("c_other") == DROP_REASON_IRRELEVANT


def test_dpp_no_relations_selects_diverse_pair():
    """
    With no contradiction pairs and a high diversity weight (β=1.0), the selector
    should prefer a relevant + diverse pair over two similar high-relevance chunks.

    c1 — diabetes treatment (highest relevance to query)
    c2 — diabetes medication (very similar to c1, redundant)
    c3 — cardiovascular cholesterol (diverse, low relevance)

    With β=1.0 the diversity bonus tips the scale toward {c1, c3}.
    """
    c1 = _chunk("c1", "diabetes treatment metformin insulin medication glucose")
    c2 = _chunk("c2", "diabetes treatment metformin insulin medication therapy")   # ≈ c1
    c3 = _chunk("c3", "cardiovascular cholesterol statin heart disease lipid")

    chunks = [c1, c2, c3]
    query = make_query(_embedder.encode("diabetes treatment medication"))
    rel_scores = compute_query_relevance(query, chunks)
    sim_matrix = compute_similarity_matrix(chunks)

    result = DPPSelector(max_chunks=2, beta=1.0).select(chunks, [], rel_scores, sim_matrix)

    assert len(result.selected_ids) == 2
    assert "c1" in result.selected_ids, "Most relevant chunk must be selected"
    assert "c3" in result.selected_ids, "Diverse chunk preferred over near-duplicate"


def test_dpp_result_is_partition_of_input():
    """selected_ids ∪ dropped_ids must equal the full input chunk set."""
    chunks = [_chunk(f"c{i}", f"text content topic subject chunk {i}") for i in range(6)]
    query = make_query(_embedder.encode("content topic"))
    rel_scores = compute_query_relevance(query, chunks)
    sim_matrix = compute_similarity_matrix(chunks)

    result = DPPSelector(max_chunks=3).select(chunks, [], rel_scores, sim_matrix)

    all_ids = {c.id for c in chunks}
    assert set(result.selected_ids) | set(result.dropped_ids) == all_ids
    assert set(result.selected_ids) & set(result.dropped_ids) == set()
