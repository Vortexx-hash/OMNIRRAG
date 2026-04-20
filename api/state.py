"""
Shared pipeline singleton and document registry.

Both are persisted to disk (data/) so they survive server restarts.
"""

from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Pipeline

_pipeline: "Pipeline | None" = None

# ------------------------------------------------------------------
# Document registry — persisted to data/documents.json
# ------------------------------------------------------------------

_DOCS_PATH = pathlib.Path("data/documents.json")


def _load_documents() -> list[dict]:
    if not _DOCS_PATH.exists():
        return []
    try:
        with open(_DOCS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_documents(docs: list[dict]) -> None:
    try:
        _DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_DOCS_PATH, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=2)
    except Exception:
        pass


# Load on import (i.e. server startup)
_documents: list[dict] = _load_documents()


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
    _save_documents(_documents)
