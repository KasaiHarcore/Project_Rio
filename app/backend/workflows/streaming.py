"""LangGraph streaming helpers.

Streams workflow execution events so the UI can render partial responses.
This implementation intentionally does NOT support interrupts/approval.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Iterator
from uuid import uuid4
import time

from backend.core.settings import AgentConfig
from backend.services.run_service import run_service
from backend.services.workflow_state_service import resolve_checkpoint_thread_id
from backend.db.models.run import RunStatus
from backend.utils.log import log_debug, log_error

from backend.workflows.langgraph_workflow import (
    build_workflow,
    _get_checkpointer,
    _sanitize_history,
    GraphState,
)


def stream_workflow(
    *,
    question: str,
    config: AgentConfig,
    history: Optional[List[Dict[str, Any]]] = None,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
    """Run the workflow and yield token/final/error events.

    Yields:
      - {"type": "token", "content": "..."}
      - {"type": "final", "result": {...}, "run_id": "..."}
      - {"type": "error", "error": "...", "run_id": "..."}

    Note: interrupts are treated as errors (they are not supported).
    """

    log_debug("Stream workflow started")
    graph = build_workflow().compile(checkpointer=_get_checkpointer())
    run_id = run_id or uuid4().hex

    checkpoint_thread_id = resolve_checkpoint_thread_id(
        thread_id,
        run_id,
        getattr(config, "state_scope", None),
    )
    config_payload = {"configurable": {"thread_id": checkpoint_thread_id}}

    max_history_items = int(getattr(config, "history_max_items", 50) or 0)
    sanitized_history = _sanitize_history(history, max_items=max_history_items)

    state: GraphState = {
        "question": question,
        "config": config,
        "history": sanitized_history,
        "thread_id": thread_id,
        "run_id": run_id,
        "step": 0,
        "retry_count": 0,
        "max_retries": getattr(config, "verify_max_retries", 2),
        "state_schema_version": getattr(config, "state_schema_version", 1),
        "checkpoint_every": getattr(config, "checkpoint_every", 1),
        "state_scope": getattr(config, "state_scope", "thread"),
        "started_at": time.time(),
        "deadline_ts": time.time() + float(getattr(config, "max_execution_seconds", 120)),
    }

    run_service.start_run(
        run_id=run_id,
        thread_id=thread_id,
        mode=getattr(config, "mode", None),
        model_name=getattr(config, "model_name", None),
    )

    latest_state: Optional[Dict[str, Any]] = None

    try:
        for chunk in graph.stream(state, config=config_payload, stream_mode=["messages", "values", "updates"]):
            mode = None
            data = None

            if isinstance(chunk, tuple) and len(chunk) == 2 and isinstance(chunk[0], str):
                mode, data = chunk
            elif isinstance(chunk, dict):
                if "messages" in chunk:
                    mode = "messages"
                    data = chunk["messages"]
                elif "values" in chunk:
                    mode = "values"
                    data = chunk["values"]
                elif "updates" in chunk:
                    mode = "updates"
                    data = chunk["updates"]

            if mode == "messages" and data is not None:
                msg = data[0] if isinstance(data, tuple) and len(data) == 2 else data
                content = getattr(msg, "content", None)
                if content is None:
                    content = str(msg)
                if content:
                    yield {"type": "token", "content": content}

            if mode == "values" and isinstance(data, dict):
                latest_state = data

            if mode == "updates" and isinstance(data, dict):
                if "__interrupt__" in data:
                    raise RuntimeError("Workflow interrupt requested, but interrupts are disabled.")

        final_state = latest_state or {}
        if "__interrupt__" not in final_state:
            run_service.finish_run(run_id=run_id, status=RunStatus.SUCCEEDED)

        log_debug("Stream workflow completed")
        yield {"type": "final", "result": final_state, "run_id": run_id}
    except Exception as e:
        run_service.finish_run(run_id=run_id, status=RunStatus.FAILED, error=str(e))
        log_error(f"Stream workflow failed: {e}")
        yield {"type": "error", "error": str(e), "run_id": run_id}
