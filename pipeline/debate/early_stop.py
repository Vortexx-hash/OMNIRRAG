"""
Debate early stop predicate.

Stop conditions (both must be true):
1. All non-isolated agents have status == "stable" (no revision in last round).
2. The debate operates on closed evidence — agents cannot acquire new facts after
   initialisation. Once all non-isolated agents are stable, no further revision
   is possible and the debate should terminate.

See SKILLS.md: Debate Early Stop Predicate.
"""

from __future__ import annotations

from models.schemas import AgentPosition
from pipeline.shared.constants import AGENT_STATUS_ISOLATED, AGENT_STATUS_STABLE


def is_stable(positions: list[AgentPosition]) -> bool:
    """
    Return True if all non-isolated agents have status AGENT_STATUS_STABLE.
    Isolated agents are excluded from the stability check.
    """
    non_isolated = [p for p in positions if p.status != AGENT_STATUS_ISOLATED]
    if not non_isolated:
        return True
    return all(p.status == AGENT_STATUS_STABLE for p in non_isolated)


def should_stop(
    positions: list[AgentPosition],
    isolated_agent_ids: list[str],
) -> bool:
    """
    Return True when the debate should terminate early.

    Conditions:
    - All non-isolated agents are stable (no revision occurred last round)
    - Evidence is closed: agents are initialised with fixed chunks and cannot
      acquire new information, so stability implies no further change is possible.
    """
    active = [p for p in positions if p.agent_id not in isolated_agent_ids]
    if not active:
        return True
    return all(p.status == AGENT_STATUS_STABLE for p in active)
