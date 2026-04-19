# RAGPipeline — SKILLS.md

Load only the section relevant to the current task. Each skill is self-contained.

---

## SKILL: Canonical Data Structures

**Load when**: implementing any module that produces or consumes pipeline data.

Source file: `models/schemas.py`

```
Chunk
  id: str
  source_doc_id: str
  text: str
  embedding: list[float]
  credibility_score: float      # 0.1–1.0, assigned at upload
  credibility_tier: int         # 1–4

Query
  raw: str
  normalized: str
  entities: list[dict]          # [{text, label}]
  property: str                 # e.g. "capital"
  intent: str                   # e.g. "factual lookup"
  vector: list[float]

RelationPair
  chunk_a_id: str
  chunk_b_id: str
  similarity_score: float
  nli_label: str                # "contradiction" | "no-contradiction"
  entity_overlap: list[str]
  scope_qualifiers: list[str]
  is_scope_difference: bool     # True when qualifiers distinguish a surface contradiction

DPPResult
  selected_ids: list[str]
  dropped_ids: list[str]
  drop_reasons: dict[str, str]  # chunk_id → "redundant" | "irrelevant"

AgentPosition
  agent_id: str
  chunk_id: str
  position_text: str
  confidence: float
  status: str                   # "stable" | "revised" | "isolated"

DebateResult
  final_positions: list[AgentPosition]
  support_map: dict[str, list[str]]   # claim_text → [agent_ids]
  isolated_agent_ids: list[str]
  rounds_completed: int

ConflictReport
  conflict_type: str            # "ambiguity" | "outlier" | "oversimplification" | "noise"
  chunk_ids: list[str]
  evidence_strength: float
  decision_case: int            # 1 | 2 | 3
```

---

## SKILL: NLI Scope Qualifier Rule

**Load when**: implementing `pipeline/relations/nli.py` or any code that interprets
NLI output.

**Rule**:
```
IF a surface-level comparison of two chunks suggests conflicting values
   for the same property (e.g. different city named as "capital")
AND chunk_a carries a scope qualifier
AND chunk_b carries a different scope qualifier
AND both qualifiers refer to different roles of the same property
THEN set is_scope_difference = True
     (do NOT classify as misinformation or hard contradiction)
```

**Canonical example**:
- Chunk A: "Sucre is the constitutional capital of Bolivia"
- Chunk B: "La Paz is the administrative capital of Bolivia"
- Surface comparison: different cities, same property → may appear conflicting
- After qualifier rule: qualifiers differ ("constitutional" vs "administrative"),
  roles are distinct → `is_scope_difference=True`, not a real contradiction

**Qualifiers to detect**: "constitutional", "administrative", "seat of government",
"de facto", "de jure", "legal", "official", "ceremonial"

---

## SKILL: DPP Scoring Function

**Load when**: implementing `pipeline/selection/dpp_selector.py`.

**Formula**:
```
Score(S) = Relevance(S)
         + β · Diversity(S)
         − Redundancy(S)
         − γ · ConflictPenalty(S)
```

**Component definitions**:
- `Relevance(S)` — mean cosine similarity of selected chunks to the query vector
- `β · Diversity(S)` — β × (1 − mean pairwise similarity among selected chunks)
- `Redundancy(S)` — sum of similarity scores above `SIMILARITY_REDUNDANCY_THRESHOLD`
  for pairs within S
- `γ · ConflictPenalty(S)` — penalty when a conflict cluster has zero representatives in S

**Hard constraint**: for every conflict cluster C identified via NLI, `|S ∩ C| ≥ 1`

**Config parameters** (from `pipeline/shared/constants.py`):
- `DPP_BETA_DEFAULT` — diversity weight
- `DPP_GAMMA_DEFAULT` — conflict preservation weight
- `SIMILARITY_REDUNDANCY_THRESHOLD` — threshold above which a pair is "redundant"

---

## SKILL: Debate Early Stop Predicate

**Load when**: implementing `pipeline/debate/early_stop.py`.

**Stop when both conditions are true**:
1. All non-isolated agents have `status == "stable"` (no revision occurred in the
   last completed round)
2. The debate is operating on closed evidence: each agent is initialised with exactly
   one chunk and cannot access new information after initialisation. Early stop
   therefore depends on agent stability — once all non-isolated agents are stable,
   no further revision is possible.

**Isolated agent definition**: an agent with zero entries in `support_map` across all
rounds. An isolated agent that cannot change its evidence does not prevent early stop.

**Hard cap**: `MAX_DEBATE_ROUNDS` from `pipeline/shared/constants.py` serves as a
safety ceiling. Under normal operation, the closed-evidence condition plus stability
convergence should trigger early stop before this cap is reached.

---

## SKILL: Conflict Classification Rules

**Load when**: implementing `pipeline/synthesis/conflict_report.py`.

**Classification priority** (apply in this order):
1. **NOISE** — chunk does not address the query property at all (should have been
   filtered by DPP; handle defensively if present)
2. **OUTLIER** — claim contradicted by all other agents + zero support in support_map +
   no scope qualifier + low credibility source
3. **OVERSIMPLIFICATION** — claim is a factually incomplete subset of a correct claim,
   no qualifying context, not outright wrong
4. **AMBIGUITY** — multiple claims survive debate with different scope qualifiers;
   all have ≥1 supporting agent

**Decision case assignment**:
- Case 1 (Ambiguity): ≥2 surviving claims with different scope qualifiers
- Case 2 (Strong winner): exactly 1 dominant claim; all others isolated or rejected
- Case 3 (Unresolved): no claim achieves majority support AND no claim is isolated

---

## SKILL: Credibility Tier Mapping

**Load when**: implementing `pipeline/credibility/scorer.py` or reading credibility
values from chunk records.

| Tier | Score range | Source types |
|---|---|---|
| 1 | 0.90–1.00 | Institutional authority, government, peer-reviewed publications |
| 2 | 0.70–0.89 | Verified academic: encyclopedias, textbooks, faculty-uploaded |
| 3 | 0.40–0.69 | Student, community, informal write-ups |
| 4 | 0.10–0.39 | Unverified, anonymous, scraped, unattributed |

**Assignment**: credibility tier is derived from `source_type` in document metadata
at upload time. Score is the midpoint of the tier range by default.

**Usage constraint**: credibility score is a soft signal available to downstream
reasoning modules — conflict report classification and answer synthesis may use it
as a weighting factor when comparing competing claims. It must never be used as a
retrieval filter or a hard gate in DPP selection.

---

## SKILL: Chunking Strategy Selection

**Load when**: implementing `pipeline/upload/chunker.py` or choosing a strategy.

| Strategy | Boundary | Best for | Trade-off |
|---|---|---|---|
| Semantic | Topic/meaning shift | General documents | Higher cost |
| Character | Fixed size (e.g. 300 chars) | Speed-critical ingestion | May cut mid-sentence |
| Overlap | Fixed size + shared window | Boundary-sensitive content | Larger index |
| Hybrid | Semantic splits + char overlap | Long, structured documents | Most robust |

Default strategy: semantic chunking unless document metadata specifies otherwise.

---

## SKILL: Integration Test Scenario Types

**Load when**: writing tests in `tests/` or designing end-to-end validation.

Representative conflict scenario families that integration tests must cover:

| Scenario | Description | Expected pipeline output |
|---|---|---|
| **Ambiguity with scope qualifiers** | Multiple chunks give different answers to the same property, each with a distinct qualifying role | Case 1 answer presenting all valid answers with qualifiers |
| **Strong winner** | One claim is supported by multiple high-credibility sources; all others are either redundant or isolated | Case 2 answer returning the single best-supported claim |
| **Rejected outlier** | One chunk makes a claim that contradicts all others, has no qualifier, and has zero debate support | Outlier classified, excluded from answer; Case 2 or Case 1 depending on remaining claims |
| **Unresolved conflict** | Claims conflict and no side achieves majority support; no claim is clearly isolated | Case 3 answer stating insufficient evidence |
| **Redundant duplicate removal** | Multiple chunks express the same claim from the same or similar sources | DPP drops duplicates; downstream agents see only one representative per cluster |

**Note**: The Bolivia example (Sucre/La Paz/Santa Cruz) is an illustrative scenario
of the ambiguity + outlier combination. It is not an exhaustive test template.
Test implementations should construct each scenario family independently.
