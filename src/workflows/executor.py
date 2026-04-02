"""
Workflow Executor - Entry Points for Running Multi-agent Workflows.

This module provides the main functions for executing the multi-agent
supervisor-worker workflow:

- run_workflow: Execute synchronously and return final result
- stream_workflow: Stream execution with token-by-token output

Both functions support:
- Durable execution with PostgreSQL checkpointing
- Human-in-the-loop interruptions
- Time-travel (resume from any checkpoint)
- Full execution metadata and timing
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langgraph.types import Command

from utils.timezone import utc_now

from core.settings import (
    AgentConfig,
    DEFAULT_MAX_ITERATIONS,
    TOOL_PREVIEW_LENGTH,
    STREAM_TOKEN_BATCH_SIZE,
)
from core.exceptions import WorkflowError
from infrastructure.llm import form
from infrastructure.cache.redis_cache import redis_tool
from infrastructure.telemetry.langsmith import (
    log_trace_hint,
    workflow_trace,
)
from utils.log import log_debug, log_error, log_info, log_success, log_warning
from workflows.checkpointer import (
    build_config_payload,
    checkpoint_context,
    list_checkpoints as _list_checkpoints,
    load_checkpoint as _load_checkpoint,
)
from workflows.memory_store import memory_store_context
from workflows.react_graph import build_react_graph
from workflows.state import (
    AgentState,
    ExecutionStatus,
    build_messages_from_history,
    create_initial_state,
)


def _build_standard_mission_action_event(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build mission_action event for standard mission interactions."""
    return {
        "type": "mission_action",
        "action": action,
        "mission": payload.get("mission", {}),
        "step_index": payload.get("step_index"),
    }


def _build_delete_mission_action_event(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build mission_action event for mission deletion."""
    return {
        "type": "mission_action",
        "action": action,
        "mission": {
            "id": payload.get("mission_id"),
            "title": payload.get("title"),
        },
        "step_index": None,
    }


_MISSION_ACTION_EVENT_BUILDERS: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, Any]]] = {
    "toggle_step": _build_standard_mission_action_event,
    "complete_mission": _build_standard_mission_action_event,
    "update_mission": _build_standard_mission_action_event,
    "delete_mission": _build_delete_mission_action_event,
}


def _build_mission_action_event(action: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a mission event from action metadata using declarative dispatch."""
    builder = _MISSION_ACTION_EVENT_BUILDERS.get(action)
    if not builder:
        return None
    return builder(action, payload)


def run_workflow(
    *,
    question: str,
    config: AgentConfig,
    history: Optional[List[Dict[str, Any]]] = None,
    thread_id: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
    checkpoint_ns: Optional[str] = None,
    user_id: Optional[str] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> Dict[str, Any]:
    """
    Execute the multi-agent workflow synchronously.
    
    This is the main entry point for running the supervisor-worker
    workflow. It handles:
    - State initialization
    - Checkpoint management
    - Execution tracking
    - Error handling
    - Result collection
    
    Args:
        question: The user's question
        config: Agent configuration
        history: Optional conversation history
        thread_id: Thread ID for checkpointing (auto-generated if not provided)
        checkpoint_id: Specific checkpoint to resume from (time-travel)
        checkpoint_ns: Checkpoint namespace
        user_id: Optional user identifier
        max_iterations: Maximum supervisor iterations
    
    Returns:
        Result dictionary containing:
        - answer: Final response text
        - stats: Execution statistics
        - run_id: Unique run identifier
        - worker_results: Results from all workers
        - timing: Timing information
        - metadata: Additional execution metadata
    """
    thread_id = thread_id or str(uuid4())
    run_id = uuid4().hex
    checkpoint_ns = checkpoint_ns or config.state_scope
    
    log_trace_hint(run_id)
    log_info(f"Starting workflow: run_id={run_id}, thread_id={thread_id}, mode={config.mode}")
    
    config_payload = build_config_payload(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )
    
    current_stage = "init"
    phase_timings: Dict[str, int] = {}
    worker_results_list: List[Dict[str, Any]] = []
    
    try:
        with workflow_trace(
            name="multi_agent.run_workflow",
            tags=[
                "workflow:supervisor_worker",
                f"mode:{config.mode}",
                f"model:{getattr(form.SELECTED_MODEL, 'name', 'unknown')}",
            ],
            metadata={
                "run_id": run_id,
                "thread_id": thread_id,
                "mode": config.mode,
                "max_iterations": max_iterations,
                "history_items": len(history or []),
            },
        ) as trace_cfg:
            config_payload.update(trace_cfg or {})
            
            current_stage = "build_state"
            history_messages = build_messages_from_history(history) if history else []
            
            initial_state = create_initial_state(
                question=question,
                thread_id=thread_id,
                mode=config.mode,
                user_id=user_id,
                history=history_messages,
                max_iterations=max_iterations,
                metadata={"run_id": run_id, "user_role": config.user_role, "character": config.character},
            )
            
            current_stage = "execute"
            with checkpoint_context() as checkpointer, memory_store_context() as store:
                if not checkpoint_id:  # Only clear if not explicitly resuming
                    try:
                        from workflows.checkpointer import get_latest_checkpoint_state
                        existing = get_latest_checkpoint_state(
                            thread_id=thread_id,
                            checkpoint_ns=checkpoint_ns,
                        )
                        if existing:
                            checkpoint_state = existing.get("checkpoint", {})
                            channel_values = checkpoint_state.get("channel_values", {})
                            checkpoint_question = (channel_values.get("original_question") or "").strip()
                            checkpoint_mode = (channel_values.get("mode") or "").strip()
                            log_info(
                                "Found existing checkpoint: "
                                f"ns={checkpoint_ns!r} status={channel_values.get('status')} "
                                f"mode={checkpoint_mode!r} question={checkpoint_question[:120]!r}"
                            )
                            status = channel_values.get("status")
                            try:
                                status_str = (status.value if hasattr(status, "value") else str(status or "")).lower()
                            except Exception:
                                status_str = str(status or "").lower()

                            question_mismatch = bool(checkpoint_question) and checkpoint_question != (question or "").strip()
                            mode_mismatch = bool(checkpoint_mode) and checkpoint_mode != (config.mode or "").strip()

                            stale_in_progress = False
                            if status_str in (ExecutionStatus.PENDING.value, ExecutionStatus.RUNNING.value):
                                ts = checkpoint_state.get("ts")
                                if ts:
                                    try:
                                        if isinstance(ts, (int, float)):
                                            checkpoint_dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                                        else:
                                            checkpoint_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                                        if checkpoint_dt.tzinfo is None:
                                            checkpoint_dt = checkpoint_dt.replace(tzinfo=timezone.utc)
                                        age_seconds = (utc_now() - checkpoint_dt).total_seconds()
                                        max_exec = int(getattr(config, "max_execution_seconds", 120) or 120)
                                        stale_in_progress = age_seconds > max(300, max_exec * 5)
                                    except Exception:
                                        stale_in_progress = False

                            is_terminal = (
                                status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.WAITING_HUMAN)
                                or status_str in (
                                    ExecutionStatus.COMPLETED.value,
                                    ExecutionStatus.FAILED.value,
                                    ExecutionStatus.WAITING_HUMAN.value,
                                )
                                or status_str.endswith(f".{ExecutionStatus.COMPLETED.value}")
                                or status_str.endswith(f".{ExecutionStatus.FAILED.value}")
                                or status_str.endswith(f".{ExecutionStatus.WAITING_HUMAN.value}")
                            )

                            if is_terminal or question_mismatch or mode_mismatch or stale_in_progress:
                                if is_terminal:
                                    reason = "terminal checkpoint"
                                elif question_mismatch:
                                    reason = "question mismatch"
                                elif mode_mismatch:
                                    reason = "mode mismatch"
                                else:
                                    reason = "stale in-progress checkpoint"
                                log_info(f"Clearing checkpoint for fresh execution ({reason})")
                                from workflows.checkpointer import delete_checkpoints
                                deleted = delete_checkpoints(thread_id=thread_id, checkpoint_ns=checkpoint_ns)
                                log_info(f"Deleted {deleted} checkpoints (ns={checkpoint_ns!r})")
                                try:
                                    redis_tool.delete_graph_state(thread_id=thread_id)
                                    log_debug(f"Cleared Redis graph state for thread {thread_id}")
                                except Exception as redis_err:
                                    log_warning(f"Failed to clear Redis graph state: {redis_err}")
                    except Exception as e:
                        log_warning(f"Failed to check/clear checkpoint: {e}")
                
                graph = build_react_graph(
                    config=config,
                    checkpointer=checkpointer,
                    store=store,
                    user_id=user_id,
                    question=question,
                )

                # Inject planner config into the configurable dict
                rio_cfg = getattr(graph, "_rio_config", {})
                if rio_cfg:
                    config_payload.setdefault("configurable", {}).update(rio_cfg)

                start_time = time.time()

                final_state = graph.invoke(
                    initial_state,
                    config=config_payload,
                    durability="sync",
                )
                
                # Extract answer from last AIMessage in messages
                answer = ""
                messages = final_state.get("messages") or []
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and msg.content:
                        tool_calls = getattr(msg, "tool_calls", None)
                        if not tool_calls:
                            answer = msg.content
                            break

                invoke_time_ms = int((time.time() - start_time) * 1000)
                phase_timings["total_ms"] = invoke_time_ms

                try:
                    # Truncate to last 50 messages to prevent unbounded state growth
                    checkpoint_messages = (final_state.get("messages") or [])[-50:]
                    redis_tool.save_graph_state(
                        thread_id=thread_id,
                        state={"messages": checkpoint_messages},
                    )
                except Exception as e:
                    log_warning(f"Failed to save state to Redis: {e}")

            stats = form.SELECTED_MODEL.get_overall_exec_stats()
            log_success(f"Workflow completed: run_id={run_id}")

            return {
                "answer": answer,
                "stats": stats,
                "run_id": run_id,
                "thread_id": thread_id,
                "timing": phase_timings,
                "status": "success",
            }
    
    except WorkflowError:
        raise
    except Exception as e:
        log_error(f"Workflow failed at {current_stage}: {e}")
        raise WorkflowError(
            f"Workflow failed at {current_stage}: {e}",
            details={"run_id": run_id, "thread_id": thread_id, "stage": current_stage},
        )


def stream_workflow(
    *,
    question: str,
    config: AgentConfig,
    history: Optional[List[Dict[str, Any]]] = None,
    thread_id: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
    checkpoint_ns: Optional[str] = None,
    user_id: Optional[str] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    user_api_keys: Optional[Dict[str, Optional[str]]] = None,
) -> Iterator[Dict[str, Any]]:
    """
    Stream the multi-agent workflow execution.

    Yields events during execution:
    - {"type": "start", "run_id": ...}
    - {"type": "worker", "worker": "...", "content": "..."}
    - {"type": "supervisor", "decision": {...}}
    - {"type": "token", "content": "..."}
    - {"type": "final", "result": {...}}
    - {"type": "error", "error": "..."}

    Args:
        question: The user's question
        config: Agent configuration
        history: Optional conversation history
        thread_id: Thread ID for checkpointing
        checkpoint_id: Checkpoint to resume from
        checkpoint_ns: Checkpoint namespace
        user_id: Optional user identifier
        max_iterations: Maximum supervisor iterations
        user_api_keys: User's API keys for external services (tavily, cohere, etc.)

    Yields:
        Event dictionaries
    """
    thread_id = thread_id or str(uuid4())
    run_id = uuid4().hex
    checkpoint_ns = checkpoint_ns or config.state_scope
    
    if not thread_id:
        raise ValueError("thread_id is required for streaming workflow")
    
    log_info(f"Starting streaming workflow: run_id={run_id}, question={question[:100]}")
    
    yield {"type": "run_started", "run_id": run_id, "thread_id": thread_id}
    log_debug("Emitted run_started event")
    
    config_payload = build_config_payload(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )
    
    current_stage = "init"
    phase_timings: Dict[str, int] = {}
    answer = ""
    
    try:
        with workflow_trace(
            name="multi_agent.stream_workflow",
            tags=["workflow:supervisor_worker_stream", f"mode:{config.mode}"],
            metadata={
                "run_id": run_id,
                "thread_id": thread_id,
                "mode": config.mode,
                "max_iterations": max_iterations,
            },
        ) as trace_cfg:
            config_payload.update(trace_cfg or {})
            
            history_messages = build_messages_from_history(history) if history else []
            state_metadata = {
                "run_id": run_id,
                "user_role": config.user_role,
                "character": config.character,
            }
            if user_api_keys:
                state_metadata["user_api_keys"] = user_api_keys

            initial_state = create_initial_state(
                question=question,
                thread_id=thread_id,
                mode=config.mode,
                user_id=user_id,
                history=history_messages,
                max_iterations=max_iterations,
                metadata=state_metadata,
            )
            
            current_stage = "execute"
            with checkpoint_context() as checkpointer, memory_store_context() as store:
                # ── Always clear checkpoint for new requests ──
                # The ReAct graph is rebuilt fresh each time with current emotional
                # context and memories.  Stale checkpoints cause the agent to replay
                # old answers instead of processing the new question.
                if not checkpoint_id:
                    try:
                        from workflows.checkpointer import delete_checkpoints
                        deleted = delete_checkpoints(thread_id=thread_id, checkpoint_ns=checkpoint_ns)
                        if deleted:
                            log_info(f"Cleared {deleted} stale checkpoint(s) for thread {thread_id}")
                        try:
                            redis_tool.delete_graph_state(thread_id=thread_id)
                        except Exception:
                            pass
                    except Exception as e:
                        log_warning(f"Failed to clear checkpoint: {e}")

                graph = build_react_graph(
                    config=config,
                    checkpointer=checkpointer,
                    store=store,
                    user_id=user_id,
                    question=question,
                )

                # Inject planner config into the configurable dict
                rio_cfg = getattr(graph, "_rio_config", {})
                if rio_cfg:
                    config_payload.setdefault("configurable", {}).update(rio_cfg)

                start_time = time.time()
                token_buffer = ""
                answer = ""

                event_count = 0
                answer_streamed = False
                seen_tool_call_ids: set = set()

                log_info("Starting graph.stream() with stream_mode='messages'...")

                # ── Use stream_mode="messages" for real-time streaming ──
                # This yields individual message chunks as they are produced
                # INSIDE the ReAct agent loop, not after the entire subgraph
                # finishes.  Each yielded item is (message_chunk, metadata).
                stream_iter = graph.stream(
                    initial_state,
                    config=config_payload,
                    stream_mode="messages",
                    subgraphs=True,
                )

                for stream_event in stream_iter:
                    event_count += 1

                    # stream_mode="messages" with subgraphs=True yields:
                    #   (namespace_tuple, (message_chunk, metadata))
                    # Without subgraphs it yields:
                    #   (message_chunk, metadata)
                    if isinstance(stream_event, tuple) and len(stream_event) == 2:
                        first, second = stream_event
                        if isinstance(first, tuple):
                            # subgraphs=True: (namespace, (chunk, meta))
                            chunk = second[0] if isinstance(second, tuple) else second
                        elif isinstance(second, dict):
                            # (chunk, metadata)
                            chunk = first
                        else:
                            chunk = first
                    else:
                        continue

                    # ── AIMessageChunk: streaming tokens or tool calls ──
                    if isinstance(chunk, (AIMessage, AIMessageChunk)):
                        content = getattr(chunk, "content", "") or ""
                        tool_calls = getattr(chunk, "tool_calls", None) or []
                        tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []

                        # Emit Logic events for tool calls (delegation / direct)
                        for tc in tool_calls:
                            tc_id = tc.get("id", "")
                            if tc_id and tc_id not in seen_tool_call_ids:
                                seen_tool_call_ids.add(tc_id)
                                tool_name = tc.get("name", "unknown")
                                if tool_name.startswith("delegate_"):
                                    domain = tool_name.replace("delegate_", "").replace("_task", "")
                                    yield {
                                        "type": "supervisor",
                                        "decision": {
                                            "action": "delegate",
                                            "worker": domain,
                                            "reasoning": str(tc.get("args", {}).get("instruction", ""))[:80],
                                            "confidence": None,
                                        },
                                        "iteration": event_count,
                                    }
                                else:
                                    yield {
                                        "type": "supervisor",
                                        "decision": {
                                            "action": "delegate",
                                            "worker": tool_name,
                                            "reasoning": f"Calling {tool_name}",
                                            "confidence": None,
                                        },
                                        "iteration": event_count,
                                    }

                        # Stream text tokens in real-time (skip tool-call-only chunks)
                        if content and not tool_calls and not tool_call_chunks:
                            if not answer_streamed:
                                answer_streamed = True
                            answer += content
                            token_buffer += content
                            if len(token_buffer) >= STREAM_TOKEN_BATCH_SIZE:
                                yield {"type": "token", "content": token_buffer}
                                token_buffer = ""

                    # ── ToolMessage: tool result → Logic worker-result ──
                    elif isinstance(chunk, ToolMessage):
                        raw_name = getattr(chunk, "name", "tool")
                        # Clean up tool name for display
                        display_name = raw_name
                        if raw_name.startswith("delegate_"):
                            display_name = raw_name.replace("delegate_", "").replace("_task", "") + " agent"
                        content = getattr(chunk, "content", "") or ""
                        yield {
                            "type": "worker",
                            "worker": display_name,
                            "success": True,
                            "content_preview": content[:TOOL_PREVIEW_LENGTH] if content else "",
                        }

                # Flush remaining token buffer
                if token_buffer:
                    yield {"type": "token", "content": token_buffer}
                    token_buffer = ""

                # Collect full answer from the final graph state
                if not answer:
                    try:
                        state_cfg = {"configurable": dict((config_payload or {}).get("configurable") or {})}
                        final_snapshot = graph.get_state(state_cfg)
                        if final_snapshot and final_snapshot.values:
                            msgs = final_snapshot.values.get("messages") or []
                            for msg in reversed(msgs):
                                if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                                    answer = msg.content
                                    break
                    except Exception:
                        pass
                
                invoke_time_ms = int((time.time() - start_time) * 1000)
                phase_timings["total_ms"] = invoke_time_ms

                log_info(f"Graph streaming completed: {event_count} events, answer={bool(answer)}")

                if event_count == 0:
                    log_warning("No graph events emitted - graph may have returned cached checkpoint state")

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
                                        log_info(f"SQL approval interrupt detected: {interrupt_value.get('request_id')}")
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
                                        log_info(f"Note confirmation interrupt detected: {intr_type} note_id={interrupt_value.get('note_id')}")
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
                        log_debug(f"Interrupt check skipped: {intr_err}")
                    else:
                        log_warning(f"Failed to check for interrupts: {intr_err}")

                try:
                    redis_tool.save_graph_state(
                        thread_id=thread_id,
                        state={"answer": answer[:2000] if answer else ""},
                    )
                except Exception:
                    pass

            stats = form.SELECTED_MODEL.get_overall_exec_stats()

            yield {
                "type": "final",
                "result": {
                    "answer": answer,
                    "stats": stats,
                    "timing": phase_timings,
                    "iterations": event_count,
                },
                "run_id": run_id,
            }

    except Exception as e:
        log_error(f"Streaming workflow failed at {current_stage}: {e}")
        yield {"type": "error", "error": str(e), "run_id": run_id}


def list_checkpoints(
    *,
    thread_id: str,
    checkpoint_ns: str = "",
    limit: int = 20,
    before_checkpoint_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List checkpoints for a thread.
    
    Args:
        thread_id: Thread to list checkpoints for
        checkpoint_ns: Namespace filter
        limit: Maximum results
        before_checkpoint_id: Pagination cursor
    
    Returns:
        List of checkpoint metadata
    """
    return _list_checkpoints(
        thread_id=thread_id,
        checkpoint_ns=checkpoint_ns,
        limit=limit,
        before_checkpoint_id=before_checkpoint_id,
    )


def load_checkpoint(
    *,
    thread_id: str,
    checkpoint_id: str,
    checkpoint_ns: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Load a specific checkpoint.
    
    Args:
        thread_id: Thread the checkpoint belongs to
        checkpoint_id: Checkpoint to load
        checkpoint_ns: Namespace
    
    Returns:
        Checkpoint data or None
    """
    return _load_checkpoint(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )


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
