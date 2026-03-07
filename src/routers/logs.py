"""Log streaming endpoints — history + SSE real-time stream."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from utils.log_buffer import get_recent_logs, subscribe, unsubscribe

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
async def get_logs():
    """Return recent log history from the ring buffer."""
    return JSONResponse(content=get_recent_logs())


@router.get("/stream")
async def stream_logs():
    """SSE endpoint — streams new log entries in real-time."""
    q = subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    entry = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"data: {json.dumps(entry)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection drop
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
