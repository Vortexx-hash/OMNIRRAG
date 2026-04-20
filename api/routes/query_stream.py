"""
SSE streaming query endpoint.

POSTs a query and returns a text/event-stream of pipeline events so the
frontend can show each stage completing in real time.

Event shape:  data: {"type": "<stage>", "data": {...}}\n\n
Final event:  data: {"type": "complete", "data": <QueryResponse JSON>}\n\n
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.routes.query import (
    _DECISION_LABELS,
    _EXCERPT_LEN,
    build_query_response_data,
)
from api.schemas import QueryRequest
from api.state import get_pipeline
from pipeline.shared.constants import CONFLICT_NOISE, CONFLICT_OUTLIER

router = APIRouter(tags=["query"])


@router.post("/query/stream")
async def query_stream(body: QueryRequest) -> StreamingResponse:
    """
    Run the full pipeline and stream SSE events for each stage.
    The final event type is 'complete' and contains the full QueryResponse.
    """
    pipeline = get_pipeline()
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def emit(event_type: str, data: dict) -> None:
        asyncio.run_coroutine_threadsafe(
            queue.put({"type": event_type, "data": data}),
            loop,
        )

    def run_pipeline() -> None:
        try:
            result = pipeline.query(body.query, emit=emit)

            # Build the complete QueryResponse data (same logic as query.py)
            response_data = build_query_response_data(pipeline, result)
            emit("synthesis", {
                "decision_case": result.decision_case,
                "decision_label": _DECISION_LABELS.get(result.decision_case, "unresolved"),
                "answer_preview": result.answer[:200],
            })
            emit("complete", response_data)
        except Exception as exc:
            emit("error", {"message": str(exc)})
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    threading.Thread(target=run_pipeline, daemon=True).start()

    async def generate() -> AsyncGenerator[str, None]:
        while True:
            item = await queue.get()
            if item is None:
                return
            yield f"data: {json.dumps(item, default=str)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
