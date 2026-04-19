from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

import api.state as state
from api.schemas import UploadRequest, UploadResponse
from api.state import get_pipeline
from pipeline.upload.chunker import ChunkingStrategy

router = APIRouter(tags=["upload"])

_STRATEGY_MAP: dict[str, ChunkingStrategy] = {
    "semantic": ChunkingStrategy.SEMANTIC,
    "character": ChunkingStrategy.CHARACTER,
    "overlap": ChunkingStrategy.OVERLAP,
    "hybrid": ChunkingStrategy.HYBRID,
}


@router.post("/upload", response_model=UploadResponse, status_code=201)
def upload_document(body: UploadRequest) -> UploadResponse:
    """
    Ingest a document into the pipeline.

    Chunks the text, embeds each chunk, assigns a credibility score from
    `source_metadata.source_type`, and stores everything in the vector store.
    Re-uploading the same `doc_id` upserts (overwrites) existing chunks.
    """
    strategy = _STRATEGY_MAP.get(body.chunking_strategy.lower())
    if strategy is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown chunking_strategy '{body.chunking_strategy}'. "
                f"Valid values: {sorted(_STRATEGY_MAP)}."
            ),
        )

    pipeline = get_pipeline()
    try:
        chunk_ids = pipeline.upload(
            text=body.text,
            source_metadata=body.source_metadata.model_dump(),
            doc_id=body.doc_id,
            strategy=strategy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    state.add_document({
        "doc_id": body.doc_id,
        "title": body.source_metadata.title,
        "source_type": body.source_metadata.source_type,
        "chunks_stored": len(chunk_ids),
        "chunk_ids": chunk_ids,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })

    return UploadResponse(
        doc_id=body.doc_id,
        chunks_stored=len(chunk_ids),
        chunk_ids=chunk_ids,
    )
