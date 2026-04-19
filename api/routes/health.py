from __future__ import annotations

from fastapi import APIRouter

import api.state as state
from api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return server status and the number of chunks currently indexed."""
    if state._pipeline is None:
        return HealthResponse(status="initializing", chunks_indexed=0)
    return HealthResponse(status="ok", chunks_indexed=state._pipeline.chunks_indexed)
