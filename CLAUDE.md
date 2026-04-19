# RAGPipeline — CLAUDE.md

## Project Purpose

Implementation of a conflict-aware RAG pipeline that detects, debates, and resolves conflicts
in retrieved evidence before generating a final answer. The pipeline goes beyond standard
retrieve-and-generate by adding pairwise relation reasoning, credibility scoring,
diversity-aware selection, and multi-agent debate.

**Design source of truth**: `rag_conflict_pipeline_v2.html`

---

## Non-Negotiable Rules

1. **`models/schemas.py` is canonical.** All data structures live there. Never define
   new schemas inline in module files. Never modify schemas from a subagent session —
   propose the change and let the main agent apply it.

2. **Credibility score is a soft signal.** It is assigned at upload time, stored on the
   chunk record, and used only as a weighting input in the final synthesizer.
   Credibility never directly filters chunks; selection is handled by retrieval, DPP,
   and debate outcome.

3. **NLI scope qualifier rule.** Two chunks that produce a surface NLI contradiction
   but carry different scope qualifiers (e.g. "constitutional capital" vs
   "administrative capital") must be classified as `is_scope_difference=True`.
   They are NOT a hard contradiction and must not be treated as misinformation.

4. **DPP must preserve conflict clusters.** The `ConflictPenalty` term in the DPP
   scoring function enforces that at least one chunk from each conflict cluster
   survives selection. Never implement DPP as pure redundancy removal.

5. **Agent isolation is strict.** Debate agents read only their own chunk at
   initialisation. During debate rounds they see other agents' positions — never
   other agents' source chunks.

6. **Upload-time and query-time are cleanly separated.** `pipeline/upload/` contains
   only logic that runs at document ingestion. It must not be called from query-time
   modules.

7. **β and γ are config, not hardcoded.** The DPP scoring weights must be exposed as
   configurable parameters. Defaults live in `pipeline/shared/constants.py`.

8. **No stage reimplementation.**
Modules must not duplicate logic from other stages.
Each stage consumes outputs from previous stages rather than recomputing them.

---

## Architecture Summary

### Upload-time (runs once per document)
```
Document + source_metadata
  → Chunker (semantic | char | overlap | hybrid)
  → Embedder (chunk → dense vector)
  → Vector DB (stores Chunk with embedding + credibility_score + credibility_tier)
```

### Query-time (runs per query)
```
Raw query
  → Query Normalizer (entities, property, intent, query vector)
  → Retriever (cosine sim → Top-K chunks)
  → Relation Builder ×4 parallel:
      3.1 Query Relevance    sim(query, chunkᵢ)
      3.2 Chunk Similarity   N×N pairwise matrix
      3.3 NLI                contradiction | no-contradiction + scope qualifier rule
      3.4 NER                entity overlap + qualifier detection
  → DPP Selector (relevance + diversity − redundancy − conflict_penalty)
  → Agent Bank (1 agent / chunk, isolated init)
  → Debate Orchestrator (round loop + early stop)
  → Conflict Report Generator (ambiguity | outlier | oversimplification | noise)
  → Final Answer Synthesizer (Case 1 | 2 | 3)
```

---

## Module Boundaries

| Module | Owner | Allowed imports |
|---|---|---|
| `pipeline/shared/` | main agent | stdlib only |
| `pipeline/upload/` | main agent | `models/`, `pipeline/shared/` |
| `pipeline/query/` | main agent | `models/`, `pipeline/shared/` |
| `pipeline/selection/` | main agent | `models/`, `pipeline/shared/`, `pipeline/relations/` |
| `pipeline/relations/` | relation-builder subagent | `models/`, `pipeline/shared/` |
| `pipeline/credibility/` | main agent | `models/`, `pipeline/shared/` |
| `pipeline/debate/` | debate-system subagent | `models/`, `pipeline/shared/` |
| `pipeline/synthesis/` | synthesis subagent | `models/`, `pipeline/shared/` |
| `main.py` | main agent | all pipeline modules |

Cross-module imports outside this table are not permitted unless explicitly justified.
Prefer using shared interfaces or schemas instead of direct dependency.

---

## Workflow Rules

- Implement phases in order: 1 (infra) → 2 (relations) → 3 (selection) → 4 (debate) → 5 (synthesis) → 6 (integration)
- Do not introduce generic RAG components unless they improve modularity, clarity, or performance and remain consistent with the pipeline design.
- Schema changes: update `models/schemas.py` first, then update all callers
- Integration tests should include representative conflict scenarios such as:
  - ambiguity with scope qualifiers
  - clear contradictions with an outlier
  - redundant duplicate removal
  - unresolved cases with insufficient evidence

  The Bolivia example is one reference scenario illustrating expected behavior,
  but it must not be treated as a fixed template or exhaustive test case.
- Tests must be written alongside each phase, not deferred

---

## Phased Implementation Plan

| Phase | Scope | Agent |
|---|---|---|
| 1 | Schemas, shared utilities, upload pipeline, normalizer, retriever | Main |
| 2 | 4 relation computations | `relation-builder` |
| 3 | Credibility scorer, DPP selector | Main |
| 4 | Agent bank, debate orchestrator, early stop | `debate-system` |
| 5 | Conflict report, answer synthesizer | `synthesis` |
| 6 | Integration, Bolivia end-to-end test | Main |
