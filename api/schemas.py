"""
Pydantic request/response schemas for the RAG Pipeline REST API.

These are *API* schemas — distinct from the internal dataclasses in
`models/schemas.py`.  They define the contract between callers and the
API layer; the routes translate between the two.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class SourceMetadata(BaseModel):
    """Metadata accompanying a document upload.

    `source_type` is required and must match one of the known types in
    `pipeline/credibility/scorer.py` (e.g. "government", "academic", "blog").
    Extra fields (title, author, url) are stored alongside for frontend display
    but are not used by the credibility scorer.
    """

    model_config = ConfigDict(extra="allow")

    source_type: str = Field(
        ...,
        description="Source class used for credibility scoring. "
                    "E.g. 'government', 'academic', 'blog', 'unverified'.",
    )
    title: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None


class UploadRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Full document text to ingest.")
    doc_id: str = Field(
        ...,
        min_length=1,
        description="Caller-assigned document identifier. "
                    "Re-uploading the same doc_id upserts its chunks.",
    )
    source_metadata: SourceMetadata
    chunking_strategy: str = Field(
        "semantic",
        description="One of: semantic | character | overlap | hybrid.",
    )


class UploadResponse(BaseModel):
    doc_id: str
    chunks_stored: int
    chunk_ids: list[str]


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language question.")


class EvidenceSummary(BaseModel):
    """A chunk that was cited in the final answer."""

    chunk_id: str
    text_excerpt: str = Field(..., description="First 300 characters of the chunk.")
    source_doc_id: str
    credibility_tier: int = Field(..., ge=1, le=4)
    credibility_score: float = Field(..., ge=0.0, le=1.0)


class RejectedEvidenceSummary(BaseModel):
    """A chunk that was present during debate but classified as outlier or noise."""

    chunk_id: str
    text_excerpt: str = Field(..., description="First 300 characters of the chunk.")
    source_doc_id: str
    credibility_tier: int
    conflict_type: str = Field(..., description="'outlier' or 'noise'.")


class ConflictReportSummary(BaseModel):
    conflict_type: str = Field(
        ...,
        description="'ambiguity' | 'outlier' | 'oversimplification' | 'noise'",
    )
    chunk_ids: list[str]
    evidence_strength: float
    decision_case: int
    has_scope_qualifier: bool


class AgentPositionSummary(BaseModel):
    agent_id: str
    chunk_id: str
    position_text: str
    confidence: float
    status: str = Field(..., description="'stable' | 'revised' | 'isolated'")
    reasoning: str = ""


class DebateSummary(BaseModel):
    agent_positions: list[AgentPositionSummary]
    support_map: dict[str, list[str]]
    isolated_agent_ids: list[str]
    rounds_completed: int


class QueryResponse(BaseModel):
    answer: str
    decision_case: int = Field(..., description="1=ambiguity, 2=strong_winner, 3=unresolved")
    decision_label: str = Field(..., description="Human-readable decision case.")
    conflict_reports: list[ConflictReportSummary]
    selected_evidence: list[EvidenceSummary]
    rejected_evidence: list[RejectedEvidenceSummary]
    sources_cited: list[str]
    conflict_handling_tags: list[str]
    debate_summary: Optional[DebateSummary] = None


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DocumentRecord(BaseModel):
    doc_id: str
    title: Optional[str] = None
    source_type: str
    chunks_stored: int
    chunk_ids: list[str]
    uploaded_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    chunks_indexed: int
