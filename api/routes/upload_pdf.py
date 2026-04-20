"""PDF upload endpoint — extracts text then delegates to the standard upload pipeline."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

import api.state as state
from api.schemas import UploadResponse
from api.state import get_pipeline
from pipeline.upload.chunker import ChunkingStrategy

router = APIRouter(tags=["upload"])

_STRATEGY_MAP: dict[str, ChunkingStrategy] = {
    "semantic": ChunkingStrategy.SEMANTIC,
    "character": ChunkingStrategy.CHARACTER,
    "overlap": ChunkingStrategy.OVERLAP,
    "hybrid": ChunkingStrategy.HYBRID,
}


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes. Tries pypdf then PyPDF2 as fallback."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore[no-redef]
        except ImportError:
            raise HTTPException(
                status_code=422,
                detail=(
                    "PDF parsing library not installed. "
                    "Run: pip install pypdf"
                ),
            )

    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages_text.append(text)

    if not pages_text:
        raise HTTPException(
            status_code=422,
            detail=(
                "No extractable text found in the PDF. "
                "The file may be a scanned image — use a text-based PDF."
            ),
        )

    return "\n\n".join(pages_text)


@router.post("/upload/pdf", response_model=UploadResponse, status_code=201)
async def upload_pdf_document(
    file: UploadFile = File(..., description="PDF file to ingest."),
    doc_id: str = Form(..., min_length=1),
    source_type: str = Form(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    chunking_strategy: str = Form("semantic"),
) -> UploadResponse:
    """
    Ingest a PDF document.

    Extracts plain text from the PDF, then runs the identical upload pipeline
    as the JSON text endpoint (chunk → embed → score → store).
    """
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="File must be a .pdf document.")

    strategy = _STRATEGY_MAP.get(chunking_strategy.lower())
    if strategy is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown chunking_strategy '{chunking_strategy}'. Valid: {sorted(_STRATEGY_MAP)}.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    text = _extract_pdf_text(file_bytes)

    source_metadata: dict = {"source_type": source_type}
    if title:
        source_metadata["title"] = title
    if author:
        source_metadata["author"] = author
    if url:
        source_metadata["url"] = url

    pipeline = get_pipeline()
    try:
        chunk_ids = pipeline.upload(
            text=text,
            source_metadata=source_metadata,
            doc_id=doc_id,
            strategy=strategy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    state.add_document({
        "doc_id": doc_id,
        "title": title or filename,
        "source_type": source_type,
        "chunks_stored": len(chunk_ids),
        "chunk_ids": chunk_ids,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })

    return UploadResponse(
        doc_id=doc_id,
        chunks_stored=len(chunk_ids),
        chunk_ids=chunk_ids,
    )
