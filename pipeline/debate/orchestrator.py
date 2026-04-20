"""
Debate Orchestrator — Stage 7.

Manages the full multi-round debate lifecycle:
1. Instantiate one DebateAgent per selected chunk.
2. Collect initial positions (agents see only their own chunk).
3. Run round loop: broadcast all positions, collect responses, update support map.
4. Check early stop after each round.
5. Return DebateResult when stable or MAX_DEBATE_ROUNDS reached.

An optional `emit` callable can be passed to `run()` to receive live events
(used by the SSE streaming endpoint for the frontend visualiser).
"""

from __future__ import annotations

from models.schemas import AgentPosition, Chunk, DebateResult
from pipeline.debate.agent_bank import DebateAgent, _word_overlap
from pipeline.debate.early_stop import should_stop
from pipeline.shared.constants import AGENT_STATUS_ISOLATED, DEBATE_SUPPORT_SIMILARITY_THRESHOLD, MAX_DEBATE_ROUNDS
from pipeline.shared.helpers import cosine_similarity
from pipeline.shared.types import AgentID, EmbedderProtocol, SupportMap


class DebateOrchestrator:
    """Runs the multi-agent debate and returns a DebateResult."""

    def __init__(self, embedder: EmbedderProtocol | None = None) -> None:
        self._embedder = embedder

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pos_to_dict(p: AgentPosition) -> dict:
        return {
            "agent_id": p.agent_id,
            "chunk_id": p.chunk_id,
            "position_text": p.position_text[:220],
            "confidence": p.confidence,
            "status": p.status,
            "reasoning": (p.reasoning or "")[:160],
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, chunks: list[Chunk], emit=None) -> DebateResult:
        """
        Execute the full debate for the given chunks.
        Returns final positions, support map, isolated agent IDs, and round count.

        emit(event_type: str, data: dict) is called at key lifecycle points when provided.
        """
        def _emit(event_type: str, data: dict) -> None:
            if emit:
                emit(event_type, data)

        if not chunks:
            return DebateResult(
                final_positions=[],
                support_map={},
                isolated_agent_ids=[],
                rounds_completed=0,
            )

        agents = self._instantiate_agents(chunks)

        _emit("debate_init", {
            "agent_count": len(agents),
            "agents": [
                {
                    "agent_id": f"agent_{c.id}",
                    "chunk_id": c.id,
                    "excerpt": c.text[:100],
                    "doc_id": c.source_doc_id,
                }
                for c in chunks
            ],
        })

        positions = self._collect_initial_positions(agents)
        _emit("debate_positions", {
            "round": 0,
            "label": "Initial positions",
            "positions": [self._pos_to_dict(p) for p in positions],
            "support_map": {},
            "isolated_ids": [],
        })

        agent_ids = [a._agent_id for a in agents]
        isolated_ids: list[str] = []
        rounds = 0

        for round_idx in range(MAX_DEBATE_ROUNDS):
            support_map = self._build_support_map(positions)
            isolated_ids = self._identify_isolated(support_map, agent_ids)

            # Early stop check: only trigger on the very first iteration if there is
            # nothing to debate (single agent or all agents isolated).  After the first
            # round we apply the normal stability rule so multi-agent debates always
            # get at least one round of position updates.
            if should_stop(positions, isolated_ids) and (round_idx == 0 and len(agent_ids) <= 1):
                break
            if round_idx > 0 and should_stop(positions, isolated_ids):
                break

            positions = self._run_round(agents, positions)
            rounds += 1

            round_support = self._build_support_map(positions)
            round_isolated = self._identify_isolated(round_support, agent_ids)
            _emit("debate_round", {
                "round": rounds,
                "label": f"Round {rounds}",
                "positions": [self._pos_to_dict(p) for p in positions],
                "support_map": {k[:120]: v for k, v in round_support.items()},
                "isolated_ids": round_isolated,
            })

        # Final pass: recompute support map and mark isolated agents in position objects
        support_map = self._build_support_map(positions)
        isolated_ids = self._identify_isolated(support_map, agent_ids)

        _emit("debate_end", {
            "rounds_completed": rounds,
            "isolated_agent_ids": isolated_ids,
        })

        final_positions: list[AgentPosition] = []
        for p in positions:
            if p.agent_id in isolated_ids:
                final_positions.append(AgentPosition(
                    agent_id=p.agent_id,
                    chunk_id=p.chunk_id,
                    position_text=p.position_text,
                    confidence=p.confidence,
                    status=AGENT_STATUS_ISOLATED,
                ))
            else:
                final_positions.append(p)

        return DebateResult(
            final_positions=final_positions,
            support_map=support_map,
            isolated_agent_ids=isolated_ids,
            rounds_completed=rounds,
        )

    def _instantiate_agents(self, chunks: list[Chunk]) -> list[DebateAgent]:
        """Create one isolated DebateAgent per chunk."""
        return [DebateAgent(agent_id=f"agent_{c.id}", chunk=c) for c in chunks]

    def _collect_initial_positions(
        self, agents: list[DebateAgent]
    ) -> list[AgentPosition]:
        """Ask each agent for its initial position."""
        return [agent.generate_initial_position() for agent in agents]

    def _run_round(
        self,
        agents: list[DebateAgent],
        current_positions: list[AgentPosition],
    ) -> list[AgentPosition]:
        """Broadcast current positions to all agents; collect updated responses."""
        position_by_agent = {p.agent_id: p for p in current_positions}
        new_positions: list[AgentPosition] = []
        for agent in agents:
            current_pos = position_by_agent[agent._agent_id]
            new_pos = agent.respond_to_broadcast(current_pos, current_positions)
            new_positions.append(new_pos)
        return new_positions

    def _build_support_map(
        self, positions: list[AgentPosition]
    ) -> SupportMap:
        """
        Build claim_text → [agent_ids] from current positions.

        When an embedder is available, cross-support is determined by cosine
        similarity of position embeddings (threshold DEBATE_SUPPORT_SIMILARITY_THRESHOLD).
        Falls back to lexical Jaccard overlap when no embedder is present.
        """
        text_to_agents: dict[str, list[str]] = {}
        for p in positions:
            text_to_agents.setdefault(p.position_text, []).append(p.agent_id)

        # Build similarity check — batch-encode unique texts when embedder present.
        unique_texts = list(text_to_agents.keys())
        if self._embedder and len(unique_texts) > 1:
            vecs = self._embedder.encode_batch(unique_texts)
            vec_map: dict[str, list[float]] = dict(zip(unique_texts, vecs))

            def _similar(a: str, b: str) -> bool:
                return cosine_similarity(vec_map[a], vec_map[b]) >= DEBATE_SUPPORT_SIMILARITY_THRESHOLD
        else:
            def _similar(a: str, b: str) -> bool:
                return _word_overlap(a, b) >= 0.2

        support_map: SupportMap = {}
        for p in positions:
            if p.position_text in support_map:
                continue
            supporters = list(text_to_agents.get(p.position_text, []))
            for other in positions:
                if other.agent_id not in supporters and other.position_text != p.position_text:
                    if _similar(p.position_text, other.position_text):
                        supporters.append(other.agent_id)
            support_map[p.position_text] = supporters

        return support_map

    def _identify_isolated(
        self, support_map: SupportMap, agent_ids: list[AgentID]
    ) -> list[AgentID]:
        """Return agent IDs that have zero cross-support from any other agent."""
        if len(agent_ids) <= 1:
            return []

        agents_with_crosssupport: set[str] = set()
        for _claim_text, supporters in support_map.items():
            if len(supporters) > 1:
                for aid in supporters:
                    agents_with_crosssupport.add(aid)
        return [aid for aid in agent_ids if aid not in agents_with_crosssupport]
