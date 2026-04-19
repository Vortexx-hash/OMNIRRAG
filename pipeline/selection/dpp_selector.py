"""
DPP Selector — Stage 5.

Selects a diverse, non-redundant subset of retrieved chunks that preserves
at least one representative from each conflict cluster.

Scoring function (per SKILLS.md):
    Score(S) = Relevance(S)
             + β · Diversity(S)
             − Redundancy(S)
             − γ · ConflictPenalty(S)

  Relevance(S)       = mean query-relevance score of selected chunks
  β · Diversity(S)   = β × (1 − mean pairwise similarity within S)
  Redundancy(S)      = sum of pairwise similarities above the threshold within S
  ConflictPenalty(S) = count of conflict clusters with zero representation in S

Hard constraint (enforced by seeding, not just by the score):
  ∀ conflict cluster C,  |S ∩ C| ≥ 1

Implementation note — two-phase greedy:
  Phase 1: seed S with the highest-relevance chunk from each conflict cluster.
           This guarantees the hard constraint regardless of γ magnitude.
  Phase 2: greedily add the remaining chunk with the highest marginal score
           until max_chunks is reached.
  Drop reasons are assigned post-hoc: "redundant" if any selected chunk
  exceeds the similarity threshold with the dropped chunk; "irrelevant" otherwise.

β and γ are configurable; defaults come from pipeline/shared/constants.py.
"""

from __future__ import annotations

from collections import defaultdict

from models.schemas import Chunk, DPPResult, RelationPair
from pipeline.shared.constants import (
    DPP_BETA_DEFAULT,
    DPP_GAMMA_DEFAULT,
    DROP_REASON_IRRELEVANT,
    DROP_REASON_REDUNDANT,
    NLI_CONTRADICTION,
    SIMILARITY_REDUNDANCY_THRESHOLD,
)
from pipeline.shared.types import RelevanceScores, SimilarityMatrix


class DPPSelector:
    """Selects a diverse, conflict-preserving chunk subset via greedy DPP scoring.

    Parameters
    ----------
    beta:
        Diversity weight.  Higher values push the selector toward less similar pairs.
    gamma:
        Conflict-cluster penalty weight in the score function (the hard seeding
        constraint is always active regardless of this value).
    redundancy_threshold:
        Pairwise similarity above which two chunks are penalised as redundant.
    max_chunks:
        Upper bound on the number of selected chunks.  ``None`` means no cap
        (all chunks may be selected if the score supports it).
    """

    def __init__(
        self,
        beta: float = DPP_BETA_DEFAULT,
        gamma: float = DPP_GAMMA_DEFAULT,
        redundancy_threshold: float = SIMILARITY_REDUNDANCY_THRESHOLD,
        max_chunks: int | None = None,
    ) -> None:
        self._beta = beta
        self._gamma = gamma
        self._redundancy_threshold = redundancy_threshold
        self._max_chunks = max_chunks

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def select(
        self,
        chunks: list[Chunk],
        relation_pairs: list[RelationPair],
        relevance_scores: RelevanceScores,
        similarity_matrix: SimilarityMatrix,
    ) -> DPPResult:
        """
        Run DPP greedy selection and return a DPPResult with drop reasons.

        The hard constraint (≥1 per conflict cluster) is guaranteed regardless
        of the β / γ hyperparameter values.
        """
        if not chunks:
            return DPPResult(selected_ids=[], dropped_ids=[], drop_reasons={})

        chunk_map: dict[str, Chunk] = {c.id: c for c in chunks}
        max_k = self._max_chunks if self._max_chunks is not None else len(chunks)
        conflict_clusters = self._build_conflict_clusters(relation_pairs)

        # --- Phase 1: mandatory seeds (one per conflict cluster) ---
        selected_ids: list[str] = []
        seen: set[str] = set()

        for cluster in conflict_clusters:
            members = [c for c in chunks if c.id in cluster]
            if not members:
                continue
            seed = max(members, key=lambda c: relevance_scores.get(c.id, 0.0))
            if seed.id not in seen and len(selected_ids) < max_k:
                selected_ids.append(seed.id)
                seen.add(seed.id)

        # --- Phase 2: greedy fill ---
        remaining = [c for c in chunks if c.id not in seen]

        while len(selected_ids) < max_k and remaining:
            current_subset = [chunk_map[cid] for cid in selected_ids]
            best_id: str | None = None
            best_score = float("-inf")

            for candidate in remaining:
                trial = current_subset + [candidate]
                score = self._score_subset(
                    trial, relevance_scores, similarity_matrix, conflict_clusters
                )
                if score > best_score:
                    best_score = score
                    best_id = candidate.id

            if best_id is None:
                break

            selected_ids.append(best_id)
            seen.add(best_id)
            remaining = [c for c in remaining if c.id != best_id]

        # --- Phase 3: assign drop reasons ---
        selected_set = set(selected_ids)
        dropped_ids = [c.id for c in chunks if c.id not in selected_set]
        drop_reasons: dict[str, str] = {}

        for cid in dropped_ids:
            is_redundant = any(
                self._get_similarity(cid, sid, similarity_matrix) > self._redundancy_threshold
                for sid in selected_set
            )
            drop_reasons[cid] = (
                DROP_REASON_REDUNDANT if is_redundant else DROP_REASON_IRRELEVANT
            )

        return DPPResult(
            selected_ids=sorted(selected_ids),
            dropped_ids=dropped_ids,
            drop_reasons=drop_reasons,
        )

    # ------------------------------------------------------------------
    # Score components
    # ------------------------------------------------------------------

    def _score_subset(
        self,
        subset: list[Chunk],
        relevance_scores: RelevanceScores,
        similarity_matrix: SimilarityMatrix,
        conflict_clusters: list[set[str]],
    ) -> float:
        if not subset:
            return 0.0
        return (
            self._relevance(subset, relevance_scores)
            + self._beta * self._diversity(subset, similarity_matrix)
            - self._redundancy(subset, similarity_matrix)
            - self._gamma * self._conflict_penalty(subset, conflict_clusters)
        )

    def _relevance(
        self, subset: list[Chunk], relevance_scores: RelevanceScores
    ) -> float:
        """Mean query-relevance score of the subset."""
        return sum(relevance_scores.get(c.id, 0.0) for c in subset) / len(subset)

    def _diversity(
        self, subset: list[Chunk], similarity_matrix: SimilarityMatrix
    ) -> float:
        """1 − mean pairwise cosine similarity.  Returns 1.0 for singletons."""
        if len(subset) < 2:
            return 1.0
        ids = [c.id for c in subset]
        total, pairs = 0.0, 0
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                total += self._get_similarity(ids[i], ids[j], similarity_matrix)
                pairs += 1
        return 1.0 - (total / pairs)

    def _redundancy(
        self, subset: list[Chunk], similarity_matrix: SimilarityMatrix
    ) -> float:
        """Sum of pairwise similarities that exceed the redundancy threshold."""
        if len(subset) < 2:
            return 0.0
        ids = [c.id for c in subset]
        total = 0.0
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                sim = self._get_similarity(ids[i], ids[j], similarity_matrix)
                if sim > self._redundancy_threshold:
                    total += sim
        return total

    def _conflict_penalty(
        self,
        subset: list[Chunk],
        conflict_clusters: list[set[str]],
    ) -> float:
        """Count of conflict clusters with no representative in the subset."""
        subset_ids = {c.id for c in subset}
        return float(
            sum(1 for cluster in conflict_clusters if subset_ids.isdisjoint(cluster))
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_conflict_clusters(
        self, relation_pairs: list[RelationPair]
    ) -> list[set[str]]:
        """
        Group chunk IDs into conflict clusters via union-find over contradiction pairs.

        Pairs with is_scope_difference=True are intentionally included: they
        represent the most important viewpoint diversity to preserve (e.g. Sucre
        constitutional vs La Paz administrative capital).
        """
        contradiction_pairs = [
            (rp.chunk_a_id, rp.chunk_b_id)
            for rp in relation_pairs
            if rp.nli_label == NLI_CONTRADICTION
        ]
        if not contradiction_pairs:
            return []

        parent: dict[str, str] = {}

        def find(x: str) -> str:
            parent.setdefault(x, x)
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        for a, b in contradiction_pairs:
            union(a, b)

        clusters: dict[str, set[str]] = defaultdict(set)
        for node in parent:
            clusters[find(node)].add(node)

        return list(clusters.values())

    def _get_similarity(
        self, a_id: str, b_id: str, similarity_matrix: SimilarityMatrix
    ) -> float:
        """Look up pairwise similarity with sorted-key normalisation."""
        key = (a_id, b_id) if a_id <= b_id else (b_id, a_id)
        return similarity_matrix.get(key, 0.0)
