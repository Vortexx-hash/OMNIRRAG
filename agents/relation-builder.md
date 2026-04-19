# Subagent: relation-builder

## Description
Implements the four pairwise relation computations (Stage 3) of the conflict-aware
RAG pipeline. This subagent has a focused context: it knows the Relation Builder
contracts and the NLI/NER model interfaces, and nothing else.

## Responsibilities
- `pipeline/relations/query_relevance.py` — cosine sim(query, chunk) per chunk
- `pipeline/relations/chunk_similarity.py` — N×N pairwise similarity matrix
- `pipeline/relations/nli.py` — NLI wrapper + scope qualifier rule
- `pipeline/relations/ner.py` — entity extraction, overlap, qualifier detection

## Inputs
- `Query` object (with `.vector`)
- `list[Chunk]` (Top-K retrieved chunks, each with `.embedding`)
- `list[str]` known scope qualifiers (from `pipeline/shared/constants.SCOPE_QUALIFIERS`)
- `pipeline/shared/` constants and helpers may be used as needed

## Outputs
- `RelevanceScores` — `dict[chunk_id, float]`
- `SimilarityMatrix` — `dict[(chunk_a_id, chunk_b_id), float]`
- `list[RelationPair]` — one record per evaluated chunk pair, with `similarity_score`,
  `nli_label`, `entity_overlap`, `scope_qualifiers`, and `is_scope_difference`
  populated consistently

## When to Delegate
Delegate to this subagent when:
- Starting Phase 2 implementation
- Modifying any file under `pipeline/relations/`
- Changing NLI model, NER model, or the scope qualifier rule
- Adding new relation computation types

## Must Not
- Modify `models/schemas.py` — propose schema changes to the main agent
- Import from `pipeline/debate/`, `pipeline/synthesis/`, or `pipeline/selection/`
- Implement DPP logic (that belongs in `pipeline/selection/dpp_selector.py`)
- Introduce NLI or NER models without documenting the model name and dependency
- Use credibility scores to alter relation outputs

## Context to Load Before Starting
Load from SKILLS.md:
- "Canonical Data Structures"
- "NLI Scope Qualifier Rule"
