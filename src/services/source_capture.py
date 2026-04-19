"""Per-stream source-payload accumulator.

Tools (web search, web extract, RAG retrieval) push a structured payload
here for every result they produce. The streaming layer drains the
accumulator after each ToolMessage and forwards the payloads on the SSE
`worker-result` event so the frontend can render rich preview cards in
the tree-view DetailPanel.

A `contextvars.ContextVar` keeps the accumulator scoped to the current
asyncio task — concurrent streams do not see each other's sources.
"""

from __future__ import annotations

import contextvars
from typing import List, Literal, Optional, TypedDict, Union


class WebSourcePayload(TypedDict, total=False):
    kind: Literal["web"]
    url: str
    title: str
    snippet: str
    site_name: str
    timestamp: float


class DocSourcePayload(TypedDict, total=False):
    kind: Literal["doc"]
    filename: str
    title: str
    excerpt: str
    page: int
    source: str
    timestamp: float


SourcePayload = Union[WebSourcePayload, DocSourcePayload]


_pending: contextvars.ContextVar[Optional[List[SourcePayload]]] = contextvars.ContextVar(
    "pending_sources", default=None
)


def start_capture() -> None:
    """Initialize the accumulator for the current task. Idempotent."""
    _pending.set([])


def append(source: SourcePayload) -> None:
    """Add a source payload to the accumulator. No-op if capture is not active."""
    bucket = _pending.get()
    if bucket is not None:
        bucket.append(source)


def drain() -> List[SourcePayload]:
    """Return and clear all accumulated payloads. Returns empty list if inactive."""
    bucket = _pending.get()
    if not bucket:
        return []
    drained = list(bucket)
    bucket.clear()
    return drained
