"""
Shared pipeline singleton — read by all route handlers.

The `_pipeline` variable is set by the FastAPI lifespan in `api/app.py` before
any request is served.  Routes import `get_pipeline` from here to avoid circular
imports (app → routes → app).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Pipeline

_pipeline: "Pipeline | None" = None
_documents: list[dict] = []


def get_pipeline() -> "Pipeline":
    if _pipeline is None:
        raise RuntimeError(
            "Pipeline not initialized — the server lifespan has not run yet."
        )
    return _pipeline


def get_documents() -> list[dict]:
    return _documents


def add_document(doc: dict) -> None:
    global _documents
    _documents = [d for d in _documents if d["doc_id"] != doc["doc_id"]]
    _documents.append(doc)
