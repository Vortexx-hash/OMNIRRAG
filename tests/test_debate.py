"""
Phase 4 tests — debate subsystem (agent_bank, orchestrator, early_stop).

All tests that exercise DebateAgent mock the OpenAI client so they never
hit the real API.  Tests that exercise only early_stop or orchestrator
internals (support map, isolation) do not need mocking because the LLM
path is only reached inside DebateAgent methods.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from models.schemas import AgentPosition, DebateResult
from pipeline.debate.agent_bank import DebateAgent
from pipeline.debate.early_stop import is_stable, should_stop
from pipeline.debate.orchestrator import DebateOrchestrator
from pipeline.shared.constants import (
    AGENT_STATUS_ISOLATED,
    AGENT_STATUS_REVISED,
    AGENT_STATUS_STABLE,
    MAX_DEBATE_ROUNDS,
)
from tests.helpers import FakeEmbedder, make_chunk

_embedder = FakeEmbedder()


def _chunk(chunk_id, text, *, tier=2, score=0.8):
    return make_chunk(chunk_id, text, _embedder.encode(text), credibility_score=score, credibility_tier=tier)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _make_mock_llm_response(position_text=None, confidence=0.8, status="stable", reasoning="test"):
    """Returns a mock that makes openai.OpenAI().chat.completions.create() return valid JSON."""
    mock_message = MagicMock()
    if position_text is not None:
        mock_message.content = json.dumps({"position_text": position_text, "reasoning": reasoning})
    else:
        mock_message.content = json.dumps({"confidence": confidence, "status": status, "reasoning": reasoning})
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


# ---------------------------------------------------------------------------
# Agent tests
# ---------------------------------------------------------------------------

@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_agent_initial_position_grounded_in_own_chunk(mock_openai_class):
    """LLM returns a position_text from the chunk; schema fields must be correct."""
    chunk = _chunk("c1", "Metformin is the first-line treatment for type 2 diabetes. It was approved by the FDA in 1994.")

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_mock_llm_response(
        position_text="Metformin is the first-line treatment for type 2 diabetes.",
        reasoning="This is the primary factual claim."
    )

    agent = DebateAgent(agent_id="agent_c1", chunk=chunk)
    pos = agent.generate_initial_position()

    assert pos.agent_id == "agent_c1"
    assert pos.chunk_id == chunk.id
    assert isinstance(pos.position_text, str)
    assert pos.position_text != ""
    assert isinstance(pos.confidence, float)
    assert 0.0 <= pos.confidence <= 1.0
    assert pos.status == AGENT_STATUS_STABLE
    assert isinstance(pos.reasoning, str)


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_agent_cannot_reference_other_chunks(mock_openai_class):
    """After respond_to_broadcast, chunk_id and agent_id must belong to the original chunk."""
    chunk_a = _chunk("ca", "Insulin regulates blood glucose levels in the body.")
    chunk_b = _chunk("cb", "Glucagon raises blood sugar by stimulating glycogen breakdown.")

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # First two calls are generate_initial_position for each agent
    # Third call is respond_to_broadcast for agent_a
    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(position_text="Insulin regulates blood glucose."),
        _make_mock_llm_response(position_text="Glucagon raises blood sugar."),
        _make_mock_llm_response(confidence=0.75, status="stable", reasoning="contested"),
    ]

    agent_a = DebateAgent(agent_id="agent_ca", chunk=chunk_a)
    agent_b = DebateAgent(agent_id="agent_cb", chunk=chunk_b)

    pos_a = agent_a.generate_initial_position()
    pos_b = agent_b.generate_initial_position()

    updated_a = agent_a.respond_to_broadcast(pos_a, [pos_a, pos_b])

    assert updated_a.chunk_id == chunk_a.id
    assert updated_a.agent_id == "agent_ca"


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_agent_revises_status_set_when_position_changes(mock_openai_class):
    """LLM returns status=revised and lower confidence; assert REVISED and confidence < initial."""
    chunk = _chunk("cu", "Xenolith crystallography reveals ancient mantle compositions.", score=0.8)

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(position_text="Xenolith crystallography reveals ancient mantle compositions."),
        _make_mock_llm_response(confidence=0.55, status="revised", reasoning="No support from other agents."),
    ]

    agent = DebateAgent(agent_id="agent_cu", chunk=chunk)
    pos = agent.generate_initial_position()
    initial_confidence = pos.confidence

    other1 = AgentPosition("agent_other1", "ox1", "Metformin treats diabetes effectively.", 0.8, AGENT_STATUS_STABLE)
    other2 = AgentPosition("agent_other2", "ox2", "Insulin regulates pancreatic beta cells.", 0.8, AGENT_STATUS_STABLE)

    updated = agent.respond_to_broadcast(pos, [pos, other1, other2])
    assert updated.status == AGENT_STATUS_REVISED
    assert updated.confidence < initial_confidence


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_agent_stable_status_when_position_unchanged(mock_openai_class):
    """Single agent with no others → respond_to_broadcast returns STABLE without LLM call."""
    chunk = _chunk("cs", "Water is composed of hydrogen and oxygen molecules.")

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.return_value = _make_mock_llm_response(
        position_text="Water is composed of hydrogen and oxygen molecules."
    )

    agent = DebateAgent(agent_id="agent_cs", chunk=chunk)
    pos = agent.generate_initial_position()

    updated = agent.respond_to_broadcast(pos, [pos])  # only self in broadcast
    assert updated.status == AGENT_STATUS_STABLE
    assert updated.confidence == pos.confidence


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_agent_position_text_never_changes(mock_openai_class):
    """Position text must remain identical after respond_to_broadcast."""
    chunk = _chunk("pt", "The earth orbits the sun in approximately 365 days.")

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    initial_text = "The earth orbits the sun in approximately 365 days."
    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(position_text=initial_text),
        _make_mock_llm_response(confidence=0.7, status="revised", reasoning="some change"),
    ]

    agent = DebateAgent(agent_id="agent_pt", chunk=chunk)
    pos = agent.generate_initial_position()
    original_text = pos.position_text

    other = AgentPosition("agent_other", "ox", "Completely different unrelated claim.", 0.8, AGENT_STATUS_STABLE)
    updated = agent.respond_to_broadcast(pos, [pos, other])

    assert updated.position_text == original_text


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_agent_confidence_bounded_in_range(mock_openai_class):
    """LLM returning out-of-range confidence triggers fallback; result stays in [0, 1]."""
    chunk = _chunk("cb2", "Photons travel at the speed of light in a vacuum.")

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    # Return invalid confidence (1.5) — should trigger fallback
    invalid_response = MagicMock()
    invalid_response.choices = [MagicMock()]
    invalid_response.choices[0].message.content = json.dumps(
        {"confidence": 1.5, "status": "stable", "reasoning": "out of range"}
    )

    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(position_text="Photons travel at the speed of light."),
        invalid_response,
    ]

    agent = DebateAgent(agent_id="agent_cb2", chunk=chunk)
    pos = agent.generate_initial_position()

    other = AgentPosition("agent_x", "ox", "Different claim about gravity.", 0.8, AGENT_STATUS_STABLE)
    updated = agent.respond_to_broadcast(pos, [pos, other])

    assert 0.0 <= updated.confidence <= 1.0


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_agent_reasoning_field_populated(mock_openai_class):
    """LLM returns reasoning string; it must be present in the returned AgentPosition."""
    chunk = _chunk("rr", "Vaccines have eradicated smallpox globally.")

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(position_text="Vaccines have eradicated smallpox globally.", reasoning="Primary claim of the text."),
        _make_mock_llm_response(confidence=0.85, status="stable", reasoning="Supported by another agent."),
    ]

    agent = DebateAgent(agent_id="agent_rr", chunk=chunk)
    pos = agent.generate_initial_position()
    assert pos.reasoning != ""

    other = AgentPosition("agent_y", "oy", "Vaccines eliminate infectious diseases.", 0.9, AGENT_STATUS_STABLE)
    updated = agent.respond_to_broadcast(pos, [pos, other])
    assert updated.reasoning != ""


# ---------------------------------------------------------------------------
# Early Stop tests (no mocking needed — pure logic)
# ---------------------------------------------------------------------------

def test_early_stop_triggers_when_all_non_isolated_stable():
    pos_a = AgentPosition("a1", "c1", "claim one", 0.8, AGENT_STATUS_STABLE)
    pos_b = AgentPosition("a2", "c2", "claim two", 0.8, AGENT_STATUS_STABLE)
    assert should_stop([pos_a, pos_b], []) is True


def test_early_stop_not_triggered_with_unstable_agents():
    pos_a = AgentPosition("a1", "c1", "claim one", 0.8, AGENT_STATUS_STABLE)
    pos_b = AgentPosition("a2", "c2", "claim two", 0.75, AGENT_STATUS_REVISED)
    assert should_stop([pos_a, pos_b], []) is False


def test_isolated_agents_do_not_block_early_stop():
    pos_a = AgentPosition("a1", "c1", "claim one", 0.8, AGENT_STATUS_STABLE)
    pos_b = AgentPosition("a2", "c2", "fringe claim", 0.55, AGENT_STATUS_ISOLATED)
    # a2 is isolated; a1 is stable → should stop
    assert should_stop([pos_a, pos_b], ["a2"]) is True


# ---------------------------------------------------------------------------
# Orchestrator tests (mock LLM via patch)
# ---------------------------------------------------------------------------

@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_orchestrator_instantiates_one_agent_per_chunk(mock_openai_class):
    """Three chunks → three agents → three final positions."""
    chunks = [
        _chunk("x1", "Diabetes is managed with metformin as first-line therapy."),
        _chunk("x2", "Insulin therapy is used for type 1 diabetes management."),
        _chunk("x3", "Blood glucose monitoring is essential for diabetes control."),
    ]

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Each agent's generate_initial_position call gets a unique position_text
    initial_responses = [
        _make_mock_llm_response(position_text=c.text[:60]) for c in chunks
    ]
    # Subsequent respond_to_broadcast calls all return stable
    broadcast_responses = [
        _make_mock_llm_response(confidence=0.8, status="stable", reasoning="ok")
        for _ in range(30)  # plenty for multiple rounds
    ]
    mock_client.chat.completions.create.side_effect = initial_responses + broadcast_responses

    orchestrator = DebateOrchestrator()
    result = orchestrator.run(chunks)
    assert len(result.final_positions) == 3


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_orchestrator_builds_support_map_from_positions(mock_openai_class):
    """Two chunks with identical text → support_map has at least one entry."""
    text = "Metformin is the standard first-line treatment for type 2 diabetes."
    chunks = [_chunk("s1", text), _chunk("s2", text)]

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(position_text=text),
        _make_mock_llm_response(position_text=text),
    ] + [_make_mock_llm_response(confidence=0.8, status="stable", reasoning="ok")] * 20

    orchestrator = DebateOrchestrator()
    result = orchestrator.run(chunks)

    assert isinstance(result.support_map, dict)
    assert len(result.support_map) >= 1


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_orchestrator_identifies_isolated_agents(mock_openai_class):
    """Agent with a completely different position should be isolated."""
    chunks = [
        _chunk("m1", "Diabetes treatment with metformin reduces glucose effectively."),
        _chunk("m2", "Metformin is prescribed for diabetes glucose management therapy."),
        _chunk("m3", "Glucose control via metformin is standard diabetes treatment."),
        _chunk("r1", "Ancient roman gladiators fought in the colosseum arena battles."),
    ]

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Give each agent a very distinct position text to force isolation of r1
    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(position_text="Diabetes treatment with metformin reduces glucose."),
        _make_mock_llm_response(position_text="Metformin is prescribed for diabetes glucose management."),
        _make_mock_llm_response(position_text="Glucose control via metformin is standard treatment."),
        _make_mock_llm_response(position_text="Ancient roman gladiators fought in the colosseum."),
    ] + [_make_mock_llm_response(confidence=0.8, status="stable", reasoning="ok")] * 40

    orchestrator = DebateOrchestrator()
    result = orchestrator.run(chunks)

    assert "agent_r1" in result.isolated_agent_ids


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_orchestrator_respects_max_debate_rounds_cap(mock_openai_class):
    """rounds_completed must never exceed MAX_DEBATE_ROUNDS."""
    chunks = [
        _chunk("r1", "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda."),
        _chunk("r2", "Omega psi chi phi upsilon tau sigma rho pi xi nu mu."),
    ]

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(position_text="Alpha beta gamma delta."),
        _make_mock_llm_response(position_text="Omega psi chi phi."),
    ] + [_make_mock_llm_response(confidence=0.8, status="revised", reasoning="keep changing")] * 100

    orchestrator = DebateOrchestrator()
    result = orchestrator.run(chunks)
    assert result.rounds_completed <= MAX_DEBATE_ROUNDS


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_orchestrator_returns_debate_result_with_all_fields(mock_openai_class):
    """DebateResult must have all required fields with correct types."""
    chunks = [
        _chunk("f1", "Photosynthesis converts light energy into chemical energy in plants."),
        _chunk("f2", "Plants use chlorophyll to absorb light for photosynthesis process."),
    ]

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(position_text="Photosynthesis converts light into chemical energy."),
        _make_mock_llm_response(position_text="Plants use chlorophyll to absorb light."),
    ] + [_make_mock_llm_response(confidence=0.8, status="stable", reasoning="ok")] * 20

    orchestrator = DebateOrchestrator()
    result = orchestrator.run(chunks)

    assert isinstance(result, DebateResult)
    assert isinstance(result.final_positions, list)
    assert isinstance(result.support_map, dict)
    assert isinstance(result.isolated_agent_ids, list)
    assert isinstance(result.rounds_completed, int)
    assert result.rounds_completed >= 0


# ---------------------------------------------------------------------------
# Challenging integration tests
# ---------------------------------------------------------------------------

def test_debate_single_chunk_terminates_immediately():
    """
    Single chunk → no debate → rounds_completed == 0.
    No LLM mock needed since respond_to_broadcast is never called for a solo agent.
    """
    with patch("pipeline.debate.agent_bank.openai.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_llm_response(
            position_text="The mitochondria is the powerhouse of the cell."
        )

        chunks = [_chunk("solo", "The mitochondria is the powerhouse of the cell.")]
        orchestrator = DebateOrchestrator()
        result = orchestrator.run(chunks)

    assert result.rounds_completed == 0
    assert len(result.final_positions) == 1
    assert result.final_positions[0].status == AGENT_STATUS_STABLE
    assert len(result.isolated_agent_ids) == 0


@patch("pipeline.debate.agent_bank.openai.OpenAI")
def test_debate_result_schema_compliance(mock_openai_class):
    """
    Run debate with 2 chunks and validate all AgentPosition fields have correct types.
    """
    chunks = [
        _chunk("sc1", "Climate change is driven by greenhouse gas emissions from human activity.", score=0.85),
        _chunk("sc2", "Rising global temperatures are caused by CO2 and methane emissions.", score=0.80),
    ]

    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        _make_mock_llm_response(
            position_text="Climate change is driven by greenhouse gas emissions.",
            reasoning="Core factual claim."
        ),
        _make_mock_llm_response(
            position_text="Rising global temperatures are caused by CO2 emissions.",
            reasoning="Core factual claim."
        ),
        _make_mock_llm_response(confidence=0.88, status="stable", reasoning="Supported by similar claim."),
        _make_mock_llm_response(confidence=0.82, status="stable", reasoning="Supported by similar claim."),
    ] + [_make_mock_llm_response(confidence=0.85, status="stable", reasoning="converged")] * 20

    orchestrator = DebateOrchestrator()
    result = orchestrator.run(chunks)

    valid_statuses = {AGENT_STATUS_STABLE, AGENT_STATUS_REVISED, AGENT_STATUS_ISOLATED}

    for ap in result.final_positions:
        assert isinstance(ap.agent_id, str), f"agent_id must be str, got {type(ap.agent_id)}"
        assert isinstance(ap.chunk_id, str), f"chunk_id must be str, got {type(ap.chunk_id)}"
        assert isinstance(ap.position_text, str), f"position_text must be str, got {type(ap.position_text)}"
        assert isinstance(ap.confidence, float), f"confidence must be float, got {type(ap.confidence)}"
        assert 0.0 <= ap.confidence <= 1.0, f"confidence {ap.confidence} out of [0, 1]"
        assert ap.status in valid_statuses, f"status {ap.status!r} not in valid set"
        assert isinstance(ap.reasoning, str), f"reasoning must be str, got {type(ap.reasoning)}"
