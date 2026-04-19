"""
Conflict Report Generator — Stage 8.

Classifies the debate output into typed conflict reports, one per claim cluster.
Determines the decision case for the final answer synthesizer.

Classification priority (applied in order):
  1. noise             — chunk does not address the query property
  2. outlier           — contradicted by all, zero support, no qualifier
  3. oversimplification — factually incomplete, no qualifier, not outright wrong
  4. ambiguity         — multiple surviving claims with different scope qualifiers

See SKILLS.md: Conflict Classification Rules.
"""

from __future__ import annotations

from models.schemas import AgentPosition, Chunk, ConflictReport, RelationPair
from pipeline.shared.constants import (
    AGENT_STATUS_ISOLATED,
    CONFLICT_AMBIGUITY,
    CONFLICT_NOISE,
    CONFLICT_OUTLIER,
    CONFLICT_OVERSIMPLIFICATION,
    DECISION_CASE_AMBIGUITY,
    DECISION_CASE_STRONG_WINNER,
    DECISION_CASE_UNRESOLVED,
    SCOPE_QUALIFIERS,
)
from pipeline.shared.types import SupportMap


def _has_scope_qualifier(text: str) -> bool:
    """Return True if any scope qualifier word/phrase appears in text (case-insensitive)."""
    text_lower = text.lower()
    return any(q in text_lower for q in SCOPE_QUALIFIERS)


def _compute_evidence_strength(
    cluster_agents: list[AgentPosition],
    chunk_map: dict[str, Chunk],
) -> float:
    """
    evidence_strength = mean(credibility_score) * mean(confidence of non-isolated agents)
    """
    if not cluster_agents:
        return 0.0

    cred_scores = [
        chunk_map[p.chunk_id].credibility_score
        for p in cluster_agents
        if p.chunk_id in chunk_map
    ]
    mean_cred = sum(cred_scores) / len(cred_scores) if cred_scores else 0.0

    non_isolated = [p for p in cluster_agents if p.status != AGENT_STATUS_ISOLATED]
    if non_isolated:
        mean_conf = sum(p.confidence for p in non_isolated) / len(non_isolated)
    else:
        # All isolated → use overall mean confidence (low by design)
        mean_conf = sum(p.confidence for p in cluster_agents) / len(cluster_agents)

    return mean_cred * mean_conf


def _classify_cluster(
    cluster_agents: list[AgentPosition],
    all_positions: list[AgentPosition],
    support_map: SupportMap,
    isolated_agent_ids: list[str],
    chunk_map: dict[str, Chunk],
    surviving_count: int,
) -> str:
    """
    Return the conflict_type string for a single claim cluster.

    Priority order:
      1. NOISE
      2. OUTLIER
      3. OVERSIMPLIFICATION
      4. AMBIGUITY (default)
    """
    cluster_text = cluster_agents[0].position_text if cluster_agents else ""

    # ── 1. NOISE ──────────────────────────────────────────────────────────────
    # All agents in cluster have credibility_tier == 4 AND zero cross-support
    # from tier 1-3 agents.
    # Note: if all agents are also isolated, we skip NOISE and fall through to
    # OUTLIER (isolated+tier4 is an outlier, not mere noise).
    all_tier4 = all(
        chunk_map.get(p.chunk_id) is not None
        and chunk_map[p.chunk_id].credibility_tier == 4
        for p in cluster_agents
    )
    all_isolated_already = all(p.agent_id in isolated_agent_ids for p in cluster_agents)
    if all_tier4 and not all_isolated_already:
        cluster_ids = {p.chunk_id for p in cluster_agents}
        cross_supporters = [
            p for p in all_positions
            if p.chunk_id not in cluster_ids
            and p.chunk_id in chunk_map
            and chunk_map[p.chunk_id].credibility_tier in (1, 2, 3)
            and (
                p.position_text == cluster_text
                or (
                    cluster_text in support_map
                    and p.agent_id in support_map[cluster_text]
                )
            )
        ]
        if not cross_supporters:
            return CONFLICT_NOISE

    # ── 1b. TIER-4 GATE ──────────────────────────────────────────────────────
    # All-tier-4 clusters with no scope qualifier are oversimplification /
    # outlier regardless of debate confidence.  The LLM debate agent can
    # inflate confidence for low-credibility claims; credibility tier is an
    # objective metadata signal that overrides it.
    if all_tier4 and not _has_scope_qualifier(cluster_text):
        _all_iso = all(p.agent_id in isolated_agent_ids for p in cluster_agents)
        if _all_iso:
            return CONFLICT_OUTLIER
        return CONFLICT_OVERSIMPLIFICATION if surviving_count > 0 else CONFLICT_OUTLIER

    # ── 2. OUTLIER ────────────────────────────────────────────────────────────
    # ALL agents in cluster are isolated AND no scope qualifier AND mean
    # credibility_score < 0.5
    all_isolated = all(p.agent_id in isolated_agent_ids for p in cluster_agents)
    if all_isolated:
        has_qualifier = _has_scope_qualifier(cluster_text)
        cred_scores = [
            chunk_map[p.chunk_id].credibility_score
            for p in cluster_agents
            if p.chunk_id in chunk_map
        ]
        mean_cred = sum(cred_scores) / len(cred_scores) if cred_scores else 0.0
        if not has_qualifier and mean_cred < 0.5:
            return CONFLICT_OUTLIER

    # ── 3. OVERSIMPLIFICATION ─────────────────────────────────────────────────
    # Has ≥1 non-isolated agent BUT mean confidence < 0.6 AND no scope qualifier
    # AND surviving_count > 0 (another non-outlier cluster exists with more evidence)
    non_isolated = [p for p in cluster_agents if p.agent_id not in isolated_agent_ids]
    if non_isolated:
        mean_conf = sum(p.confidence for p in non_isolated) / len(non_isolated)
        has_qualifier = _has_scope_qualifier(cluster_text)
        if mean_conf < 0.6 and not has_qualifier and surviving_count > 0:
            return CONFLICT_OVERSIMPLIFICATION

    # ── 4. AMBIGUITY (default) ────────────────────────────────────────────────
    return CONFLICT_AMBIGUITY


def generate_conflict_reports(
    positions: list[AgentPosition],
    support_map: SupportMap,
    isolated_agent_ids: list[str],
    chunks: list[Chunk],
    relation_pairs: list[RelationPair],
) -> list[ConflictReport]:
    """
    Produce one ConflictReport per claim cluster.
    Applies the classification priority from SKILLS.md.
    """
    if not positions:
        return []

    chunk_map: dict[str, Chunk] = {c.id: c for c in chunks}

    # ── Step 1: Build position clusters ──────────────────────────────────────
    # Group by identical position_text
    cluster_map: dict[str, list[AgentPosition]] = {}
    for pos in positions:
        cluster_map.setdefault(pos.position_text, []).append(pos)

    # Handle scope-difference pairs from relation_pairs: merge clusters whose
    # chunk pairs have is_scope_difference=True into ambiguity groups.
    # We track which cluster texts are "scope-linked" — they will both be
    # forced to AMBIGUITY later regardless of their individual classification.
    scope_linked_texts: set[str] = set()
    if relation_pairs:
        # Build chunk_id → position_text mapping
        chunk_to_text: dict[str, str] = {p.chunk_id: p.position_text for p in positions}
        for rp in relation_pairs:
            if rp.is_scope_difference:
                text_a = chunk_to_text.get(rp.chunk_a_id)
                text_b = chunk_to_text.get(rp.chunk_b_id)
                if text_a:
                    scope_linked_texts.add(text_a)
                if text_b:
                    scope_linked_texts.add(text_b)

    # ── Step 2: Classify each cluster (two-pass to handle oversimplification) ─
    # First pass: count clusters that are NOT outlier/noise (surviving_count)
    # We need to classify once to estimate surviving_count, then reclassify.

    # Quick pre-pass to determine which clusters look like definite
    # outliers/noise (so surviving_count is accurate for oversimplification check)
    pre_reports: list[tuple[str, list[AgentPosition], str]] = []

    for text, agents in cluster_map.items():
        conflict_type = _classify_cluster(
            cluster_agents=agents,
            all_positions=positions,
            support_map=support_map,
            isolated_agent_ids=isolated_agent_ids,
            chunk_map=chunk_map,
            surviving_count=1,  # placeholder — will be replaced in real pass
        )
        pre_reports.append((text, agents, conflict_type))

    # Count how many clusters are "surviving" (not outlier/noise) in pre-pass
    initial_surviving = sum(
        1 for _, _, ct in pre_reports
        if ct not in (CONFLICT_OUTLIER, CONFLICT_NOISE)
    )

    # Real pass: use accurate surviving_count for oversimplification gate
    reports: list[ConflictReport] = []
    surviving_so_far = 0

    for text, agents in cluster_map.items():
        # Force scope-linked clusters to ambiguity
        if text in scope_linked_texts:
            conflict_type = CONFLICT_AMBIGUITY
        else:
            # For oversimplification, surviving_count = number of clusters that
            # are NOT outlier/noise (from pre-pass), minus this cluster itself.
            # We subtract 1 from initial_surviving for the current cluster, so
            # "another surviving cluster exists" iff surviving_count > 0.
            pre_type = next(ct for t, _, ct in pre_reports if t == text)
            other_survivors = initial_surviving - (
                1 if pre_type not in (CONFLICT_OUTLIER, CONFLICT_NOISE) else 0
            )
            conflict_type = _classify_cluster(
                cluster_agents=agents,
                all_positions=positions,
                support_map=support_map,
                isolated_agent_ids=isolated_agent_ids,
                chunk_map=chunk_map,
                surviving_count=other_survivors,
            )

        # Map conflict_type to per-cluster decision_case
        if conflict_type in (CONFLICT_OUTLIER, CONFLICT_NOISE):
            cluster_decision_case = DECISION_CASE_STRONG_WINNER
        elif conflict_type == CONFLICT_OVERSIMPLIFICATION:
            cluster_decision_case = DECISION_CASE_STRONG_WINNER
        else:
            cluster_decision_case = DECISION_CASE_AMBIGUITY

        evidence_strength = _compute_evidence_strength(agents, chunk_map)
        cluster_text = agents[0].position_text if agents else ""

        reports.append(ConflictReport(
            conflict_type=conflict_type,
            chunk_ids=[p.chunk_id for p in agents],
            evidence_strength=evidence_strength,
            decision_case=cluster_decision_case,
            has_scope_qualifier=_has_scope_qualifier(cluster_text),
        ))

        if conflict_type not in (CONFLICT_OUTLIER, CONFLICT_NOISE):
            surviving_so_far += 1

    return reports


def determine_decision_case(reports: list[ConflictReport]) -> int:
    """
    Return the overall decision case (1 | 2 | 3) based on the set of reports.

    Case 1 — Ambiguity: ≥2 surviving claims with scope qualifiers
    Case 2 — Strong winner: exactly 1 dominant claim
    Case 3 — Unresolved: no majority, no isolated outlier
    """
    surviving = [
        r for r in reports
        if r.conflict_type not in (CONFLICT_OUTLIER, CONFLICT_NOISE)
    ]

    if len(surviving) == 0:
        return DECISION_CASE_UNRESOLVED

    if len(surviving) == 1:
        return DECISION_CASE_STRONG_WINNER

    # ≥2 surviving claims — true ambiguity only if at least one surviving claim
    # carries a known scope qualifier (e.g. "constitutional" vs "administrative").
    # Without scope qualifiers the competing claims represent an unresolved
    # conflict, not a multi-faceted answer.
    has_scope = any(r.has_scope_qualifier for r in surviving)
    if has_scope:
        return DECISION_CASE_AMBIGUITY

    return DECISION_CASE_UNRESOLVED
