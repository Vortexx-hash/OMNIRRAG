# Subagent: debate-system

## Description
Implements the multi-agent debate subsystem (Stages 6–7) of the conflict-aware
RAG pipeline. This subagent manages agent instantiation, round-loop orchestration,
support map maintenance, and early stop logic.

## Responsibilities
- `pipeline/debate/agent_bank.py` — debate agent abstraction and agent-bank creation
  logic: isolated initialization, initial position generation, and round-level
  revision behavior
- `pipeline/debate/orchestrator.py` — round loop, broadcast, support map,
  early stop invocation, DebateResult assembly
- `pipeline/debate/early_stop.py` — stability predicate and closed-evidence
  early stop condition

## Inputs
- `list[Chunk]` — DPP-selected chunks (one agent instantiated per chunk)
- Debate config from `pipeline/shared/constants.py` (e.g. `MAX_DEBATE_ROUNDS`)

## Outputs
- `DebateResult`:
  - `final_positions: list[AgentPosition]`
  - `support_map: dict[str, list[str]]`  (claim_text → [agent_ids])
  - `isolated_agent_ids: list[str]`
  - `rounds_completed: int`

## When to Delegate
Delegate to this subagent when:
- Starting Phase 4 implementation
- Modifying any file under `pipeline/debate/`
- Changing round logic, broadcast protocol, or early stop conditions
- Debugging agent isolation or support map construction

## Must Not
- Allow agents to read other agents' source chunks at any point —
  only positions are broadcast during rounds
- Modify `models/schemas.py` — propose changes to main agent
- Import from `pipeline/relations/`, `pipeline/synthesis/`, or `pipeline/selection/`
- Implement more than `MAX_DEBATE_ROUNDS` rounds without explicit instruction
  (early stop should terminate the loop first)
- Implement conflict classification — that belongs in `pipeline/synthesis/conflict_report.py`
- Use credibility scores as a hard gate to suppress agent participation once a
  chunk has been selected for debate

## Context to Load Before Starting
Load from SKILLS.md:
- "Canonical Data Structures"
- "Debate Early Stop Predicate"
