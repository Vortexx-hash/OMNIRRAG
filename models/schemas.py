"""
Canonical data structures for the conflict-aware RAG pipeline.

This file is the single source of truth for all schemas. Do not define
data structures inline in other modules. All changes must be made here
and propagated to callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A document fragment stored in the vector DB at upload time."""

    id: str
    source_doc_id: str
    text: str
    embedding: list[float]
    credibility_score: float  # 0.1–1.0, assigned at upload from source metadata
    credibility_tier: int     # 1–4, derived from source type


@dataclass
class Query:
    """A normalised user query with extracted semantics and a dense vector."""

    raw: str
    normalized: str
    entities: list[dict]  # [{"text": str, "label": str}], e.g. {"text": "Bolivia", "label": "COUNTRY"}
    property: str         # e.g. "capital"
    intent: str           # e.g. "factual lookup"
    vector: list[float]


@dataclass
class RelationPair:
    """
    Pairwise relationship between two chunks.

    Populated by the Relation Builder (Stage 3).
    is_scope_difference=True when a surface NLI contradiction is resolved
    by differing scope qualifiers (see SKILLS.md: NLI Scope Qualifier Rule).
    """

    chunk_a_id: str
    chunk_b_id: str
    similarity_score: float
    nli_label: str             # "contradiction" | "no-contradiction"
    entity_overlap: list[str]  # shared entity surface forms
    scope_qualifiers: list[str]
    is_scope_difference: bool  # True → not a real contradiction, different roles


@dataclass
class DPPResult:
    """Output of the DPP Selector (Stage 5)."""

    selected_ids: list[str]
    dropped_ids: list[str]
    drop_reasons: dict[str, str]  # chunk_id → "redundant" | "irrelevant"


@dataclass
class AgentPosition:
    """
    A single debate agent's current stance.

    status:
      "stable"   — position unchanged from previous round
      "revised"  — position updated this round
      "isolated" — zero support from any other agent across all rounds

    reasoning: LLM-generated explanation for the confidence update (empty when rule-based).
    """

    agent_id: str
    chunk_id: str
    position_text: str
    confidence: float
    status: str
    reasoning: str = ""


@dataclass
class DebateResult:
    """Aggregate output of the Debate Orchestrator (Stage 7)."""

    final_positions: list[AgentPosition]
    support_map: dict[str, list[str]]  # claim_text → [agent_ids]
    isolated_agent_ids: list[str]
    rounds_completed: int


@dataclass
class SynthesisResult:
    """Output of the Final Answer Synthesizer (Stage 9)."""

    answer: str                        # natural language answer
    decision_case: int                 # 1 | 2 | 3
    conflict_reports: list["ConflictReport"]
    conflict_handling_tags: list[str]  # e.g. ["scope_conflict_preserved", "outlier_rejected"]
    sources_cited: list[str]           # chunk_ids referenced in the answer


@dataclass
class ConflictReport:
    """
    Typed classification of a claim cluster produced by the Conflict Report Generator.

    conflict_type:
      "ambiguity"           — multiple valid answers with scope qualifiers (→ Case 1)
      "outlier"             — rejected misinformation, zero debate support
      "oversimplification"  — factually incomplete but not wrong, downweighted
      "noise"               — irrelevant to the query property

    decision_case:
      1 — Ambiguity: present all surviving answers with qualifiers
      2 — Strong winner: return single best-supported answer
      3 — Unresolved: insufficient evidence to decide
    """

    conflict_type: str
    chunk_ids: list[str]
    evidence_strength: float
    decision_case: int
    has_scope_qualifier: bool = False  # True when position_text contains a scope qualifier
