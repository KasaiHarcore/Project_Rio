"""
Synchronous workflow execution entry point.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage

from utils.timezone import utc_now

from core.settings import (
    AgentConfig,
    DEFAULT_MAX_ITERATIONS,
)
from core.exceptions import WorkflowError
from infrastructure.llm import form
from infrastructure.cache.redis_cache import redis_tool
from infrastructure.telemetry.phoenix import (
    log_trace_hint,
    workflow_trace,
)
from utils.log import log_debug, log_error, log_info, log_success, log_warning
from workflows.checkpointer import (
    build_config_payload,
    checkpoint_context,
)
from workflows.memory_store import memory_store_context
from workflows.react_graph import build_react_graph
from workflows.state import (
    ExecutionStatus,
    build_messages_from_history,
    create_initial_state,
)


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
