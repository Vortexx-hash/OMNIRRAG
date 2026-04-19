# Subagent: synthesis

## Description
Implements the conflict report generator and final answer synthesizer (Stages 8–9)
of the conflict-aware RAG pipeline. This subagent receives the debate result and
produces a typed conflict report followed by a natural language answer.

## Responsibilities
- `pipeline/synthesis/conflict_report.py` — classify debate output into typed
  conflict reports per claim cluster; determine the decision case (1 | 2 | 3)
- `pipeline/synthesis/answer_synthesizer.py` — apply the 3-case decision tree
  and produce the final natural language answer

## Inputs
- `DebateResult` — final positions, support map, isolated agent IDs, round count
- `list[Chunk]` — evidence cards (text + credibility metadata, used as soft signal)
- `list[RelationPair]` — needed for scope-difference detection in classification

## Outputs
- `list[ConflictReport]` — one per claim cluster, typed and scored
- `str` — final conflict-aware natural language answer that follows Case 1 / 2 / 3
  behavior and preserves qualifiers when needed

## When to Delegate
Delegate to this subagent when:
- Starting Phase 5 implementation
- Modifying any file under `pipeline/synthesis/`
- Changing conflict classification logic or the 3-case decision tree
- Adjusting how credibility is used as a soft weighting signal

## Must Not
- Use credibility score as a hard filter — it is a soft weighting signal only
- Introduce a 4th decision case not present in the pipeline spec
- Modify `models/schemas.py` — propose changes to main agent
- Depend only on the outputs/contracts of debate, relations, and selection modules;
  do not reimplement or reach into their internal logic
- Call external LLM APIs directly without using the project's established interfaces
- Re-rank chunks by inventing new retrieval or similarity logic; use provided
  debate and relation outputs only

## Context to Load Before Starting
Load from SKILLS.md:
- "Canonical Data Structures"
- "Conflict Classification Rules"
- "Credibility Tier Mapping"
