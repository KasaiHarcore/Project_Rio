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
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
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
from workflows.graph import build_workflow_graph
from workflows.state import (
    AgentState,
    ExecutionStatus,
    WorkerType,
    build_messages_from_history,
    create_initial_state,
    extract_answer_from_state,
    get_gathered_context,
)


# =============================================================================
# Main Execution Functions
# =============================================================================

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
    # Identifiers
    thread_id = thread_id or str(uuid4())
    run_id = uuid4().hex
    checkpoint_ns = checkpoint_ns or config.state_scope
    
    log_trace_hint(run_id)
    log_info(f"Starting workflow: run_id={run_id}, thread_id={thread_id}, mode={config.mode}")
    
    # Build checkpoint config
    config_payload = build_config_payload(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )
    
    # Tracking
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
            
            # Build initial state
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
            
            # Execute with checkpointing (short-term) and memory store (long-term)
            current_stage = "execute"
            with checkpoint_context() as checkpointer, memory_store_context() as store:
                # Check if there's an existing completed checkpoint that would block execution
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

                            # Detect mismatches that should force a fresh execution.
                            question_mismatch = bool(checkpoint_question) and checkpoint_question != (question or "").strip()
                            mode_mismatch = bool(checkpoint_mode) and checkpoint_mode != (config.mode or "").strip()

                            # If a previous in-progress run got stuck, don't keep resuming it forever.
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
                                # Also clear Redis graph state to prevent stale data
                                try:
                                    redis_tool.delete_graph_state(thread_id=thread_id)
                                    log_debug(f"Cleared Redis graph state for thread {thread_id}")
                                except Exception as redis_err:
                                    log_warning(f"Failed to clear Redis graph state: {redis_err}")
                    except Exception as e:
                        log_warning(f"Failed to check/clear checkpoint: {e}")
                
                # Build the graph with checkpointer (short-term) and store (long-term)
                graph = build_workflow_graph(
                    config=config,
                    checkpointer=checkpointer,
                    store=store,
                )
                
                # Execute the workflow (auto-traced by LangSmith via config metadata)
                start_time = time.time()
                
                final_state = graph.invoke(
                    initial_state,
                    config=config_payload,
                    durability="sync",
                )
                
                # Extract results
                answer = extract_answer_from_state(final_state)
                worker_results = final_state.get("worker_results") or []
                worker_results_list = [r.to_dict() for r in worker_results]
                phase_timings = final_state.get("timing") or {}
                
                invoke_time_ms = int((time.time() - start_time) * 1000)
                phase_timings["total_ms"] = invoke_time_ms
                
                # Save state to Redis for quick access
                try:
                    redis_tool.save_graph_state(
                        thread_id=thread_id,
                        state={
                            "schema_version": final_state.get("schema_version", 1),
                            "messages": final_state.get("messages") or [],
                        },
                    )
                except Exception as e:
                    log_warning(f"Failed to save state to Redis: {e}")
            
            # Finalize
            stats = form.SELECTED_MODEL.get_overall_exec_stats()
            log_success(f"Workflow completed: run_id={run_id}")
            
            return {
                "answer": answer,
                "stats": stats,
                "run_id": run_id,
                "thread_id": thread_id,
                "worker_results": worker_results_list,
                "timing": phase_timings,
                "iterations": final_state.get("iteration_count", 0),
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
    # Generate identifiers
    thread_id = thread_id or str(uuid4())
    run_id = uuid4().hex
    checkpoint_ns = checkpoint_ns or config.state_scope
    
    if not thread_id:
        raise ValueError("thread_id is required for streaming workflow")
    
    log_info(f"Starting streaming workflow: run_id={run_id}, question={question[:100]}")
    
    # Emit run_started event (frontend expects this name)
    yield {"type": "run_started", "run_id": run_id, "thread_id": thread_id}
    log_debug("Emitted run_started event")
    
    # Build checkpoint config
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
            
            # Build initial state
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
            
            # Execute with checkpointing (short-term) and memory store (long-term)
            current_stage = "execute"
            with checkpoint_context() as checkpointer, memory_store_context() as store:
                # Check if there's an existing completed checkpoint that would block execution
                # LangGraph doesn't re-run a graph if it's already at END state
                # So we need to clear the checkpoint for fresh execution
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
                            # Check if the previous run reached a terminal state.
                            # NOTE: the graph stores `status` as an ExecutionStatus enum, not its `.value`.
                            status = channel_values.get("status")
                            status_str = None
                            try:
                                status_str = (status.value if hasattr(status, "value") else str(status or "")).lower()
                            except Exception:
                                status_str = str(status or "").lower()

                            # If a new question arrives on the same thread_id, we must not resume
                            # an old in-progress checkpoint with a different `original_question`.
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
                                log_info(f"Clearing checkpoint for fresh execution (thread_id={thread_id}, {reason})")
                                from workflows.checkpointer import delete_checkpoints
                                deleted = delete_checkpoints(thread_id=thread_id, checkpoint_ns=checkpoint_ns)
                                log_info(f"Deleted {deleted} checkpoints (ns={checkpoint_ns!r})")
                                # Also clear Redis graph state to prevent stale data
                                try:
                                    redis_tool.delete_graph_state(thread_id=thread_id)
                                    log_debug(f"Cleared Redis graph state for thread {thread_id}")
                                except Exception as redis_err:
                                    log_warning(f"Failed to clear Redis graph state: {redis_err}")
                    except Exception as e:
                        log_warning(f"Failed to check/clear checkpoint: {e}")
                
                # Build the graph with checkpointer (short-term) and store (long-term)
                graph = build_workflow_graph(
                    config=config,
                    checkpointer=checkpointer,
                    store=store,
                )
                
                start_time = time.time()
                token_buffer = ""
                final_state = None
                
                # Stream the graph execution
                seen_workers = set()
                seen_decisions = 0
                event_count = 0
                
                log_info("Starting graph.stream() iteration...")
                log_debug(f"Initial state: original_question={initial_state.get('original_question')[:100] if initial_state.get('original_question') else 'None'}")
                log_debug(f"Initial state: final_response={initial_state.get('final_response')}")
                log_debug(f"Initial state: status={initial_state.get('status')}")
                
                stream_iter = graph.stream(
                    initial_state,
                    config=config_payload,
                    stream_mode="values",
                    durability="sync",
                )

                for event in stream_iter:
                    event_count += 1
                    log_debug(f"Graph event {event_count}: keys={list(event.keys()) if isinstance(event, dict) else type(event)}")
                    
                    # Log important state fields
                    if isinstance(event, dict):
                        log_debug(f"  -> status={event.get('status')}, final_response={bool(event.get('final_response'))}")
                        log_debug(f"  -> iteration_count={event.get('iteration_count')}, workers={len(event.get('worker_results') or [])}")
                    # event is the current state after each node
                    if isinstance(event, dict):
                        final_state = event

                        # Check for guardrail state changes
                        if event.get("guardrail_passed") is not None:
                            yield {
                                "type": "guardrail",
                                "guardrail": "input",
                                "passed": event["guardrail_passed"],
                                "reason": event.get("guardrail_rejection") or "",
                            }
                        if event.get("guardrail_output_passed") is not None:
                            yield {
                                "type": "guardrail",
                                "guardrail": "output",
                                "passed": event["guardrail_output_passed"],
                                "reason": event.get("guardrail_output_rejection") or "",
                            }

                        # Check for supervisor decisions
                        decisions = event.get("supervisor_decisions") or []
                        if len(decisions) > seen_decisions:
                            latest_decision = decisions[-1]
                            seen_decisions = len(decisions)
                            yield {
                                "type": "supervisor",
                                "decision": latest_decision.to_dict(),
                                "iteration": event.get("iteration_count", 0),
                            }
                        
                        # Check for worker results
                        worker_results = event.get("worker_results") or []
                        for result in worker_results:
                            result_key = f"{result.worker_type.value}_{result.timestamp}"
                            if result_key not in seen_workers:
                                seen_workers.add(result_key)
                                
                                # Emit planning event for planning worker (frontend shows this)
                                if result.worker_type.value == "planning" and result.success:
                                    yield {
                                        "type": "planning",
                                        "content": result.content,
                                    }
                                
                                # Emit note_result for note worker (frontend renders sticky notes)
                                # Also persist to DB so notes survive page reloads.
                                if result.worker_type.value == "note" and result.success and result.content:
                                    try:
                                        import json as _json
                                        notes = _json.loads(result.content)
                                        if isinstance(notes, list) and notes:
                                            # Persist to database
                                            persisted_note_ids: list[str] = []
                                            if user_id:
                                                try:
                                                    from services.note_service import NoteService
                                                    from uuid import UUID as _UUID
                                                    saved = NoteService.create_notes_from_agent(
                                                        user_id=_UUID(user_id),
                                                        notes_json=notes,
                                                        thread_id=thread_id,
                                                    )
                                                    persisted_note_ids = [str(n.id) for n in saved]
                                                    log_info(f"Persisted {len(saved)} agent notes to DB")
                                                except Exception as db_err:
                                                    log_warning(f"Failed to persist agent notes: {db_err}")

                                            yield {
                                                "type": "note_result",
                                                "notes": notes,
                                                "persisted_ids": persisted_note_ids,
                                            }
                                    except Exception:
                                        pass
                                
                                # Emit mission_result for mission worker (frontend renders on Mission Page)
                                # Also persist to DB so missions survive page reloads.
                                if result.worker_type.value == "mission" and result.success and result.content:
                                    try:
                                        import json as _json2
                                        missions = _json2.loads(result.content)
                                        if isinstance(missions, list) and missions:
                                            # Persist to database
                                            persisted_ids: list[str] = []
                                            if user_id:
                                                try:
                                                    from services.mission_service import MissionService
                                                    from uuid import UUID as _UUID
                                                    saved = MissionService.create_missions_from_agent(
                                                        user_id=_UUID(user_id),
                                                        missions_json=missions,
                                                        thread_id=thread_id,
                                                    )
                                                    persisted_ids = [str(m.id) for m in saved]
                                                    log_info(f"Persisted {len(saved)} agent missions to DB")
                                                except Exception as db_err:
                                                    log_warning(f"Failed to persist agent missions: {db_err}")

                                            yield {
                                                "type": "mission_result",
                                                "missions": missions,
                                                "persisted_ids": persisted_ids,
                                            }
                                    except Exception:
                                        pass
                                
                                # Emit worker event
                                yield {
                                    "type": "worker",
                                    "worker": result.worker_type.value,
                                    "success": result.success,
                                    "content_preview": (result.content or "")[:TOOL_PREVIEW_LENGTH],
                                }
                        
                        # Check for final response
                        final_response = event.get("final_response")
                        if final_response:
                            # Stream the final response token by token
                            for char in final_response:
                                token_buffer += char
                                if len(token_buffer) >= STREAM_TOKEN_BATCH_SIZE:
                                    yield {"type": "token", "content": token_buffer}
                                    token_buffer = ""
                            
                            if token_buffer:
                                yield {"type": "token", "content": token_buffer}
                                token_buffer = ""
                            
                            answer = final_response
                
                invoke_time_ms = int((time.time() - start_time) * 1000)
                phase_timings["total_ms"] = invoke_time_ms

                log_info(f"Graph streaming completed: {event_count} events, answer={bool(answer)}")

                # Detect if graph didn't actually run (returned checkpoint state)
                if event_count == 0:
                    log_warning("No graph events emitted - graph may have returned cached checkpoint state")

                # ── Interrupt detection ────────────────────────────
                # When the SQL worker calls interrupt(), the stream
                # ends silently.  Check the graph snapshot for
                # pending interrupts and emit them to the frontend.
                try:
                    state_cfg = {"configurable": dict((config_payload or {}).get("configurable") or {})}
                    snapshot = graph.get_state(state_cfg)
                    pending_interrupts = getattr(snapshot, "tasks", None)
                    if pending_interrupts:
                        for task in pending_interrupts:
                            for intr in getattr(task, "interrupts", []):
                                interrupt_value = getattr(intr, "value", None)
                                if isinstance(interrupt_value, dict) and interrupt_value.get("type") == "sql_approval":
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
                except Exception as intr_err:
                    if "Subgraph thread not found" in str(intr_err):
                        log_debug(f"Interrupt check skipped: {intr_err}")
                    else:
                        log_warning(f"Failed to check for interrupts: {intr_err}")

                if final_state:
                    phase_timings.update(final_state.get("timing") or {})
                
                # Save to Redis
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
            
            # Finalize
            stats = form.SELECTED_MODEL.get_overall_exec_stats()

            # Emit emotional update if present
            if final_state:
                emotional_ctx = final_state.get("emotional_context")
                if emotional_ctx and isinstance(emotional_ctx, dict):
                    yield {
                        "type": "emotional_update",
                        **emotional_ctx,
                    }

            # Final result
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
                },
                "run_id": run_id,
            }

    except Exception as e:
        log_error(f"Streaming workflow failed at {current_stage}: {e}")
        yield {"type": "error", "error": str(e), "run_id": run_id}


# =============================================================================
# Checkpoint Management Functions
# =============================================================================

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
    
    # Load the checkpoint state
    checkpoint_data = load_checkpoint(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )
    
    if not checkpoint_data:
        return {"error": f"Checkpoint not found: {checkpoint_id}", "status": "failed"}
    
    # If human response provided, add it to the input
    # The graph will continue from the checkpoint with the new input
    
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

    # Validate the approval response
    action = approval_response.get("action", "reject")
    valid_actions = {"approve", "edit", "reject", "always_approve"}
    if action not in valid_actions:
        yield {"type": "error", "error": f"Invalid action: {action}. Must be one of {valid_actions}"}
        return

    # Build the resume value that will be received by interrupt() in SQL worker
    # The SQL worker expects: {"action": "approve"|"edit"|"reject", "modified_sql": "...", "reason": "..."}
    resume_value: Dict[str, Any] = {"action": action}

    if action == "always_approve":
        # "always_approve" behaves like "approve" for this query,
        # but we also set a flag in thread metadata below.
        resume_value["action"] = "approve"

    if action == "edit":
        edited_sql = approval_response.get("edited_sql", "").strip()
        if not edited_sql:
            yield {"type": "error", "error": "edited_sql is required when action is 'edit'"}
            return
        resume_value["modified_sql"] = edited_sql

    if approval_response.get("reason"):
        resume_value["reason"] = approval_response["reason"]

    # Build config for resuming
    config_payload = build_config_payload(
        thread_id=thread_id,
        checkpoint_ns=checkpoint_ns,
    )

    run_id = uuid4().hex

    yield {"type": "run_started", "run_id": run_id, "thread_id": thread_id}

    try:
        with checkpoint_context() as checkpointer, memory_store_context() as store:
            graph = build_workflow_graph(
                config=config,
                checkpointer=checkpointer,
                store=store,
            )

            # If "always_approve", set the auto-approve flag in graph state
            # so future SQL operations in this thread skip the interrupt.
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

            # Resume with Command(resume=value) — this delivers the value
            # directly to the interrupt() call in the SQL worker.
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

                    # Supervisor decisions
                    decisions = event.get("supervisor_decisions") or []
                    if len(decisions) > seen_decisions:
                        latest_decision = decisions[-1]
                        seen_decisions = len(decisions)
                        yield {
                            "type": "supervisor",
                            "decision": latest_decision.to_dict(),
                            "iteration": event.get("iteration_count", 0),
                        }

                    # Worker results
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

                    # Final response tokens
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

            # Check for new interrupts (e.g. retry with re-approval)
            try:
                state_cfg = {"configurable": dict((config_payload or {}).get("configurable") or {})}
                snapshot = graph.get_state(state_cfg)
                pending_interrupts = getattr(snapshot, "tasks", None)
                if pending_interrupts:
                    for task in pending_interrupts:
                        for intr in getattr(task, "interrupts", []):
                            interrupt_value = getattr(intr, "value", None)
                            if isinstance(interrupt_value, dict) and interrupt_value.get("type") == "sql_approval":
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

            # Save to Redis
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

            # Final result
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
