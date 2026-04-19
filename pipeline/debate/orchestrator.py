"""
Debate Orchestrator — Stage 7.

Manages the full multi-round debate lifecycle:
1. Instantiate one DebateAgent per selected chunk.
2. Collect initial positions (agents see only their own chunk).
3. Run round loop: broadcast all positions, collect responses, update support map.
4. Check early stop after each round.
5. Return DebateResult when stable or MAX_DEBATE_ROUNDS reached.
"""

from __future__ import annotations

from models.schemas import AgentPosition, Chunk, DebateResult
from pipeline.debate.agent_bank import DebateAgent, _word_overlap
from pipeline.debate.early_stop import should_stop
from pipeline.shared.constants import AGENT_STATUS_ISOLATED, MAX_DEBATE_ROUNDS
from pipeline.shared.types import AgentID, SupportMap


class DebateOrchestrator:
    """Runs the multi-agent debate and returns a DebateResult."""

    def run(self, chunks: list[Chunk]) -> DebateResult:
        """
        Execute the full debate for the given chunks.
        Returns final positions, support map, isolated agent IDs, and round count.
        """
        if not chunks:
            return DebateResult(
                final_positions=[],
                support_map={},
                isolated_agent_ids=[],
                rounds_completed=0,
            )

        agents = self._instantiate_agents(chunks)
        positions = self._collect_initial_positions(agents)
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

        # Final pass: recompute support map and mark isolated agents in position objects
        support_map = self._build_support_map(positions)
        isolated_ids = self._identify_isolated(support_map, agent_ids)

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
        Agents whose position_text matches (or endorses) a claim are counted as supporters.

        Duplicate position_texts are grouped; cross-overlap above threshold adds further support.
        """
        # Collect all agents per unique text first (self-support)
        text_to_agents: dict[str, list[str]] = {}
        for p in positions:
            text_to_agents.setdefault(p.position_text, []).append(p.agent_id)

        support_map: SupportMap = {}
        for p in positions:
            if p.position_text in support_map:
                # Already computed for this text (duplicate position_text)
                continue
            supporters = list(text_to_agents.get(p.position_text, []))  # same text = self-support
            for other in positions:
                if other.agent_id not in supporters and other.position_text != p.position_text:
                    if _word_overlap(p.position_text, other.position_text) >= 0.2:
                        supporters.append(other.agent_id)
            support_map[p.position_text] = supporters

        return support_map

    def _identify_isolated(
        self, support_map: SupportMap, agent_ids: list[AgentID]
    ) -> list[AgentID]:
        """
        Return agent IDs that have zero cross-support from any other agent.

        An agent is isolated if it does not appear in any support_map entry
        that contains at least one other agent (i.e., it has no cross-support).
        """
        # A single agent has no peers to provide cross-support; it is not isolated.
        if len(agent_ids) <= 1:
            return []

        agents_with_crosssupport: set[str] = set()
        for _claim_text, supporters in support_map.items():
            if len(supporters) > 1:
                for aid in supporters:
                    agents_with_crosssupport.add(aid)
        return [aid for aid in agent_ids if aid not in agents_with_crosssupport]
