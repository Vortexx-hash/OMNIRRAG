"""
FastAPI application factory for the conflict-aware RAG Pipeline API.

Startup sequence (lifespan):
  1. Initialise the Pipeline singleton (loads ML models — may take a few seconds)
  2. Store it in `api.state._pipeline`
  3. Yield — server is now ready to handle requests

All routes are registered here; individual route logic lives in `api/routes/`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import api.state as state
from main import Pipeline


@asynccontextmanager
async def _lifespan(app: FastAPI):
    state._pipeline = Pipeline()
    yield
    state._pipeline = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="Conflict-Aware RAG Pipeline",
        description=(
            "Upload documents and query them with conflict detection, "
            "multi-agent debate, and structured conflict classification."
        ),
        version="1.0.0",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from api.routes.health import router as health_router
    from api.routes.upload import router as upload_router
    from api.routes.query import router as query_router
    from api.routes.documents import router as documents_router

    app.include_router(health_router)
    app.include_router(upload_router)
    app.include_router(query_router)
    app.include_router(documents_router)

    return app


app = create_app()
