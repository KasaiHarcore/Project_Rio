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
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage

from backend.core.settings import (
    AgentConfig,
    DEFAULT_MAX_ITERATIONS,
    TOOL_PREVIEW_LENGTH,
    STREAM_TOKEN_BATCH_SIZE,
)
from backend.db.models.run import RunStatus
from backend.db.models.run_step import RunStepStatus, RunStepType
from backend.services.llm import form
from backend.services.run_service import run_service
from backend.services.run_step_service import run_step_service
from backend.services.tool_usage_service import (
    clear_tool_logging_context,
    set_tool_logging_context,
)
from backend.services.tools.redis_tool import redis_tool
from backend.telemetry.langsmith import (
    end_run_error,
    end_run_success,
    log_trace_link_hint,
    traced_span,
    workflow_trace,
)
from backend.utils.log import log_debug, log_error, log_info, log_success, log_warning
from backend.workflows.checkpointer import (
    build_config_payload,
    checkpoint_context,
    list_checkpoints as _list_checkpoints,
    load_checkpoint as _load_checkpoint,
)
from backend.workflows.graph import build_workflow_graph
from backend.workflows.state import (
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
    # Generate identifiers
    thread_id = thread_id or str(uuid4())
    run_id = uuid4().hex
    checkpoint_ns = checkpoint_ns or config.state_scope
    
    # Start run tracking
    run_service.start_run(
        run_id=run_id,
        thread_id=thread_id,
        mode=config.mode,
        model_name=getattr(form.SELECTED_MODEL, "name", None),
    )
    set_tool_logging_context(thread_id=thread_id, run_id=run_id)
    log_trace_link_hint(run_id)
    
    log_info(f"Starting workflow: run_id={run_id}, thread_id={thread_id}, mode={config.mode}")
    
    # Build checkpoint config
    config_payload = build_config_payload(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )
    
    # Tracking variables
    current_stage = "init"
    step_index = 0
    phase_timings: Dict[str, int] = {}
    worker_results_list: List[Dict[str, Any]] = []
    root_run = None
    
    def _start_step(step_type: RunStepType, name: str):
        nonlocal step_index
        step_id = run_step_service.start_step(
            run_id=run_id,
            step_index=step_index,
            step_type=step_type,
            name=name,
        )
        step_index += 1
        return step_id
    
    def _finish_step(step_id, status: RunStepStatus = RunStepStatus.SUCCEEDED):
        if step_id:
            run_step_service.finish_step(step_id=step_id, status=status)
    
    # Prepare trace inputs
    trace_inputs = {
        "question": question,
        "thread_id": thread_id,
        "run_id": run_id,
        "mode": config.mode,
        "history_items": len(history or []),
    }
    trace_tags = [
        "workflow:supervisor_worker",
        f"mode:{config.mode}",
        f"model:{getattr(form.SELECTED_MODEL, 'name', 'unknown')}",
    ]
    
    try:
        with workflow_trace(
            name="multi_agent.run_workflow",
            run_type="chain",
            inputs=trace_inputs,
            tags=trace_tags,
            metadata={"max_iterations": max_iterations},
        ) as _root:
            root_run = _root
            
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
                metadata={"run_id": run_id, "user_role": config.user_role},
            )
            
            # Execute with checkpointing
            current_stage = "execute"
            with checkpoint_context() as checkpointer:
                # Check if there's an existing completed checkpoint that would block execution
                if not checkpoint_id:  # Only clear if not explicitly resuming
                    try:
                        from backend.workflows.checkpointer import get_latest_checkpoint_state
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
                                            checkpoint_dt = datetime.fromtimestamp(float(ts))
                                        else:
                                            checkpoint_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                                        age_seconds = (datetime.utcnow() - checkpoint_dt.replace(tzinfo=None)).total_seconds()
                                        max_exec = int(getattr(config, "max_execution_seconds", 120) or 120)
                                        stale_in_progress = age_seconds > max(300, max_exec * 5)
                                    except Exception:
                                        stale_in_progress = False

                            is_terminal = (
                                status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAIL-ED, ExecutionStatus.WAITING_HUMAN)
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
                                from backend.workflows.checkpointer import delete_checkpoints
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
                
                # Build the graph
                graph = build_workflow_graph(
                    config=config,
                    checkpointer=checkpointer,
                )
                
                # Execute the workflow
                invoke_step_id = _start_step(RunStepType.LLM, "workflow.invoke")
                start_time = time.time()
                
                try:
                    with traced_span(
                        name="workflow.invoke",
                        run_type="chain",
                        inputs={"question": question[:TOOL_PREVIEW_LENGTH]},
                    ) as span:
                        # Invoke the graph with durable checkpoint writes.
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
                        
                        span.set_outputs({
                            "answer_preview": (answer or "")[:1200],
                            "iterations": final_state.get("iteration_count", 0),
                            "workers_used": [r.worker_type.value for r in worker_results],
                        })
                    
                    _finish_step(invoke_step_id, RunStepStatus.SUCCEEDED)
                    
                except Exception as e:
                    _finish_step(invoke_step_id, RunStepStatus.FAILED)
                    raise
                
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
            run_service.finish_run(run_id=run_id, status=RunStatus.SUCCEEDED)
            stats = form.SELECTED_MODEL.get_overall_exec_stats()
            
            end_run_success(
                run=root_run,
                outputs={
                    "answer_preview": (answer or "")[:2000],
                    "stats": stats,
                },
                metadata={"timings_ms": phase_timings},
            )
            
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
    
    except Exception as e:
        run_service.finish_run(run_id=run_id, status=RunStatus.FAILED, error=str(e))
        end_run_error(
            run=root_run,
            error=e,
            metadata={"failed_stage": current_stage, "run_id": run_id},
        )
        log_error(f"Workflow failed: {e}")
        
        return {
            "answer": "",
            "error": str(e),
            "run_id": run_id,
            "thread_id": thread_id,
            "status": "failed",
        }
    
    finally:
        clear_tool_logging_context()


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
    
    Yields:
        Event dictionaries
    """
    # Generate identifiers
    thread_id = thread_id or str(uuid4())
    run_id = uuid4().hex
    checkpoint_ns = checkpoint_ns or config.state_scope
    
    if not thread_id:
        raise ValueError("thread_id is required for streaming workflow")
    
    # Start run tracking
    run_service.start_run(
        run_id=run_id,
        thread_id=thread_id,
        mode=config.mode,
        model_name=getattr(form.SELECTED_MODEL, "name", None),
    )
    set_tool_logging_context(thread_id=thread_id, run_id=run_id)
    
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
    root_run = None
    
    try:
        with workflow_trace(
            name="multi_agent.stream_workflow",
            run_type="chain",
            inputs={"question": question, "thread_id": thread_id},
            tags=["workflow:supervisor_worker_stream", f"mode:{config.mode}"],
        ) as _root:
            root_run = _root
            
            # Build initial state
            history_messages = build_messages_from_history(history) if history else []
            initial_state = create_initial_state(
                question=question,
                thread_id=thread_id,
                mode=config.mode,
                user_id=user_id,
                history=history_messages,
                max_iterations=max_iterations,
                metadata={"run_id": run_id, "user_role": config.user_role},
            )
            
            # Execute with checkpointing
            current_stage = "execute"
            with checkpoint_context() as checkpointer:
                # Check if there's an existing completed checkpoint that would block execution
                # LangGraph doesn't re-run a graph if it's already at END state
                # So we need to clear the checkpoint for fresh execution
                if not checkpoint_id:  # Only clear if not explicitly resuming
                    try:
                        from backend.workflows.checkpointer import get_latest_checkpoint_state
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
                                            checkpoint_dt = datetime.fromtimestamp(float(ts))
                                        else:
                                            checkpoint_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                                        age_seconds = (datetime.utcnow() - checkpoint_dt.replace(tzinfo=None)).total_seconds()
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
                                from backend.workflows.checkpointer import delete_checkpoints
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
                
                graph = build_workflow_graph(
                    config=config,
                    checkpointer=checkpointer,
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
            run_service.finish_run(run_id=run_id, status=RunStatus.SUCCEEDED)
            stats = form.SELECTED_MODEL.get_overall_exec_stats()
            
            end_run_success(
                run=root_run,
                outputs={"answer_preview": (answer or "")[:2000]},
                metadata={"timings_ms": phase_timings},
            )
            
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
        run_service.finish_run(run_id=run_id, status=RunStatus.FAILED, error=str(e))
        end_run_error(
            run=root_run,
            error=e,
            metadata={"failed_stage": current_stage},
        )
        log_error(f"Streaming workflow failed: {e}")
        yield {"type": "error", "error": str(e), "run_id": run_id}
    
    finally:
        clear_tool_logging_context()


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
