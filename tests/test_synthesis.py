"""
Phase 5 tests — conflict report and answer synthesizer.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from models.schemas import AgentPosition, ConflictReport, RelationPair, SynthesisResult
from pipeline.shared.constants import (
    CONFLICT_AMBIGUITY,
    CONFLICT_NOISE,
    CONFLICT_OUTLIER,
    CONFLICT_OVERSIMPLIFICATION,
    DECISION_CASE_AMBIGUITY,
    DECISION_CASE_STRONG_WINNER,
    DECISION_CASE_UNRESOLVED,
)
from pipeline.synthesis.conflict_report import (
    determine_decision_case,
    generate_conflict_reports,
)
from pipeline.synthesis.answer_synthesizer import AnswerSynthesizer
from tests.helpers import FakeEmbedder, make_chunk

_embedder = FakeEmbedder()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _chunk(cid: str, text: str, *, tier: int = 2, score: float = 0.8):
    return make_chunk(cid, text, _embedder.encode(text),
                      credibility_score=score, credibility_tier=tier)


def _pos(agent_id: str, chunk_id: str, text: str,
         conf: float = 0.8, status: str = "stable") -> AgentPosition:
    return AgentPosition(
        agent_id=agent_id,
        chunk_id=chunk_id,
        position_text=text,
        confidence=conf,
        status=status,
    )


def _make_mock_synthesis_response(answer: str, sources_cited=None, tags=None):
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "answer": answer,
        "sources_cited": sources_cited or [],
        "conflict_handling_tags": tags or [],
    })
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


# ──────────────────────────────────────────────────────────────────────────────
# Conflict Report tests
# ──────────────────────────────────────────────────────────────────────────────

def test_conflict_report_classifies_scope_difference_as_ambiguity():
    """Two positions with 'constitutional' vs 'administrative' qualifiers → both AMBIGUITY."""
    c1 = _chunk("c1", "Sucre is the constitutional capital of Bolivia.", tier=1, score=0.95)
    c2 = _chunk("c2", "La Paz is the administrative capital of Bolivia.", tier=1, score=0.95)

    pos1 = _pos("a1", "c1", "Sucre is the constitutional capital of Bolivia.")
    pos2 = _pos("a2", "c2", "La Paz is the administrative capital of Bolivia.")

    rp = RelationPair(
        chunk_a_id="c1",
        chunk_b_id="c2",
        similarity_score=0.7,
        nli_label="contradiction",
        entity_overlap=["Bolivia"],
        scope_qualifiers=["constitutional", "administrative"],
        is_scope_difference=True,
    )

    support_map = {
        pos1.position_text: ["a1"],
        pos2.position_text: ["a2"],
    }

    reports = generate_conflict_reports(
        positions=[pos1, pos2],
        support_map=support_map,
        isolated_agent_ids=[],
        chunks=[c1, c2],
        relation_pairs=[rp],
    )

    assert len(reports) == 2
    types = {r.conflict_type for r in reports}
    assert types == {CONFLICT_AMBIGUITY}


def test_conflict_report_classifies_zero_support_claim_as_outlier():
    """Isolated agent with tier=4, mean cred < 0.5, no qualifier → OUTLIER."""
    c_main = _chunk("cmain", "Metformin is first-line treatment for type 2 diabetes.", tier=1, score=0.9)
    c_fringe = _chunk("cfringe", "Bleach cures diabetes with no side effects.", tier=4, score=0.10)

    pos_main = _pos("a_main", "cmain", "Metformin is first-line treatment for type 2 diabetes.")
    pos_fringe = _pos("a_fringe", "cfringe", "Bleach cures diabetes with no side effects.",
                      conf=0.10, status="isolated")

    support_map = {
        pos_main.position_text: ["a_main"],
        pos_fringe.position_text: ["a_fringe"],
    }

    reports = generate_conflict_reports(
        positions=[pos_main, pos_fringe],
        support_map=support_map,
        isolated_agent_ids=["a_fringe"],
        chunks=[c_main, c_fringe],
        relation_pairs=[],
    )

    fringe_reports = [r for r in reports if "cfringe" in r.chunk_ids]
    assert fringe_reports, "Expected a report for the fringe chunk"
    assert fringe_reports[0].conflict_type == CONFLICT_OUTLIER


def test_conflict_report_classifies_incomplete_claim_as_oversimplification():
    """Low confidence (0.45), no qualifier, competing stronger cluster → OVERSIMPLIFICATION."""
    c_strong = _chunk("cstrong",
                      "Metformin is the first-line treatment for type 2 diabetes per clinical guidelines.",
                      tier=1, score=0.95)
    c_weak = _chunk("cweak",
                    "Diabetes can be treated with medication.",
                    tier=3, score=0.50)

    pos_strong = _pos("a_strong", "cstrong",
                      "Metformin is the first-line treatment for type 2 diabetes per clinical guidelines.",
                      conf=0.85)
    pos_weak = _pos("a_weak", "cweak",
                    "Diabetes can be treated with medication.",
                    conf=0.45)

    support_map = {
        pos_strong.position_text: ["a_strong"],
        pos_weak.position_text: ["a_weak"],
    }

    reports = generate_conflict_reports(
        positions=[pos_strong, pos_weak],
        support_map=support_map,
        isolated_agent_ids=[],
        chunks=[c_strong, c_weak],
        relation_pairs=[],
    )

    weak_reports = [r for r in reports if "cweak" in r.chunk_ids]
    assert weak_reports, "Expected a report for weak chunk"
    assert weak_reports[0].conflict_type == CONFLICT_OVERSIMPLIFICATION


def test_conflict_report_determines_case_1_for_scope_ambiguity():
    """Two ambiguity reports with scope qualifiers → DECISION_CASE_AMBIGUITY (1)."""
    r1 = ConflictReport(
        conflict_type=CONFLICT_AMBIGUITY,
        chunk_ids=["c1"],
        evidence_strength=0.8,
        decision_case=DECISION_CASE_AMBIGUITY,
        has_scope_qualifier=True,   # "constitutional capital"
    )
    r2 = ConflictReport(
        conflict_type=CONFLICT_AMBIGUITY,
        chunk_ids=["c2"],
        evidence_strength=0.75,
        decision_case=DECISION_CASE_AMBIGUITY,
        has_scope_qualifier=True,   # "administrative capital"
    )

    result = determine_decision_case([r1, r2])
    assert result == DECISION_CASE_AMBIGUITY


def test_conflict_report_determines_case_2_for_single_dominant_claim():
    """1 ambiguity + 1 outlier → determine_decision_case returns DECISION_CASE_STRONG_WINNER (2)."""
    r_winner = ConflictReport(
        conflict_type=CONFLICT_AMBIGUITY,
        chunk_ids=["c1"],
        evidence_strength=0.85,
        decision_case=DECISION_CASE_AMBIGUITY,
    )
    r_outlier = ConflictReport(
        conflict_type=CONFLICT_OUTLIER,
        chunk_ids=["c2"],
        evidence_strength=0.10,
        decision_case=DECISION_CASE_STRONG_WINNER,
    )

    result = determine_decision_case([r_winner, r_outlier])
    assert result == DECISION_CASE_STRONG_WINNER


def test_conflict_report_determines_case_3_when_no_majority():
    """Two ambiguity reports with no scope qualifiers → DECISION_CASE_UNRESOLVED (3)."""
    # Both are oversimplification (no scope qualifier, no clear winner)
    r1 = ConflictReport(
        conflict_type=CONFLICT_OVERSIMPLIFICATION,
        chunk_ids=["c1"],
        evidence_strength=0.50,
        decision_case=DECISION_CASE_STRONG_WINNER,
    )
    r2 = ConflictReport(
        conflict_type=CONFLICT_OVERSIMPLIFICATION,
        chunk_ids=["c2"],
        evidence_strength=0.50,
        decision_case=DECISION_CASE_STRONG_WINNER,
    )

    result = determine_decision_case([r1, r2])
    assert result == DECISION_CASE_UNRESOLVED


def test_conflict_report_evidence_strength_is_float_in_range():
    """evidence_strength must be in [0.0, 1.0]."""
    c = _chunk("c1", "Sucre is the constitutional capital.", tier=1, score=0.9)
    pos = _pos("a1", "c1", "Sucre is the constitutional capital.", conf=0.85)
    support_map = {pos.position_text: ["a1"]}

    reports = generate_conflict_reports(
        positions=[pos],
        support_map=support_map,
        isolated_agent_ids=[],
        chunks=[c],
        relation_pairs=[],
    )

    assert reports
    for r in reports:
        assert isinstance(r.evidence_strength, float)
        assert 0.0 <= r.evidence_strength <= 1.0


def test_conflict_report_returns_one_report_per_unique_cluster():
    """3 positions (2 same text, 1 different) → 2 reports."""
    c1 = _chunk("c1", "La Paz is the administrative capital.", tier=1, score=0.9)
    c2 = _chunk("c2", "La Paz is the administrative capital.", tier=2, score=0.8)
    c3 = _chunk("c3", "Sucre is the constitutional capital.", tier=1, score=0.95)

    pos1 = _pos("a1", "c1", "La Paz is the administrative capital.")
    pos2 = _pos("a2", "c2", "La Paz is the administrative capital.")
    pos3 = _pos("a3", "c3", "Sucre is the constitutional capital.")

    support_map = {
        pos1.position_text: ["a1", "a2"],
        pos3.position_text: ["a3"],
    }

    reports = generate_conflict_reports(
        positions=[pos1, pos2, pos3],
        support_map=support_map,
        isolated_agent_ids=[],
        chunks=[c1, c2, c3],
        relation_pairs=[],
    )

    assert len(reports) == 2


def test_conflict_report_empty_positions_returns_empty_list():
    """No positions → empty list."""
    reports = generate_conflict_reports(
        positions=[],
        support_map={},
        isolated_agent_ids=[],
        chunks=[],
        relation_pairs=[],
    )
    assert reports == []


# ──────────────────────────────────────────────────────────────────────────────
# Answer Synthesizer tests (mock LLM)
# ──────────────────────────────────────────────────────────────────────────────

def test_synthesizer_case_1_answer_includes_all_qualifiers():
    """Case 1: mock returns answer mentioning both qualifiers; assert they appear in result.answer."""
    c1 = _chunk("c1", "Sucre is the constitutional capital of Bolivia.", tier=1, score=0.95)
    c2 = _chunk("c2", "La Paz is the administrative capital of Bolivia.", tier=1, score=0.95)

    pos1 = _pos("a1", "c1", "Sucre is the constitutional capital of Bolivia.")
    pos2 = _pos("a2", "c2", "La Paz is the administrative capital of Bolivia.")

    r1 = ConflictReport(conflict_type=CONFLICT_AMBIGUITY, chunk_ids=["c1"],
                        evidence_strength=0.85, decision_case=DECISION_CASE_AMBIGUITY)
    r2 = ConflictReport(conflict_type=CONFLICT_AMBIGUITY, chunk_ids=["c2"],
                        evidence_strength=0.85, decision_case=DECISION_CASE_AMBIGUITY)

    mock_resp = _make_mock_synthesis_response(
        "Bolivia has two capitals: Sucre is the constitutional capital, "
        "while La Paz is the administrative capital.",
        sources_cited=["c1", "c2"],
        tags=["scope_conflict_preserved"],
    )

    with patch("pipeline.synthesis.answer_synthesizer.openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        synth = AnswerSynthesizer()
        result = synth.synthesize([r1, r2], [pos1, pos2], [c1, c2])

    assert "constitutional" in result.answer.lower()
    assert "administrative" in result.answer.lower()


def test_synthesizer_case_2_answer_returns_single_claim():
    """Case 2: mock returns single claim; assert decision_case == 2."""
    c_win = _chunk("cwin", "Metformin is first-line treatment for type 2 diabetes.", tier=1, score=0.9)
    c_out = _chunk("cout", "Bleach cures diabetes.", tier=4, score=0.1)

    pos_win = _pos("a_win", "cwin", "Metformin is first-line treatment for type 2 diabetes.")
    pos_out = _pos("a_out", "cout", "Bleach cures diabetes.", conf=0.1, status="isolated")

    r_win = ConflictReport(conflict_type=CONFLICT_AMBIGUITY, chunk_ids=["cwin"],
                           evidence_strength=0.85, decision_case=DECISION_CASE_AMBIGUITY)
    r_out = ConflictReport(conflict_type=CONFLICT_OUTLIER, chunk_ids=["cout"],
                           evidence_strength=0.05, decision_case=DECISION_CASE_STRONG_WINNER)

    mock_resp = _make_mock_synthesis_response(
        "Metformin is the first-line treatment for type 2 diabetes.",
        sources_cited=["cwin"],
        tags=["outlier_rejected"],
    )

    with patch("pipeline.synthesis.answer_synthesizer.openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        synth = AnswerSynthesizer()
        result = synth.synthesize([r_win, r_out], [pos_win, pos_out], [c_win, c_out])

    assert result.decision_case == DECISION_CASE_STRONG_WINNER


def test_synthesizer_case_3_answer_states_insufficient_evidence():
    """Case 3: mock returns unresolved; assert decision_case == 3."""
    c1 = _chunk("c1", "Nuclear energy is the safest source of electricity.", tier=2, score=0.8)
    c2 = _chunk("c2", "Renewable energy is the safest electricity source.", tier=2, score=0.8)

    pos1 = _pos("a1", "c1", "Nuclear energy is the safest source of electricity.")
    pos2 = _pos("a2", "c2", "Renewable energy is the safest electricity source.")

    # Both oversimplification → case 3
    r1 = ConflictReport(conflict_type=CONFLICT_OVERSIMPLIFICATION, chunk_ids=["c1"],
                        evidence_strength=0.5, decision_case=DECISION_CASE_STRONG_WINNER)
    r2 = ConflictReport(conflict_type=CONFLICT_OVERSIMPLIFICATION, chunk_ids=["c2"],
                        evidence_strength=0.5, decision_case=DECISION_CASE_STRONG_WINNER)

    mock_resp = _make_mock_synthesis_response(
        "The available evidence presents conflicting claims and does not allow a definitive answer.",
        sources_cited=[],
        tags=["unresolved_conflict"],
    )

    with patch("pipeline.synthesis.answer_synthesizer.openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        synth = AnswerSynthesizer()
        result = synth.synthesize([r1, r2], [pos1, pos2], [c1, c2])

    assert result.decision_case == DECISION_CASE_UNRESOLVED


def test_synthesizer_does_not_filter_by_credibility():
    """A tier-4 surviving report produces a SynthesisResult (not silently dropped)."""
    c_tier4 = _chunk("ct4", "Some claim from a low-credibility source.", tier=4, score=0.2)
    pos = _pos("a1", "ct4", "Some claim from a low-credibility source.")

    # Surviving report (not OUTLIER/NOISE) even though tier=4
    r = ConflictReport(conflict_type=CONFLICT_AMBIGUITY, chunk_ids=["ct4"],
                       evidence_strength=0.15, decision_case=DECISION_CASE_AMBIGUITY)

    mock_resp = _make_mock_synthesis_response(
        "A claim from a low-credibility source survived debate.",
        sources_cited=["ct4"],
        tags=["scope_conflict_preserved"],
    )

    with patch("pipeline.synthesis.answer_synthesizer.openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        synth = AnswerSynthesizer()
        result = synth.synthesize([r], [pos], [c_tier4])

    assert isinstance(result, SynthesisResult)
    assert result.answer != ""


def test_synthesizer_result_schema_compliance():
    """Validate all SynthesisResult fields: correct types and value constraints."""
    c = _chunk("c1", "Sucre is the constitutional capital of Bolivia.", tier=1, score=0.95)
    pos = _pos("a1", "c1", "Sucre is the constitutional capital of Bolivia.")
    r = ConflictReport(conflict_type=CONFLICT_AMBIGUITY, chunk_ids=["c1"],
                       evidence_strength=0.85, decision_case=DECISION_CASE_AMBIGUITY)

    mock_resp = _make_mock_synthesis_response(
        "Sucre is the constitutional capital.",
        sources_cited=["c1"],
        tags=["scope_conflict_preserved"],
    )

    with patch("pipeline.synthesis.answer_synthesizer.openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        synth = AnswerSynthesizer()
        result = synth.synthesize([r], [pos], [c])

    assert isinstance(result.answer, str)
    assert result.decision_case in {1, 2, 3}
    assert isinstance(result.conflict_reports, list)
    assert isinstance(result.conflict_handling_tags, list)
    assert isinstance(result.sources_cited, list)


def test_synthesizer_fallback_on_llm_failure():
    """Make mock raise an exception; assert synthesize() still returns a SynthesisResult."""
    c = _chunk("c1", "Sucre is the constitutional capital of Bolivia.", tier=1, score=0.95)
    pos = _pos("a1", "c1", "Sucre is the constitutional capital of Bolivia.")
    r = ConflictReport(conflict_type=CONFLICT_AMBIGUITY, chunk_ids=["c1"],
                       evidence_strength=0.85, decision_case=DECISION_CASE_AMBIGUITY)

    with patch("pipeline.synthesis.answer_synthesizer.openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("LLM unavailable")
        mock_openai_cls.return_value = mock_client

        synth = AnswerSynthesizer()
        result = synth.synthesize([r], [pos], [c])

    assert isinstance(result, SynthesisResult)
    assert isinstance(result.answer, str)
    assert len(result.answer) > 0
    assert result.decision_case in {1, 2, 3}


# ──────────────────────────────────────────────────────────────────────────────
# Visualizer-related test
# ──────────────────────────────────────────────────────────────────────────────

def test_synthesizer_visualizer_integration_mock():
    """
    Smoke-test: run the full generate_conflict_reports → synthesize pipeline with
    Bolivia-style data (mocked LLM) to verify no crashes end-to-end.
    """
    c1 = _chunk("sucre1", "Sucre is the constitutional capital of Bolivia.", tier=1, score=0.95)
    c2 = _chunk("lapaz1", "La Paz is the administrative capital of Bolivia.", tier=1, score=0.95)
    c3 = _chunk("outlier1", "Santa Cruz is the capital of Bolivia.", tier=4, score=0.15)

    pos1 = _pos("a_sucre", "sucre1", "Sucre is the constitutional capital of Bolivia.")
    pos2 = _pos("a_lapaz", "lapaz1", "La Paz is the administrative capital of Bolivia.")
    pos3 = _pos("a_out", "outlier1", "Santa Cruz is the capital of Bolivia.",
                conf=0.15, status="isolated")

    support_map = {
        pos1.position_text: ["a_sucre"],
        pos2.position_text: ["a_lapaz"],
        pos3.position_text: ["a_out"],
    }

    reports = generate_conflict_reports(
        positions=[pos1, pos2, pos3],
        support_map=support_map,
        isolated_agent_ids=["a_out"],
        chunks=[c1, c2, c3],
        relation_pairs=[],
    )

    assert reports  # non-empty

    mock_resp = _make_mock_synthesis_response(
        "Bolivia has two capitals: Sucre (constitutional) and La Paz (administrative). "
        "Santa Cruz is rejected as an outlier.",
        sources_cited=["sucre1", "lapaz1"],
        tags=["scope_conflict_preserved", "outlier_rejected"],
    )

    with patch("pipeline.synthesis.answer_synthesizer.openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        synth = AnswerSynthesizer()
        result = synth.synthesize(reports, [pos1, pos2, pos3], [c1, c2, c3])

    assert isinstance(result, SynthesisResult)
    assert result.decision_case in {1, 2, 3}
