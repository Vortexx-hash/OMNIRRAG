"""
Integration tests — Phase 6.

Covers five scenario families described in CLAUDE.md:
  1. Ambiguity with scope qualifiers  → Case 1
  2. Strong winner (outlier rejected) → Case 2
  3. Unresolved conflict              → Case 3
  4. Redundant duplicate removal (DPP stage)
  5. Upload pipeline (credibility assignment)

The LLM stages (debate agents, answer synthesizer) are mocked so tests
run without hitting the OpenAI API.  All other pipeline stages run against
their real implementations.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from main import Pipeline
from models.schemas import Chunk, SynthesisResult
from pipeline.relations.chunk_similarity import compute_similarity_matrix
from pipeline.relations.query_relevance import compute_query_relevance
from pipeline.selection.dpp_selector import DPPSelector
from pipeline.shared.constants import (
    CONFLICT_AMBIGUITY,
    CONFLICT_OUTLIER,
    DECISION_CASE_AMBIGUITY,
    DECISION_CASE_STRONG_WINNER,
    DECISION_CASE_UNRESOLVED,
)
from pipeline.upload.vector_store import VectorStore
from tests.helpers import FakeEmbedder, make_query


# ---------------------------------------------------------------------------
# Mock response helpers
# ---------------------------------------------------------------------------

def _debate_init_resp(position_text: str, reasoning: str = "key claim") -> MagicMock:
    """Fake LLM response for DebateAgent.generate_initial_position()."""
    content = json.dumps({"position_text": position_text, "reasoning": reasoning})
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _debate_round_resp(
    confidence: float, status: str = "stable", reasoning: str = "unchanged"
) -> MagicMock:
    """Fake LLM response for DebateAgent.respond_to_broadcast()."""
    content = json.dumps(
        {"confidence": confidence, "status": status, "reasoning": reasoning}
    )
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _synth_resp(answer: str, sources: list[str], tags: list[str]) -> MagicMock:
    """Fake LLM response for AnswerSynthesizer._call_llm()."""
    content = json.dumps(
        {"answer": answer, "sources_cited": sources, "conflict_handling_tags": tags}
    )
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# Test fixtures / builders
# ---------------------------------------------------------------------------

def _chunk(
    cid: str,
    text: str,
    *,
    tier: int = 2,
    score: float = 0.80,
    doc_id: str = "doc",
) -> Chunk:
    fake = FakeEmbedder()
    return Chunk(
        id=cid,
        source_doc_id=doc_id,
        text=text,
        embedding=fake.encode(text),
        credibility_score=score,
        credibility_tier=tier,
    )


def _pipeline_with(*chunks: Chunk) -> Pipeline:
    """Return a Pipeline whose store is pre-seeded with the given chunks."""
    store = VectorStore(path=None)
    for c in chunks:
        store.upsert(c)
    return Pipeline(
        embedder=FakeEmbedder(),
        vector_store=store,
        top_k=len(chunks),          # retrieve all chunks in the store
    )


# Patch targets
_DEBATE_PATCH = "pipeline.debate.agent_bank.openai.OpenAI"
_SYNTH_PATCH = "pipeline.synthesis.answer_synthesizer.openai.OpenAI"


# ===========================================================================
# 1. Upload pipeline
# ===========================================================================

class TestUploadPipeline:
    """Verify upload-time credibility assignment and storage."""

    def test_government_source_assigns_tier1(self):
        store = VectorStore(path=None)
        p = Pipeline(embedder=FakeEmbedder(), vector_store=store)
        ids = p.upload(
            "Sucre is the constitutional capital of Bolivia.",
            {"source_type": "government"},
            "docA",
        )
        assert len(ids) >= 1
        stored = store.get(ids[0])
        assert stored.credibility_tier == 1
        assert stored.credibility_score >= 0.90

    def test_unverified_source_assigns_tier4(self):
        store = VectorStore(path=None)
        p = Pipeline(embedder=FakeEmbedder(), vector_store=store)
        ids = p.upload(
            "Some unverified claim about a capital city.",
            {"source_type": "unverified"},
            "docB",
        )
        assert len(ids) >= 1
        stored = store.get(ids[0])
        assert stored.credibility_tier == 4
        assert stored.credibility_score <= 0.39

    def test_academic_source_assigns_tier2(self):
        store = VectorStore(path=None)
        p = Pipeline(embedder=FakeEmbedder(), vector_store=store)
        ids = p.upload(
            "Metformin is recommended as first-line therapy for type 2 diabetes.",
            {"source_type": "academic"},
            "docC",
        )
        assert len(ids) >= 1
        stored = store.get(ids[0])
        assert stored.credibility_tier == 2
        assert 0.70 <= stored.credibility_score <= 0.89

    def test_empty_store_query_returns_unresolved_no_llm_needed(self):
        """Pipeline short-circuits with no-evidence answer when the store is empty."""
        p = Pipeline(embedder=FakeEmbedder(), vector_store=VectorStore(path=None))
        result = p.query("What is the capital of Bolivia?")
        assert result.decision_case == DECISION_CASE_UNRESOLVED
        assert result.answer == "No relevant evidence found."
        assert result.conflict_reports == []


# ===========================================================================
# 2. Ambiguity scenario — Case 1
# ===========================================================================

_SUCRE_TEXT = "Sucre is the constitutional capital of Bolivia"
_LAPAZ_TEXT = "La Paz is the administrative capital of Bolivia"


class TestAmbiguityScenario:
    """
    Bolivia dual-capital scenario.

    Two tier-1 chunks carry different scope qualifiers ("constitutional" vs
    "administrative").  NLI detects a surface contradiction; the scope
    qualifier rule marks it as is_scope_difference=True.  Both clusters are
    forced to CONFLICT_AMBIGUITY and determine_decision_case returns Case 1.
    """

    def _chunks(self):
        return (
            _chunk("sucre1", _SUCRE_TEXT, tier=1, score=0.95),
            _chunk("lapaz1", _LAPAZ_TEXT, tier=1, score=0.95),
        )

    def _debate_side_effects(self):
        # 2 agents → 2 initial + 2 round-1 = 4 debate LLM calls
        return [
            _debate_init_resp(_SUCRE_TEXT),
            _debate_init_resp(_LAPAZ_TEXT),
            _debate_round_resp(0.95),
            _debate_round_resp(0.95),
        ]

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_scope_conflict_yields_case_1(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Bolivia has two capitals: Sucre (constitutional) and La Paz (administrative).",
            ["sucre1", "lapaz1"],
            ["scope_conflict_preserved"],
        )

        result = p.query("What is the capital of Bolivia?")

        assert result.decision_case == DECISION_CASE_AMBIGUITY

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_all_clusters_classified_as_ambiguity(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Bolivia has two capitals.",
            ["sucre1", "lapaz1"],
            ["scope_conflict_preserved"],
        )

        result = p.query("What is the capital of Bolivia?")

        types = {r.conflict_type for r in result.conflict_reports}
        assert CONFLICT_AMBIGUITY in types
        assert CONFLICT_OUTLIER not in types

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_scope_conflict_preserved_tag_present(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Bolivia has two capitals.",
            ["sucre1", "lapaz1"],
            ["scope_conflict_preserved"],
        )

        result = p.query("What is the capital of Bolivia?")

        assert "scope_conflict_preserved" in result.conflict_handling_tags

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_synthesis_result_schema_is_valid(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Two valid capitals exist.",
            ["sucre1"],
            ["scope_conflict_preserved"],
        )

        result = p.query("What is the capital of Bolivia?")

        assert isinstance(result, SynthesisResult)
        assert isinstance(result.answer, str) and result.answer
        assert isinstance(result.decision_case, int)
        assert isinstance(result.conflict_reports, list)
        assert isinstance(result.conflict_handling_tags, list)
        assert isinstance(result.sources_cited, list)


# ===========================================================================
# 3. Strong winner scenario — Case 2
# ===========================================================================

_MET_POS = "Metformin is the first-line treatment for type 2 diabetes"
_BLEACH_POS = "Bleach cures diabetes completely"


class TestStrongWinnerScenario:
    """
    Consensus + tier-4 outlier → Case 2.

    One high-credibility chunk (consensus1, tier=1) and one tier-4 fringe
    chunk (outlier1, tier=4).  Both agents are isolated (word overlap < 0.2
    between metformin and bleach claims).  consensus1 survives as AMBIGUITY
    (high credibility keeps it from being rejected); outlier1 gets
    CONFLICT_OUTLIER (tier-4 gate + isolated + no scope qualifier).
    Exactly 1 surviving cluster → Case 2.

    Chunk IDs are chosen so DPP sorted order ("consensus1" < "outlier1") matches
    the agent instantiation order, making mock sequencing deterministic.
    """

    def _chunks(self):
        return (
            _chunk("consensus1",
                   "Metformin is the first-line treatment for type 2 diabetes",
                   tier=1, score=0.95),
            _chunk("outlier1",
                   "Bleach cures diabetes completely",
                   tier=4, score=0.10),
        )

    def _debate_side_effects(self):
        # DPP sorted order: "consensus1" < "outlier1"
        # 2 agents → 2 initial + 2 round-1 = 4 calls
        return [
            _debate_init_resp(_MET_POS),    # consensus1 initial
            _debate_init_resp(_BLEACH_POS), # outlier1 initial
            _debate_round_resp(0.95),       # consensus1 round-1
            _debate_round_resp(0.10),       # outlier1 round-1
        ]

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_outlier_rejected_yields_case_2(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Metformin is the first-line treatment for type 2 diabetes.",
            ["consensus1"],
            ["outlier_rejected"],
        )

        result = p.query("What is the first-line treatment for diabetes?")

        assert result.decision_case == DECISION_CASE_STRONG_WINNER

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_tier4_claim_appears_as_outlier_in_reports(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Metformin.",
            ["consensus1"],
            ["outlier_rejected"],
        )

        result = p.query("What is the first-line treatment for diabetes?")

        outlier_reports = [
            r for r in result.conflict_reports if r.conflict_type == CONFLICT_OUTLIER
        ]
        assert len(outlier_reports) >= 1

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_outlier_rejected_tag_present(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Metformin.",
            ["consensus1"],
            ["outlier_rejected"],
        )

        result = p.query("What is the first-line treatment for diabetes?")

        assert "outlier_rejected" in result.conflict_handling_tags

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_credibility_is_soft_signal_not_hard_filter(self, mock_debate, mock_synth):
        """
        The tier-4 outlier chunk must reach debate (not silently filtered before it).
        CLAUDE.md rule: credibility is a soft signal, never a hard gate.
        """
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Metformin.",
            ["consensus1"],
            ["outlier_rejected"],
        )

        result = p.query("What is the first-line treatment for diabetes?")

        # outlier1 must appear in a conflict report (it reached debate)
        all_reported_ids = {
            cid for r in result.conflict_reports for cid in r.chunk_ids
        }
        assert "outlier1" in all_reported_ids


# ===========================================================================
# 4. Unresolved conflict scenario — Case 3
# ===========================================================================

_NUCLEAR_POS = "Fission plants deliver reliable baseload generation around the clock"
_RENEWABLE_POS = "Photovoltaic panels convert sunlight without carbon dioxide"


class TestUnresolvedConflictScenario:
    """
    Energy debate: two equally credible claims, no scope qualifiers.

    Position texts use disjoint vocabulary so FakeEmbedder produces near-zero
    cosine similarity — preventing spurious cluster merging in the conflict
    report.  Both clusters survive as CONFLICT_AMBIGUITY with
    has_scope_qualifier=False → determine_decision_case returns Case 3.
    """

    def _chunks(self):
        return (
            _chunk("nuclear1",
                   "Fission plants deliver reliable baseload generation around the clock",
                   tier=2, score=0.80),
            _chunk("renewable1",
                   "Photovoltaic panels convert sunlight without carbon dioxide",
                   tier=2, score=0.80),
        )

    def _debate_side_effects(self):
        # 2 agents → 2 initial + 2 round-1 = 4 calls
        return [
            _debate_init_resp(_NUCLEAR_POS),
            _debate_init_resp(_RENEWABLE_POS),
            _debate_round_resp(0.80),
            _debate_round_resp(0.80),
        ]

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_no_scope_qualifiers_yields_case_3(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Evidence is inconclusive. Both nuclear and renewable energy claim to be safest.",
            ["nuclear1", "renewable1"],
            ["unresolved_conflict"],
        )

        result = p.query("What is the safest source of electricity?")

        assert result.decision_case == DECISION_CASE_UNRESOLVED

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_neither_cluster_classified_as_outlier(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Both positions have merit.",
            ["nuclear1", "renewable1"],
            ["unresolved_conflict"],
        )

        result = p.query("What is the safest source of electricity?")

        assert all(
            r.conflict_type != CONFLICT_OUTLIER for r in result.conflict_reports
        )

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_unresolved_conflict_tag_present(self, mock_debate, mock_synth):
        p = _pipeline_with(*self._chunks())
        mock_debate.return_value.chat.completions.create.side_effect = (
            self._debate_side_effects()
        )
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Conflicting evidence found.",
            ["nuclear1", "renewable1"],
            ["unresolved_conflict"],
        )

        result = p.query("What is the safest source of electricity?")

        assert "unresolved_conflict" in result.conflict_handling_tags


# ===========================================================================
# 5. Redundant duplicate removal (DPP stage)
# ===========================================================================

class TestRedundantDuplicateRemoval:
    """
    DPP must drop near-identical chunks (similarity > 0.85) and label them
    "redundant", preserving one representative and a diverse complement.

    Uses DPPSelector directly (with max_chunks=2) so the drop behaviour is
    observable without needing to expose internals through Pipeline.query().
    A second test verifies the full pipeline completes cleanly when duplicates
    are present in the store.
    """

    _DUP_TEXT = "Metformin is the first-line treatment for type 2 diabetes"
    _UNIQUE_TEXT = "Sucre is the constitutional capital of Bolivia"

    def _dup_chunks(self):
        return (
            _chunk("dup1", self._DUP_TEXT, tier=1, score=0.95),
            _chunk("dup2", self._DUP_TEXT, tier=2, score=0.85),  # identical text → similarity=1.0
            _chunk("unique1", self._UNIQUE_TEXT, tier=2, score=0.80),
        )

    def test_dpp_drops_identical_chunk_as_redundant(self):
        """
        With max_chunks=2 the selector must choose between dup1/dup2 and unique1.
        The kept duplicate and unique1 score higher than both duplicates together
        (redundancy penalty = 1.0 for identical pair).  One duplicate is dropped
        with drop_reason == "redundant".
        """
        fake = FakeEmbedder()
        chunks = list(self._dup_chunks())
        query = make_query(
            fake.encode("first-line treatment diabetes"),
            normalized="treatment diabetes",
        )
        relevance_scores = compute_query_relevance(query, chunks)
        similarity_matrix = compute_similarity_matrix(chunks)

        dpp = DPPSelector(max_chunks=2)
        result = dpp.select(
            chunks,
            relation_pairs=[],
            relevance_scores=relevance_scores,
            similarity_matrix=similarity_matrix,
        )

        assert len(result.dropped_ids) >= 1
        assert any(v == "redundant" for v in result.drop_reasons.values())
        # Both duplicates must NOT appear together in the selected set
        assert not {"dup1", "dup2"}.issubset(set(result.selected_ids))

    def test_dpp_keeps_at_most_one_of_the_duplicates(self):
        """Selected set contains at most one of {dup1, dup2}."""
        fake = FakeEmbedder()
        chunks = list(self._dup_chunks())
        query = make_query(fake.encode("treatment diabetes"), normalized="treatment diabetes")
        relevance_scores = compute_query_relevance(query, chunks)
        similarity_matrix = compute_similarity_matrix(chunks)

        dpp = DPPSelector(max_chunks=2)
        result = dpp.select(
            chunks,
            relation_pairs=[],
            relevance_scores=relevance_scores,
            similarity_matrix=similarity_matrix,
        )

        dup_count = sum(1 for sid in result.selected_ids if sid in ("dup1", "dup2"))
        assert dup_count <= 1

    @patch(_SYNTH_PATCH)
    @patch(_DEBATE_PATCH)
    def test_pipeline_completes_cleanly_with_duplicate_chunks(
        self, mock_debate, mock_synth
    ):
        """
        Full pipeline run: two identical chunks in the store.
        DPP keeps both (no max_chunks cap), debate converges on one position,
        result is a valid SynthesisResult with a non-empty answer.
        """
        chunks = (
            _chunk("dup1", self._DUP_TEXT, tier=1, score=0.95),
            _chunk("dup2", self._DUP_TEXT, tier=2, score=0.85),
        )
        p = _pipeline_with(*chunks)

        # With default max_chunks=None DPP keeps both; 2 agents in debate.
        # 2 initial + 2 round-1 = 4 debate calls
        mock_debate.return_value.chat.completions.create.side_effect = [
            _debate_init_resp(self._DUP_TEXT),
            _debate_init_resp(self._DUP_TEXT),
            _debate_round_resp(0.95),
            _debate_round_resp(0.85),
        ]
        mock_synth.return_value.chat.completions.create.return_value = _synth_resp(
            "Metformin is the first-line treatment for type 2 diabetes.",
            ["dup1"],
            ["outlier_rejected"],
        )

        result = p.query("What is the treatment for diabetes?")

        assert isinstance(result, SynthesisResult)
        assert result.answer
        assert result.decision_case in (
            DECISION_CASE_AMBIGUITY,
            DECISION_CASE_STRONG_WINNER,
            DECISION_CASE_UNRESOLVED,
        )
