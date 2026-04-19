from __future__ import annotations

from fastapi import APIRouter

import api.state as state
from api.schemas import DocumentRecord

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=list[DocumentRecord])
def list_documents() -> list[DocumentRecord]:
    """Return all documents uploaded in this server session."""
    return [DocumentRecord(**d) for d in state.get_documents()]
