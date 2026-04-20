"""
Pipeline runner — entry point for the conflict-aware RAG pipeline.

Wires all pipeline stages (upload-time and query-time) through a single
Pipeline class.  Module-level convenience functions delegate to a shared
default instance.
"""

from __future__ import annotations

import pathlib

from models.schemas import Chunk, SynthesisResult
from pipeline.credibility.scorer import score_chunk
from pipeline.debate.orchestrator import DebateOrchestrator
from pipeline.query.normalizer import QueryNormalizer
from pipeline.query.retriever import Retriever
from pipeline.relations.chunk_similarity import compute_similarity_matrix
from pipeline.relations.ner import NERExtractor, extract_all
from pipeline.relations.nli import NLIClassifier, build_relation_pairs
from pipeline.relations.query_relevance import compute_query_relevance
from pipeline.selection.dpp_selector import DPPSelector
from pipeline.shared.constants import DECISION_CASE_UNRESOLVED, DPP_MIN_RELEVANCE_THRESHOLD, SCOPE_QUALIFIERS, TOP_K_DEFAULT
from pipeline.shared.types import EmbedderProtocol, VectorStoreProtocol
from pipeline.synthesis.answer_synthesizer import AnswerSynthesizer
from pipeline.synthesis.conflict_report import generate_conflict_reports
from pipeline.upload.chunker import Chunker, ChunkingStrategy
from pipeline.upload.embedder import Embedder
from pipeline.upload.vector_store import VectorStore


class Pipeline:
    """
    End-to-end conflict-aware RAG pipeline.

    upload() runs at document ingestion time.
    query()  runs at request time.

    Both an embedder and a vector_store can be injected (e.g. for testing).
    When omitted the production defaults are used.
    """

    def __init__(
        self,
        embedder: EmbedderProtocol | None = None,
        vector_store: VectorStoreProtocol | None = None,
        top_k: int = TOP_K_DEFAULT,
    ) -> None:
        self._embedder: EmbedderProtocol = embedder if embedder is not None else Embedder()
        self._store: VectorStoreProtocol = vector_store if vector_store is not None else VectorStore()
        self._top_k = top_k
        self._chunker = Chunker()
        self._normalizer = QueryNormalizer(self._embedder)
        self._retriever = Retriever(self._store)
        self._ner = NERExtractor()
        self._nli = NLIClassifier()
        self._dpp = DPPSelector(min_relevance=DPP_MIN_RELEVANCE_THRESHOLD)
        self._debate = DebateOrchestrator(embedder=self._embedder)
        self._synthesizer = AnswerSynthesizer()

    # ------------------------------------------------------------------
    # Store helpers (used by the API layer)
    # ------------------------------------------------------------------

    @property
    def last_debate_result(self):
        return getattr(self, "_last_debate_result", None)

    @property
    def chunks_indexed(self) -> int:
        """Number of chunks currently in the vector store."""
        return len(self._store)

    def get_chunks(self, chunk_ids: list[str]) -> list[Chunk]:
        """Fetch chunk objects by ID; silently skips missing IDs."""
        result = []
        for cid in chunk_ids:
            try:
                result.append(self._store.get(cid))
            except KeyError:
                pass
        return result

    # ------------------------------------------------------------------
    # Upload-time
    # ------------------------------------------------------------------

    def upload(
        self,
        text: str,
        source_metadata: dict,
        doc_id: str,
        strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
    ) -> list[str]:
        """
        Chunk, embed, score, and store a document.

        Returns the list of chunk IDs written to the vector store.
        source_metadata must contain at least {"source_type": "<type>"}.
        """
        credibility_score, credibility_tier = score_chunk(source_metadata)
        raw_chunks = self._chunker.chunk(text, strategy=strategy)
        stored_ids: list[str] = []
        for i, chunk_text in enumerate(raw_chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            embedding = self._embedder.encode(chunk_text)
            chunk = Chunk(
                id=chunk_id,
                source_doc_id=doc_id,
                text=chunk_text,
                embedding=embedding,
                credibility_score=credibility_score,
                credibility_tier=credibility_tier,
            )
            self._store.upsert(chunk)
            stored_ids.append(chunk_id)
        return stored_ids

    # ------------------------------------------------------------------
    # Query-time
    # ------------------------------------------------------------------

    def query(self, raw_query: str, emit=None) -> SynthesisResult:
        """
        Full query pipeline:
          normalize → retrieve → relate (×4) → DPP select
          → debate → conflict report → synthesize

        Returns a SynthesisResult with a conflict-aware natural language answer.
        """
        def _emit(stage: str, data: dict) -> None:
            if emit:
                emit(stage, data)

        query_obj = self._normalizer.normalize(raw_query)
        _emit("normalize", {
            "normalized": query_obj.normalized,
            "entities": query_obj.entities[:8],
            "intent": query_obj.intent,
            "property": query_obj.property,
        })

        chunks = self._retriever.retrieve(query_obj, top_k=self._top_k)
        _emit("retrieve", {
            "count": len(chunks),
            "chunks": [{"id": c.id, "excerpt": c.text[:80], "doc_id": c.source_doc_id} for c in chunks[:6]],
        })

        if not chunks:
            _emit("complete_early", {"reason": "no_chunks"})
            return SynthesisResult(
                answer="No relevant evidence found.",
                decision_case=DECISION_CASE_UNRESOLVED,
                conflict_reports=[],
                conflict_handling_tags=[],
                sources_cited=[],
            )

        # Stage 3: Relation building (4 computations)
        relevance_scores = compute_query_relevance(query_obj, chunks)
        similarity_matrix = compute_similarity_matrix(chunks)
        ner_results = extract_all(chunks, self._ner)
        relation_pairs = build_relation_pairs(
            chunks, self._nli, SCOPE_QUALIFIERS, ner_results
        )
        _emit("relations", {
            "pair_count": len(relation_pairs),
            "contradiction_count": sum(1 for p in relation_pairs if p.nli_label == "contradiction"),
            "scope_diff_count": sum(1 for p in relation_pairs if p.is_scope_difference),
        })

        # Stage 5: DPP selection
        dpp_result = self._dpp.select(
            chunks, relation_pairs, relevance_scores, similarity_matrix
        )
        selected_chunks = self._store.get_many(dpp_result.selected_ids)
        _emit("dpp", {
            "selected_count": len(dpp_result.selected_ids),
            "dropped_count": len(dpp_result.dropped_ids),
            "drop_reasons": dpp_result.drop_reasons,
        })

        # Stages 6-7: Debate
        debate_result = self._debate.run(selected_chunks, emit=emit)
        self._last_debate_result = debate_result

        # Stage 8: Conflict classification
        conflict_reports = generate_conflict_reports(
            positions=debate_result.final_positions,
            support_map=debate_result.support_map,
            isolated_agent_ids=debate_result.isolated_agent_ids,
            chunks=selected_chunks,
            relation_pairs=relation_pairs,
            embedder=self._embedder,
        )

        _emit("conflict", {
            "report_count": len(conflict_reports),
            "reports": [
                {"conflict_type": r.conflict_type, "chunk_count": len(r.chunk_ids),
                 "evidence_strength": r.evidence_strength, "has_scope_qualifier": r.has_scope_qualifier}
                for r in conflict_reports
            ],
        })

        # Stage 9: Synthesize
        return self._synthesizer.synthesize(
            reports=conflict_reports,
            positions=debate_result.final_positions,
            chunks=selected_chunks,
        )


# ---------------------------------------------------------------------------
# Module-level singleton + convenience functions
# ---------------------------------------------------------------------------

_default_pipeline: Pipeline | None = None


def _get_default_pipeline() -> Pipeline:
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = Pipeline()
    return _default_pipeline


def run_upload_pipeline(doc_path: str, source_metadata: dict) -> None:
    """Read a document file and run it through the upload pipeline."""
    text = pathlib.Path(doc_path).read_text(encoding="utf-8")
    doc_id = pathlib.Path(doc_path).stem
    _get_default_pipeline().upload(text, source_metadata, doc_id)


def run_query_pipeline(raw_query: str) -> str:
    """Run the full query pipeline and return the final natural language answer."""
    return _get_default_pipeline().query(raw_query).answer


if __name__ == "__main__":
    print("Use: python scripts/synthesis_visualizer.py [bolivia|medical|unresolved]")
    print("Or import Pipeline directly and call upload() / query().")
