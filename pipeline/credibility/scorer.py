"""
Credibility Scorer — upload-time stage.

Assigns a credibility tier (1–4) and a score (0.1–1.0) to a document chunk
based on its source metadata.  Called at upload time; the result is stored
directly on the Chunk record.

Credibility is a **soft signal only**.  It is never used to filter chunks;
it informs only the final answer synthesizer's weighting.
See SKILLS.md: Credibility Tier Mapping.
"""

from __future__ import annotations

from pipeline.shared.constants import CREDIBILITY_TIER_RANGES

# ---------------------------------------------------------------------------
# Source-type → tier mapping
# ---------------------------------------------------------------------------

_SOURCE_TYPE_TIER: dict[str, int] = {
    # Tier 1 — Institutional authority, government, peer-reviewed
    "government": 1,
    "gov": 1,
    "institutional": 1,
    "peer_reviewed": 1,
    "peer-reviewed": 1,
    "official": 1,
    # Tier 2 — Verified academic, encyclopedias, faculty
    "academic": 2,
    "encyclopedia": 2,
    "encyclopaedia": 2,
    "faculty": 2,
    "verified": 2,
    "textbook": 2,
    "journal": 2,
    # Tier 3 — Student, community, informal
    "student": 3,
    "community": 3,
    "informal": 3,
    "blog": 3,
    "wiki": 3,
    "forum": 3,
    # Tier 4 — Unverified, anonymous, scraped
    "unverified": 4,
    "anonymous": 4,
    "scraped": 4,
    "unknown": 4,
    "social_media": 4,
    "social-media": 4,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assign_tier(source_type: str) -> int:
    """
    Return the credibility tier (1–4) for *source_type*.
    Matching is case-insensitive.
    Raises ValueError for source types not in the known mapping.
    """
    key = source_type.lower().strip()
    if key not in _SOURCE_TYPE_TIER:
        raise ValueError(
            f"Unknown source type: {source_type!r}. "
            f"Known types: {sorted(_SOURCE_TYPE_TIER)}"
        )
    return _SOURCE_TYPE_TIER[key]


def tier_to_score(tier: int) -> float:
    """Return the midpoint credibility score for *tier* (within its declared range)."""
    if tier not in CREDIBILITY_TIER_RANGES:
        raise ValueError(f"Invalid tier: {tier!r}.  Must be one of {sorted(CREDIBILITY_TIER_RANGES)}.")
    lo, hi = CREDIBILITY_TIER_RANGES[tier]
    return round((lo + hi) / 2, 4)


def score_chunk(source_metadata: dict) -> tuple[float, int]:
    """
    Derive ``(credibility_score, credibility_tier)`` from document source metadata.

    Required metadata key:
        ``"source_type"`` — a non-empty string identifying the source class
        (e.g. ``"government"``, ``"academic"``, ``"blog"``).

    Raises ValueError if the key is missing, empty, or maps to an unknown type.
    """
    source_type = source_metadata.get("source_type", "")
    if not source_type:
        raise ValueError(
            "source_metadata must include a non-empty 'source_type' key."
        )
    tier = assign_tier(source_type)
    score = tier_to_score(tier)
    return score, tier
