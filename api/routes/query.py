from __future__ import annotations

from fastapi import APIRouter

from api.schemas import (
    AgentPositionSummary,
    ConflictReportSummary,
    DebateSummary,
    EvidenceSummary,
    QueryRequest,
    QueryResponse,
    RejectedEvidenceSummary,
)
from api.state import get_pipeline
from pipeline.shared.constants import (
    CONFLICT_NOISE,
    CONFLICT_OUTLIER,
    DECISION_CASE_AMBIGUITY,
    DECISION_CASE_STRONG_WINNER,
    DECISION_CASE_UNRESOLVED,
)

router = APIRouter(tags=["query"])

_DECISION_LABELS = {
    DECISION_CASE_AMBIGUITY: "ambiguity",
    DECISION_CASE_STRONG_WINNER: "strong_winner",
    DECISION_CASE_UNRESOLVED: "unresolved",
}

_EXCERPT_LEN = 300


def build_query_response_data(pipeline, result) -> dict:
    """
    Build the full QueryResponse payload from a SynthesisResult.
    Shared by the sync query endpoint and the SSE streaming endpoint.
    Returns a plain dict (JSON-serialisable).
    """
    raw_debate = pipeline.last_debate_result

    cited_ids = list(result.sources_cited)
    rejected_ids: list[str] = []
    rejected_type_map: dict[str, str] = {}
    for report in result.conflict_reports:
        if report.conflict_type in (CONFLICT_OUTLIER, CONFLICT_NOISE):
            for cid in report.chunk_ids:
                if cid not in rejected_type_map:
                    rejected_ids.append(cid)
                    rejected_type_map[cid] = report.conflict_type

    all_ids = list(dict.fromkeys(cited_ids + rejected_ids))
    chunks = pipeline.get_chunks(all_ids)
    chunk_map = {c.id: c for c in chunks}

    selected_evidence = [
        {
            "chunk_id": cid,
            "text_excerpt": (chunk_map[cid].text[:_EXCERPT_LEN] if cid in chunk_map else ""),
            "source_doc_id": (chunk_map[cid].source_doc_id if cid in chunk_map else ""),
            "credibility_tier": (chunk_map[cid].credibility_tier if cid in chunk_map else 4),
            "credibility_score": (chunk_map[cid].credibility_score if cid in chunk_map else 0.0),
        }
        for cid in cited_ids
    ]

    rejected_evidence = [
        {
            "chunk_id": cid,
            "text_excerpt": (chunk_map[cid].text[:_EXCERPT_LEN] if cid in chunk_map else ""),
            "source_doc_id": (chunk_map[cid].source_doc_id if cid in chunk_map else ""),
            "credibility_tier": (chunk_map[cid].credibility_tier if cid in chunk_map else 4),
            "conflict_type": rejected_type_map[cid],
        }
        for cid in rejected_ids
    ]

    conflict_reports = [
        {
            "conflict_type": r.conflict_type,
            "chunk_ids": r.chunk_ids,
            "evidence_strength": r.evidence_strength,
            "decision_case": r.decision_case,
            "has_scope_qualifier": r.has_scope_qualifier,
        }
        for r in result.conflict_reports
    ]

    debate_summary = None
    if raw_debate is not None:
        debate_summary = {
            "agent_positions": [
                {
                    "agent_id": p.agent_id,
                    "chunk_id": p.chunk_id,
                    "position_text": p.position_text,
                    "confidence": p.confidence,
                    "status": p.status,
                    "reasoning": p.reasoning,
                }
                for p in raw_debate.final_positions
            ],
            "support_map": raw_debate.support_map,
            "isolated_agent_ids": raw_debate.isolated_agent_ids,
            "rounds_completed": raw_debate.rounds_completed,
        }

    return {
        "answer": result.answer,
        "decision_case": result.decision_case,
        "decision_label": _DECISION_LABELS.get(result.decision_case, "unresolved"),
        "conflict_reports": conflict_reports,
        "selected_evidence": selected_evidence,
        "rejected_evidence": rejected_evidence,
        "sources_cited": result.sources_cited,
        "conflict_handling_tags": result.conflict_handling_tags,
        "debate_summary": debate_summary,
    }


@router.post("/query", response_model=QueryResponse)
def run_query(body: QueryRequest) -> QueryResponse:
    """
    Run the full conflict-aware RAG pipeline against the indexed documents.
    """
    pipeline = get_pipeline()
    result = pipeline.query(body.query)
    data = build_query_response_data(pipeline, result)
    return QueryResponse(**data)
