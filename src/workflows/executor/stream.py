"""
Streaming workflow execution entry point.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from core.settings import (
    AgentConfig,
    DEFAULT_MAX_ITERATIONS,
    TOOL_PREVIEW_LENGTH,
    STREAM_TOKEN_BATCH_SIZE,
)
from core.exceptions import WorkflowError
from infrastructure.llm import form
from infrastructure.cache.redis_cache import redis_tool
from infrastructure.telemetry.phoenix import (
    workflow_trace,
)
from services import source_capture
from utils.log import log_debug, log_error, log_info, log_warning
from workflows.checkpointer import (
    build_config_payload,
    checkpoint_context,
)
from workflows.memory_store import memory_store_context
from workflows.react_graph import build_react_graph
from workflows.state import (
    build_messages_from_history,
    create_initial_state,
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

    # Initialize the per-stream source accumulator. Tools (web/RAG) push
    # structured WebSource / DocSource payloads here; the ToolMessage
    # handler below drains them onto each `worker` event.
    source_capture.start_capture()

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
                answer = ""

                event_count = 0
                answer_streamed = False
                seen_tool_call_ids: set = set()

                # ── Per-message buffering ──
                # Buffer AI content per message ID so we can suppress text
                # that accompanies tool calls (e.g. "I'll delegate this...").
                # Content is only flushed to the client when we confirm the
                # message has no tool calls (new message starts, ToolMessage
                # arrives, or stream ends).
                _cur_msg_id: Optional[str] = None
                _msg_buffer = ""
                _msg_has_tools = False

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
                    chunk = None
                    meta = {}
                    if isinstance(stream_event, tuple) and len(stream_event) == 2:
                        first, second = stream_event
                        if isinstance(first, tuple):
                            # subgraphs=True: (namespace, (chunk, meta))
                            if isinstance(second, tuple) and len(second) == 2:
                                chunk, meta = second[0], second[1] if isinstance(second[1], dict) else {}
                            else:
                                chunk = second
                        elif isinstance(second, dict):
                            # (chunk, metadata)
                            chunk, meta = first, second
                        else:
                            chunk = first
                    if chunk is None:
                        continue

                    # Only stream chunks from agent and tools nodes;
                    # skip planner, guardrails, post_process, etc.
                    node_name = meta.get("langgraph_node", "") if isinstance(meta, dict) else ""
                    if node_name and node_name not in ("agent", "tools"):
                        continue

                    # ── AIMessageChunk: streaming tokens or tool calls ──
                    if isinstance(chunk, (AIMessage, AIMessageChunk)):
                        msg_id = getattr(chunk, "id", None)
                        content = getattr(chunk, "content", "") or ""
                        tool_calls = getattr(chunk, "tool_calls", None) or []
                        tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []

                        # ── New AI message started — flush the previous one ──
                        if msg_id and msg_id != _cur_msg_id:
                            # Flush previous message buffer (only if it was clean)
                            if _msg_buffer and not _msg_has_tools:
                                if not answer_streamed:
                                    answer_streamed = True
                                answer += _msg_buffer
                                yield {"type": "token", "content": _msg_buffer}
                            _cur_msg_id = msg_id
                            _msg_buffer = ""
                            _msg_has_tools = False

                        # ── Tool calls detected — suppress content for this message ──
                        if tool_calls or tool_call_chunks:
                            _msg_has_tools = True
                            _msg_buffer = ""  # discard any buffered content

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

                        # ── Buffer content (only for messages without tool calls) ──
                        if content and not _msg_has_tools:
                            _msg_buffer += content
                            # Progressive flush for large responses
                            if len(_msg_buffer) >= STREAM_TOKEN_BATCH_SIZE:
                                if not answer_streamed:
                                    answer_streamed = True
                                answer += _msg_buffer
                                yield {"type": "token", "content": _msg_buffer}
                                _msg_buffer = ""

                    # ── ToolMessage: tool result → Logic worker-result ──
                    elif isinstance(chunk, ToolMessage):
                        # Flush any pending AI message buffer before processing
                        # (it should already be marked as has_tools, but be safe)
                        if _msg_buffer and not _msg_has_tools:
                            if not answer_streamed:
                                answer_streamed = True
                            answer += _msg_buffer
                            yield {"type": "token", "content": _msg_buffer}
                        _msg_buffer = ""
                        _msg_has_tools = False
                        _cur_msg_id = None

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
                            "sources": source_capture.drain(),
                        }

                # Flush remaining message buffer
                if _msg_buffer and not _msg_has_tools:
                    if not answer_streamed:
                        answer_streamed = True
                    answer += _msg_buffer
                    yield {"type": "token", "content": _msg_buffer}
                    _msg_buffer = ""

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
