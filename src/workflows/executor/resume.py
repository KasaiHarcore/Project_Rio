"""
Resume functions for workflow execution after human-in-the-loop interrupts.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterator, Optional
from uuid import uuid4

from langgraph.types import Command

from core.settings import (
    AgentConfig,
    TOOL_PREVIEW_LENGTH,
    STREAM_TOKEN_BATCH_SIZE,
)
from core.exceptions import WorkflowError
from infrastructure.llm import form
from infrastructure.cache.redis_cache import redis_tool
from utils.log import log_debug, log_error, log_info, log_warning
from workflows.checkpointer import (
    build_config_payload,
    checkpoint_context,
)
from workflows.memory_store import memory_store_context
from workflows.react_graph import build_react_graph

from workflows.executor.checkpoints import load_checkpoint
from workflows.executor.run import run_workflow


def resume_from_checkpoint(
    *,
    thread_id: str,
    checkpoint_id: str,
    checkpoint_ns: str = "",
    config: AgentConfig,
    human_response: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resume workflow execution from a specific checkpoint.

    Useful for:
    - Continuing after human-in-the-loop
    - Time-travel debugging
    - Retry after failure

    Args:
        thread_id: Thread to resume
        checkpoint_id: Checkpoint to resume from
        checkpoint_ns: Namespace
        config: Agent configuration
        human_response: Optional human response for human-in-the-loop

    Returns:
        Execution result
    """
    log_info(f"Resuming from checkpoint: {checkpoint_id}")

    checkpoint_data = load_checkpoint(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )

    if not checkpoint_data:
        return {"error": f"Checkpoint not found: {checkpoint_id}", "status": "failed"}


    return run_workflow(
        question=human_response or "",  # Continue with human response
        config=config,
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )


def resume_sql_approval(
    *,
    thread_id: str,
    config: AgentConfig,
    approval_response: Dict[str, Any],
    checkpoint_ns: str = "",
) -> Iterator[Dict[str, Any]]:
    """
    Resume workflow after SQL operation approval.

    Uses LangGraph's ``Command(resume=value)`` so the resumed value
    reaches the SQL worker's ``interrupt()`` call directly.

    Returns a streaming iterator (same event protocol as ``stream_workflow``)
    so the frontend can receive tokens and structured events after approval.

    Args:
        thread_id: Thread to resume
        config: Agent configuration
        approval_response: User's approval response containing:
            - action: 'approve', 'edit', 'reject', 'always_approve'
            - edited_sql: Optional modified SQL (when action is 'edit')
            - reason: Optional reason for rejection
        checkpoint_ns: Namespace

    Yields:
        Event dictionaries (same protocol as stream_workflow)
    """
    log_info(f"Resuming SQL approval for thread: {thread_id}")

    checkpoint_ns = checkpoint_ns or config.state_scope

    action = approval_response.get("action", "reject")
    valid_actions = {"approve", "edit", "reject", "always_approve"}
    if action not in valid_actions:
        yield {"type": "error", "error": f"Invalid action: {action}. Must be one of {valid_actions}"}
        return

    resume_value: Dict[str, Any] = {"action": action}

    if action == "always_approve":
        resume_value["action"] = "approve"

    if action == "edit":
        edited_sql = approval_response.get("edited_sql", "").strip()
        if not edited_sql:
            yield {"type": "error", "error": "edited_sql is required when action is 'edit'"}
            return
        resume_value["modified_sql"] = edited_sql

    if approval_response.get("reason"):
        resume_value["reason"] = approval_response["reason"]

    config_payload = build_config_payload(
        thread_id=thread_id,
        checkpoint_ns=checkpoint_ns,
    )

    run_id = uuid4().hex

    yield {"type": "run_started", "run_id": run_id, "thread_id": thread_id}

    try:
        with checkpoint_context() as checkpointer, memory_store_context() as store:
            graph = build_react_graph(
                config=config,
                checkpointer=checkpointer,
                store=store,
            )

            if action == "always_approve":
                try:
                    state_cfg = {"configurable": dict((config_payload or {}).get("configurable") or {})}
                    current_state = graph.get_state(state_cfg)
                    if current_state and current_state.values:
                        metadata = dict(current_state.values.get("metadata") or {})
                        metadata["sql_auto_approve"] = True
                        graph.update_state(state_cfg, {"metadata": metadata})
                        log_info(f"Set sql_auto_approve=True for thread {thread_id}")
                except Exception as meta_err:
                    if "Subgraph thread not found" in str(meta_err):
                        log_debug(f"Failed to set sql_auto_approve flag: {meta_err}")
                    else:
                        log_warning(f"Failed to set sql_auto_approve flag: {meta_err}")

            start_time = time.time()
            token_buffer = ""
            final_state = None
            answer = ""

            seen_workers = set()
            seen_decisions = 0
            event_count = 0

            stream_iter = graph.stream(
                Command(resume=resume_value),
                config=config_payload,
                stream_mode="values",
            )

            for event in stream_iter:
                event_count += 1
                if isinstance(event, dict):
                    final_state = event

                    decisions = event.get("supervisor_decisions") or []
                    if len(decisions) > seen_decisions:
                        latest_decision = decisions[-1]
                        seen_decisions = len(decisions)
                        yield {
                            "type": "supervisor",
                            "decision": latest_decision.to_dict(),
                            "iteration": event.get("iteration_count", 0),
                        }

                    worker_results = event.get("worker_results") or []
                    for result in worker_results:
                        result_key = f"{result.worker_type.value}_{result.timestamp}"
                        if result_key not in seen_workers:
                            seen_workers.add(result_key)
                            yield {
                                "type": "worker",
                                "worker": result.worker_type.value,
                                "success": result.success,
                                "content_preview": (result.content or "")[:TOOL_PREVIEW_LENGTH],
                            }

                    final_response = event.get("final_response")
                    if final_response:
                        for char in final_response:
                            token_buffer += char
                            if len(token_buffer) >= STREAM_TOKEN_BATCH_SIZE:
                                yield {"type": "token", "content": token_buffer}
                                token_buffer = ""
                        if token_buffer:
                            yield {"type": "token", "content": token_buffer}
                            token_buffer = ""
                        answer = final_response

            try:
                state_cfg = {"configurable": dict((config_payload or {}).get("configurable") or {})}
                snapshot = graph.get_state(state_cfg)
                pending_interrupts = getattr(snapshot, "tasks", None)
                if pending_interrupts:
                    for task in pending_interrupts:
                        for intr in getattr(task, "interrupts", []):
                            interrupt_value = getattr(intr, "value", None)
                            if isinstance(interrupt_value, dict):
                                intr_type = interrupt_value.get("type", "")
                                if intr_type == "sql_approval":
                                    yield {
                                        "type": "sql_approval_request",
                                        "request_id": interrupt_value.get("request_id"),
                                        "sql": interrupt_value.get("sql"),
                                        "natural_query": interrupt_value.get("natural_query"),
                                        "operation_type": interrupt_value.get("operation_type"),
                                        "danger_level": interrupt_value.get("danger_level"),
                                        "affected_tables": interrupt_value.get("affected_tables", []),
                                        "estimated_rows_affected": interrupt_value.get("estimated_rows_affected"),
                                        "warnings": interrupt_value.get("warnings", []),
                                        "explanation": interrupt_value.get("explanation", ""),
                                        "message": interrupt_value.get("message", ""),
                                    }
                                elif intr_type in ("note_create_confirmation", "note_delete_confirmation", "note_update_confirmation"):
                                    yield {
                                        "type": "note_confirmation_request",
                                        "confirmation_type": intr_type,
                                        "note_id": interrupt_value.get("note_id", ""),
                                        "note_title": interrupt_value.get("note_title", ""),
                                        "action": "delete" if "delete" in intr_type else "create" if "create" in intr_type else "update",
                                        "update_type": interrupt_value.get("update_type"),
                                        "message": interrupt_value.get("message", ""),
                                        "options": interrupt_value.get("options", ["approve", "reject"]),
                                    }
            except Exception as intr_err:
                if "Subgraph thread not found" in str(intr_err):
                    log_debug(f"Interrupt check after resume skipped: {intr_err}")
                else:
                    log_warning(f"Failed to check for interrupts after resume: {intr_err}")

            phase_timings: Dict[str, int] = {}
            invoke_time_ms = int((time.time() - start_time) * 1000)
            phase_timings["total_ms"] = invoke_time_ms
            if final_state:
                phase_timings.update(final_state.get("timing") or {})

            try:
                if final_state:
                    redis_tool.save_graph_state(
                        thread_id=thread_id,
                        state={
                            "schema_version": final_state.get("schema_version", 1),
                            "messages": final_state.get("messages") or [],
                        },
                    )
            except Exception:
                pass

            stats = form.SELECTED_MODEL.get_overall_exec_stats()
            worker_results_list = []
            if final_state:
                worker_results = final_state.get("worker_results") or []
                worker_results_list = [r.to_dict() for r in worker_results]

            yield {
                "type": "final",
                "result": {
                    "answer": answer,
                    "stats": stats,
                    "timing": phase_timings,
                    "worker_results": worker_results_list,
                    "iterations": final_state.get("iteration_count", 0) if final_state else 0,
                    "approval_action": action,
                },
                "run_id": run_id,
            }

    except WorkflowError:
        raise
    except Exception as e:
        log_error(f"SQL approval resume failed: {e}")
        yield {"type": "error", "error": str(e), "run_id": run_id}


def resume_note_confirmation(
    *,
    thread_id: str,
    config: AgentConfig,
    decision: str,
    checkpoint_ns: str = "",
) -> Iterator[Dict[str, Any]]:
    """Resume workflow after note HITL confirmation (delete / full-rewrite).

    Uses LangGraph ``Command(resume=value)`` so the value reaches the
    ``interrupt()`` call inside the note handler.

    Args:
        thread_id: Thread to resume
        config: Agent configuration
        decision: "approve" or "reject"
        checkpoint_ns: Namespace

    Yields:
        Event dicts (same protocol as stream_workflow)
    """
    log_info(f"Resuming note confirmation for thread: {thread_id}, decision={decision}")

    checkpoint_ns = checkpoint_ns or config.state_scope

    if decision not in ("approve", "reject"):
        yield {"type": "error", "error": f"Invalid decision: {decision}. Must be 'approve' or 'reject'."}
        return

    resume_value = {"decision": decision}

    config_payload = build_config_payload(
        thread_id=thread_id,
        checkpoint_ns=checkpoint_ns,
    )

    run_id = uuid4().hex
    yield {"type": "run_started", "run_id": run_id, "thread_id": thread_id}

    try:
        with checkpoint_context() as checkpointer, memory_store_context() as store:
            graph = build_react_graph(
                config=config,
                checkpointer=checkpointer,
                store=store,
            )

            start_time = time.time()
            token_buffer = ""
            final_state = None
            answer = ""
            seen_workers = set()
            seen_decisions = 0
            event_count = 0

            stream_iter = graph.stream(
                Command(resume=resume_value),
                config=config_payload,
                stream_mode="values",
            )

            for event in stream_iter:
                event_count += 1
                if isinstance(event, dict):
                    final_state = event

                    decisions = event.get("supervisor_decisions") or []
                    if len(decisions) > seen_decisions:
                        latest_decision = decisions[-1]
                        seen_decisions = len(decisions)
                        yield {
                            "type": "supervisor",
                            "decision": latest_decision.to_dict(),
                            "iteration": event.get("iteration_count", 0),
                        }

                    worker_results = event.get("worker_results") or []
                    for result in worker_results:
                        result_key = f"{result.worker_type.value}_{result.timestamp}"
                        if result_key not in seen_workers:
                            seen_workers.add(result_key)
                            yield {
                                "type": "worker",
                                "worker": result.worker_type.value,
                                "success": result.success,
                                "content_preview": (result.content or "")[:TOOL_PREVIEW_LENGTH],
                            }

                    # Emit note_result events for sidebar updates
                    for result in worker_results:
                        if result.worker_type.value == "note" and result.success:
                            metadata = result.metadata or {}
                            action = metadata.get("action", "")
                            if action in ("create", "update", "delete"):
                                note_content = result.content or ""
                                note_id = metadata.get("note_id", "")
                                try:
                                    import json as _json
                                    parsed = _json.loads(note_content) if note_content.startswith("{") else {}
                                    note_id = note_id or parsed.get("note_id") or parsed.get("id", "")
                                except Exception:
                                    parsed = {}
                                yield {
                                    "type": "note_result",
                                    "action": action,
                                    "notes": [parsed] if parsed else [],
                                    "persisted_ids": [note_id] if note_id else [],
                                }

                    final_response = event.get("final_response")
                    if final_response:
                        for char in final_response:
                            token_buffer += char
                            if len(token_buffer) >= STREAM_TOKEN_BATCH_SIZE:
                                yield {"type": "token", "content": token_buffer}
                                token_buffer = ""
                        if token_buffer:
                            yield {"type": "token", "content": token_buffer}
                            token_buffer = ""
                        answer = final_response

            phase_timings: Dict[str, int] = {}
            invoke_time_ms = int((time.time() - start_time) * 1000)
            phase_timings["total_ms"] = invoke_time_ms
            if final_state:
                phase_timings.update(final_state.get("timing") or {})

            try:
                if final_state:
                    redis_tool.save_graph_state(
                        thread_id=thread_id,
                        state={
                            "schema_version": final_state.get("schema_version", 1),
                            "messages": final_state.get("messages") or [],
                        },
                    )
            except Exception:
                pass

            stats = form.SELECTED_MODEL.get_overall_exec_stats()
            worker_results_list = []
            if final_state:
                wr = final_state.get("worker_results") or []
                worker_results_list = [r.to_dict() for r in wr]

            yield {
                "type": "final",
                "result": {
                    "answer": answer,
                    "stats": stats,
                    "timing": phase_timings,
                    "worker_results": worker_results_list,
                    "iterations": final_state.get("iteration_count", 0) if final_state else 0,
                    "decision": decision,
                },
                "run_id": run_id,
            }

    except WorkflowError:
        raise
    except Exception as e:
        log_error(f"Note confirmation resume failed: {e}")
        yield {"type": "error", "error": str(e), "run_id": run_id}
