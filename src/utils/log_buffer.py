"""In-memory ring buffer for log entries with SSE fan-out support."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from typing import Any, Dict, List


_MAX_BUFFER = 500
_buffer: deque[Dict[str, Any]] = deque(maxlen=_MAX_BUFFER)
_subscribers: List[asyncio.Queue[Dict[str, Any]]] = []

_LEVEL_NAME_MAP = {
    "TRACE": "trace",
    "DEBUG": "debug",
    "INFO": "info",
    "SUCCESS": "success",
    "WARNING": "warning",
    "ERROR": "error",
    "CRITICAL": "critical",
}


def _level_name(record_level) -> str:
    """Convert loguru level to a frontend-friendly lowercase name."""
    raw = getattr(record_level, "name", "INFO")
    return _LEVEL_NAME_MAP.get(raw, raw.lower())


def log_buffer_sink(message) -> None:
    """Loguru sink function — captures each log record into the ring buffer."""
    record = message.record
    entry = {
        "id": uuid.uuid4().hex[:12],
        "timestamp": record["time"].strftime("%H:%M:%S.%f")[:-3],
        "level": _level_name(record["level"]),
        "message": record["message"],
        "source": record["name"] or "root",
    }
    _buffer.append(entry)

    # Fan out to SSE subscribers
    dead: List[asyncio.Queue] = []
    for q in _subscribers:
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def get_recent_logs() -> List[Dict[str, Any]]:
    """Return a snapshot of the current buffer."""
    return list(_buffer)


def subscribe() -> asyncio.Queue[Dict[str, Any]]:
    """Create a new subscriber queue for SSE streaming."""
    q: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=200)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    """Remove a subscriber queue."""
    try:
        _subscribers.remove(q)
    except ValueError:
        pass
