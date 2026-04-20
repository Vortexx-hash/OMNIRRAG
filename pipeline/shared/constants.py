"""
Pipeline-wide constants and default configuration values.

Tunable hyperparameters (DPP weights, thresholds) are defined here so they
can be overridden at call sites without modifying module logic.
"""

# Retrieval
TOP_K_DEFAULT: int = 10

# DPP Selector weights (β and γ must be passed as config, not hardcoded in logic)
DPP_BETA_DEFAULT: float = 0.5    # diversity weight
DPP_GAMMA_DEFAULT: float = 0.3   # conflict preservation weight
SIMILARITY_REDUNDANCY_THRESHOLD: float = 0.85  # pairs above this are "redundant"
DPP_MIN_RELEVANCE_THRESHOLD: float = 0.25  # phase-2 floor; chunks below this are skipped

# Debate
MAX_DEBATE_ROUNDS: int = 10  # hard safety ceiling; early stop triggers before this
DEBATE_SUPPORT_SIMILARITY_THRESHOLD: float = 0.65  # cosine sim floor for cross-support detection
DEBATE_INIT_MODEL: str = "gpt-4o-mini"  # claim extraction from chunk — pure structured output
DEBATE_ROUND_MODEL: str = "gpt-4o"      # confidence update — semantic judgment of related claims
SYNTHESIS_MODEL: str = "gpt-4o"         # final narrative answer

# Credibility tiers: (min_score, max_score)
CREDIBILITY_TIER_RANGES: dict[int, tuple[float, float]] = {
    1: (0.90, 1.00),  # Institutional authority
    2: (0.70, 0.89),  # Verified academic
    3: (0.40, 0.69),  # Student / community
    4: (0.10, 0.39),  # Unverified / external
}

# NLI labels
NLI_CONTRADICTION = "contradiction"
NLI_NO_CONTRADICTION = "no-contradiction"

# Agent statuses
AGENT_STATUS_STABLE = "stable"
AGENT_STATUS_REVISED = "revised"
AGENT_STATUS_ISOLATED = "isolated"

# Conflict types
CONFLICT_AMBIGUITY = "ambiguity"
CONFLICT_OUTLIER = "outlier"
CONFLICT_OVERSIMPLIFICATION = "oversimplification"
CONFLICT_NOISE = "noise"

# Decision cases
DECISION_CASE_AMBIGUITY = 1
DECISION_CASE_STRONG_WINNER = 2
DECISION_CASE_UNRESOLVED = 3

# DPP drop reasons
DROP_REASON_REDUNDANT = "redundant"
DROP_REASON_IRRELEVANT = "irrelevant"

# Known scope qualifiers for NLI rule
SCOPE_QUALIFIERS: list[str] = [
    # Governmental / geographic
    "constitutional",
    "administrative",
    "seat of government",
    "de facto",
    "de jure",
    "legal",
    "official",
    "ceremonial",
    # Medical / scientific dosing and context qualifiers
    "short-term",
    "long-term",
    "acute",
    "chronic",
    "low dose",
    "high dose",
    "therapeutic",
    "supplemental",
    "clinical",
    "subclinical",
    "adult",
    "pediatric",
    "elderly",
    "children",
    "insomnia",
    "jet lag",
    "shift work",
    "circadian",
    "sleep onset",
    "sleep maintenance",
    # General epistemic qualifiers
    "preliminary",
    "observational",
    "randomized",
    "meta-analysis",
]
