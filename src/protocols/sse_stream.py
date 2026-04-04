"""AI SDK v6 UIMessageStream (Server-Sent Events) protocol helpers.

Protocol reference (ai@6.0+ / @ai-sdk/react):
  Each SSE event is: ``data: {json}\\n\\n``
  UIMessageChunk types used:
    {"type":"start"}                          - message start
    {"type":"start-step"}                     - step start
    {"type":"text-start","id":"..."}          - begin text part
    {"type":"text-delta","id":"...","delta":"..."} - text token
    {"type":"text-end","id":"..."}            - end text part
    {"type":"data-<name>","data":{...}}       - custom data (sidebar events)
    {"type":"finish-step"}                    - step finished
    {"type":"finish","finishReason":"stop"}   - message finished
  Final event: ``data: [DONE]\\n\\n``
"""

from __future__ import annotations

import json


def sse(payload: dict | str) -> str:
    """Wrap a JSON payload (or raw string like ``[DONE]``) as an SSE data line."""
    data = payload if isinstance(payload, str) else json.dumps(payload, separators=(",", ":"))
    return f"data: {data}\n\n"


def text_start(part_id: str) -> str:
    return sse({"type": "text-start", "id": part_id})


def text_delta(part_id: str, delta: str) -> str:
    return sse({"type": "text-delta", "id": part_id, "delta": delta})


def text_end(part_id: str) -> str:
    return sse({"type": "text-end", "id": part_id})


def data_event(name: str, data: dict) -> str:
    """Emit a custom ``data-<name>`` UIMessageChunk.

    AI SDK v6 allows custom data types whose ``type`` starts with ``data-``.
    """
    return sse({"type": f"data-{name}", "data": data})


def start_message() -> str:
    return sse({"type": "start"})


def start_step() -> str:
    return sse({"type": "start-step"})


def finish_step() -> str:
    return sse({"type": "finish-step"})


def finish_message(reason: str = "stop") -> str:
    return sse({"type": "finish", "finishReason": reason})


def error_event(message: str) -> str:
    return sse({"type": "error", "errorText": message})


def done() -> str:
    return sse("[DONE]")
