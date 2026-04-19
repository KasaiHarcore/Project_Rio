"""Chat endpoints: streaming conversation, thread listing, message history."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from core.concurrency import concurrency_manager
from core.dependencies import (
    get_current_user,
    get_cache_service,
    get_chat_service,
)
from core.exceptions import NotFoundError, ValidationError
from infrastructure.cache.helpers import best_effort
from infrastructure.cache.service import CacheService
from models.user import User
from protocols.sse_stream import (
    data_event,
    done,
    error_event,
    finish_message,
    finish_step,
    start_message,
    start_step,
    text_delta,
    text_end,
    text_start,
)
from schemas.chat import (
    ChatRequest,
    EditRequest,
    MemoryListResponse,
    MemoryResponse,
    MessageListResponse,
    MessageResponse,
    RegenerateRequest,
    ThreadListResponse,
    ThreadPatchRequest,
    ThreadResponse,
)
from services.agent_service import AgentService
from services.chat_history_service import chat_history_service
from services.chat_service import ChatService
from utils.log import log_error, log_info


router = APIRouter(prefix="/chat", tags=["chat"])


def _safe_stats(stats: dict | None) -> dict:
    """Return a JSON-safe subset of execution stats."""
    if not stats:
        return {}
    return {
        "total_tokens": stats.get("total_tokens", 0),
        "total_input_tokens": stats.get("total_input_tokens", 0),
        "total_output_tokens": stats.get("total_output_tokens", 0),
        "total_cost": stats.get("total_cost", 0),
    }


@router.post("")
async def chat_stream(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    svc: ChatService = Depends(get_chat_service),
):
    """Stream an AI response using AI SDK v6 UIMessageStream (SSE)."""
    request_model_params = {
        k: v for k, v in {
            "temperature": body.temperature,
            "max_tokens": body.max_tokens,
            "top_p": body.top_p,
            "frequency_penalty": body.frequency_penalty,
            "presence_penalty": body.presence_penalty,
        }.items() if v is not None
    }

    prep = svc.prepare_chat(
        user=user,
        messages=body.messages,
        thread_id=body.thread_id,
        mode=body.mode,
        character=body.character,
        workspace_context=body.workspace_context,
        request_model_params=request_model_params or None,
    )

    def _generate():
        """Sync generator - emits SSE lines. Guarantees envelope closure on error."""
        answer_parts: list[str] = []
        run_id = None
        final_stats = None
        text_part_id = uuid4().hex[:12]
        text_started = False
        had_error = False
        logic_entries: list[dict] = []
        accumulated_sources: list[dict] = []
        # Pre-allocate the assistant message UUID so we can echo it on the
        # `message-persisted` SSE event below — the frontend transport
        # uses it to flush its in-flight source buffer onto the right
        # UIMessage id (the persistence write is fire-and-forget async).
        assistant_message_id = str(uuid4())
        # Tail of the message chain inside this turn. Starts at the user
        # message that triggered the run; advances as we persist tool
        # rows so each tool's parent_id chains correctly:
        #   user → tool₁ → tool₂ → … → assistant_final → next_user
        last_message_id: str | None = prep.user_message_id
        # Number of sources already accumulated; lets us slice "this
        # tool's sources" off the tail when persisting per-tool.
        sources_consumed = 0

        yield start_message()
        yield start_step()

        try:
            for event in AgentService().stream_query(
                question=prep.effective_question,
                config=prep.config,
                history=prep.history,
                thread_id=prep.thread_id,
                user_id=str(prep.user_id),
                user_api_key=prep.user_api_key,
                user_model_params=prep.user_model_params,
                user_api_keys=prep.user_api_keys,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    chunk = event.get("content", "")
                    if not text_started:
                        yield text_start(text_part_id)
                        text_started = True
                    answer_parts.append(chunk)
                    yield text_delta(text_part_id, chunk)

                elif event_type == "run_started":
                    run_id = event.get("run_id")
                    yield data_event("run-started", {
                        "run_id": run_id,
                        "thread_id": event.get("thread_id"),
                        "character": prep.config.character,
                    })
                    logic_entries.append({
                        "title": "Workflow started",
                        "detail": f"Agent: {prep.config.character}" if prep.config.character else None,
                        "kind": "info",
                    })

                elif event_type == "supervisor":
                    decision = event.get("decision", {})
                    action = decision.get("action")
                    worker = decision.get("worker") or decision.get("next_worker")
                    reasoning = decision.get("reasoning", "")
                    confidence = decision.get("confidence")
                    yield data_event("supervisor-decision", {
                        "action": action,
                        "worker": worker,
                        "reasoning": reasoning,
                        "confidence": confidence,
                        "iteration": event.get("iteration", 0),
                    })
                    conf_str = f" ({round(confidence * 100)}%)" if isinstance(confidence, (int, float)) else ""
                    if action == "respond":
                        title = "Responding directly"
                    elif action == "clarify":
                        title = "Asking for clarification"
                    else:
                        title = f"Routing → {worker}"
                    logic_entries.append({
                        "title": title,
                        "detail": f"{reasoning}{conf_str}" if reasoning else None,
                        "kind": "decision",
                    })

                elif event_type == "worker":
                    worker_name = event.get("worker", "unknown")
                    success = event.get("success", True)
                    sources = event.get("sources") or []
                    content_preview = event.get("content_preview", "")
                    yield data_event("worker-result", {
                        "worker": worker_name,
                        "success": success,
                        "content_preview": content_preview,
                        "sources": sources,
                    })
                    if sources:
                        accumulated_sources.extend(sources)
                    logic_entries.append({
                        "title": f"{worker_name} completed" if success else f"{worker_name} failed",
                        "detail": str(content_preview)[:200] or None,
                        "kind": "tool-call",
                    })

                    # Persist this tool result as its own Message row so the
                    # tree-view can render it as a first-class node, chained
                    # off whatever came before it in this turn.
                    tool_message_id = str(uuid4())
                    tool_metadata: dict | None = None
                    if sources:
                        tool_metadata = {"sources": sources}
                    try:
                        svc.persist_tool_message(
                            user_id=prep.user_id,
                            thread_id=prep.thread_id,
                            content=str(content_preview or ""),
                            tool_name=worker_name,
                            message_id=tool_message_id,
                            parent_id=last_message_id,
                            run_id=run_id,
                            metadata=tool_metadata,
                        )
                    except Exception as tool_persist_err:
                        log_error(f"Failed to persist tool message: {tool_persist_err}")

                    yield data_event("tool-message-persisted", {
                        "message_id": tool_message_id,
                        "parent_id": last_message_id,
                        "tool_name": worker_name,
                        "content": content_preview or "",
                        "sources": sources,
                    })
                    sources_consumed += len(sources)
                    last_message_id = tool_message_id

                elif event_type == "planning":
                    content = event.get("content", "")
                    yield data_event("planning", {
                        "content": content,
                    })
                    if content:
                        logic_entries.append({
                            "title": "Execution plan",
                            "detail": content[:200],
                            "kind": "thinking",
                        })

                elif event_type == "note_result":
                    yield data_event("note-result", {
                        "action": event.get("action", "create"),
                        "notes": event.get("notes", []),
                        "persisted_ids": event.get("persisted_ids", []),
                    })

                elif event_type == "artifact_result":
                    yield data_event("artifact-result", {
                        "artifacts": event.get("artifacts", []),
                        "persisted_ids": event.get("persisted_ids", []),
                    })

                elif event_type == "mission_result":
                    yield data_event("mission-result", {
                        "missions": event.get("missions", []),
                        "persisted_ids": event.get("persisted_ids", []),
                    })

                elif event_type == "mission_action":
                    yield data_event("mission-action", {
                        "action": event.get("action"),
                        "mission": event.get("mission", {}),
                        "step_index": event.get("step_index"),
                    })

                elif event_type == "note_confirmation_request":
                    yield data_event("note-confirmation-request", {
                        "confirmation_type": event.get("confirmation_type"),
                        "note_id": event.get("note_id", ""),
                        "note_title": event.get("note_title", ""),
                        "action": event.get("action", "delete"),
                        "update_type": event.get("update_type"),
                        "message": event.get("message", ""),
                        "options": event.get("options", ["approve", "reject"]),
                    })

                elif event_type == "sql_approval_request":
                    yield data_event("sql-approval-request", {
                        "request_id": event.get("request_id"),
                        "sql": event.get("sql"),
                        "natural_query": event.get("natural_query"),
                        "operation_type": event.get("operation_type"),
                        "danger_level": event.get("danger_level"),
                        "affected_tables": event.get("affected_tables", []),
                        "estimated_rows_affected": event.get("estimated_rows_affected"),
                        "warnings": event.get("warnings", []),
                        "explanation": event.get("explanation", ""),
                        "message": event.get("message", ""),
                    })

                elif event_type == "stage_assessment":
                    yield data_event("stage-assessment", event.get("data", {}))

                elif event_type == "intervention_decision":
                    yield data_event("intervention-decision", event.get("data", {}))

                elif event_type == "next_step":
                    yield data_event("next-step", event.get("data", {}))

                elif event_type == "emotional_update":
                    yield data_event("emotional-update", {
                        "mood": event.get("mood"),
                        "energy": event.get("energy"),
                        "affinity": event.get("affinity"),
                        "relationship_tier": event.get("relationship_tier"),
                        "mood_changed": event.get("mood_changed", False),
                        "streak_days": event.get("streak_days", 0),
                        "interaction_count": event.get("interaction_count", 0),
                    })

                elif event_type == "final":
                    result = event.get("result", {})
                    run_id = event.get("run_id") or run_id
                    final_stats = result.get("stats")

                    final_answer = result.get("answer", "")
                    if not answer_parts and final_answer:
                        if not text_started:
                            yield text_start(text_part_id)
                            text_started = True
                        answer_parts.append(final_answer)
                        yield text_delta(text_part_id, final_answer)

                    yield data_event("final", {
                        "run_id": run_id,
                        "stats": _safe_stats(final_stats),
                        "worker_results": result.get("worker_results", []),
                        "iterations": result.get("iterations", 0),
                        "timing": result.get("timing", {}),
                    })

                    timing = result.get("timing", {})
                    iterations = result.get("iterations", 0)
                    parts: list[str] = []
                    if iterations > 0:
                        parts.append(f"{iterations} iteration(s)")
                    total_ms = timing.get("total_ms")
                    if isinstance(total_ms, (int, float)):
                        parts.append(f"{total_ms / 1000:.1f}s")
                    logic_entries.append({
                        "title": "Workflow complete",
                        "detail": " · ".join(parts) if parts else None,
                        "kind": "info",
                    })

                elif event_type == "error":
                    error_msg = event.get("error", "Unknown error")
                    had_error = True
                    yield error_event(error_msg)

        except GeneratorExit:
            log_info("Client disconnected mid-stream")
            return
        except Exception as exc:
            log_error(f"Streaming error: {exc}")
            had_error = True
            yield error_event(str(exc))

        # --- Guaranteed cleanup: always close the SSE envelope ---
        if text_started:
            yield text_end(text_part_id)

        full_answer = "".join(answer_parts)

        # Build metadata with logic entries + sources for persistence
        msg_metadata: dict | None = None
        if logic_entries or accumulated_sources:
            msg_metadata = {}
            if logic_entries:
                msg_metadata["logic_entries"] = logic_entries
            if accumulated_sources:
                msg_metadata["sources"] = accumulated_sources

        try:
            if full_answer:
                # Chain parent_id off the LAST tool row (if any tools ran)
                # so the message tree reads:
                #   user → tool₁ → tool₂ → … → assistant
                # Falls back to the original branching path when the user
                # supplied an explicit parent_message_id (regenerate flow).
                effective_assistant_parent = (
                    body.parent_message_id
                    or (last_message_id if last_message_id != prep.user_message_id else None)
                )
                svc.persist_assistant_message(
                    user_id=prep.user_id,
                    thread_id=prep.thread_id,
                    content=full_answer,
                    run_id=run_id,
                    character_id=prep.config.character,
                    parent_id=effective_assistant_parent,
                    user_message_id=prep.user_message_id,
                    message_id=assistant_message_id,
                    metadata=msg_metadata,
                )
                # Echo the pre-allocated UUID + the full source set so the
                # frontend transport can flush its in-flight buffer onto the
                # correct UIMessage id (the async write may not have committed
                # yet, but the id is stable).
                yield data_event("message-persisted", {
                    "message_id": assistant_message_id,
                    "sources": accumulated_sources,
                })
        except Exception as persist_err:
            log_error(f"Failed to persist assistant message: {persist_err}")

        if not had_error:
            try:
                from workflows.agent_tools.note_tools import find_contextual_notes

                ctx_notes = find_contextual_notes(
                    query=prep.effective_question,
                    user_id=str(prep.user_id),
                    k=3,
                )
                if ctx_notes:
                    yield data_event("contextual-notes", {"notes": ctx_notes})
            except Exception:
                pass

        finish_reason = "error" if had_error else "stop"
        yield finish_step()
        yield finish_message(finish_reason)
        yield done()

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "X-Thread-Id": prep.thread_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/threads/{thread_id}/regenerate")
async def regenerate_response(
    thread_id: str,
    body: RegenerateRequest,
    user: User = Depends(get_current_user),
    svc: ChatService = Depends(get_chat_service),
):
    """Regenerate an assistant response for a user message, creating a new branch."""
    prep = svc.prepare_regeneration(
        user=user,
        thread_id=thread_id,
        message_id=body.message_id,
        character=body.character,
    )

    # The parent of the new assistant message is the target user message
    parent_msg_id = body.message_id

    def _generate():
        answer_parts: list[str] = []
        run_id = None
        final_stats = None
        text_part_id = uuid4().hex[:12]
        text_started = False
        had_error = False

        yield start_message()
        yield start_step()

        try:
            for event in AgentService().stream_query(
                question=prep.effective_question,
                config=prep.config,
                history=prep.history,
                thread_id=prep.thread_id,
                user_id=str(prep.user_id),
                user_api_key=prep.user_api_key,
                user_model_params=prep.user_model_params,
                user_api_keys=prep.user_api_keys,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    chunk = event.get("content", "")
                    if not text_started:
                        yield text_start(text_part_id)
                        text_started = True
                    answer_parts.append(chunk)
                    yield text_delta(text_part_id, chunk)

                elif event_type == "run_started":
                    run_id = event.get("run_id")
                    yield data_event("run-started", {
                        "run_id": run_id,
                        "thread_id": event.get("thread_id"),
                        "character": prep.config.character,
                    })

                elif event_type == "supervisor":
                    decision = event.get("decision", {})
                    yield data_event("supervisor-decision", {
                        "action": decision.get("action"),
                        "worker": decision.get("worker") or decision.get("next_worker"),
                        "reasoning": decision.get("reasoning", ""),
                        "confidence": decision.get("confidence"),
                        "iteration": event.get("iteration", 0),
                    })

                elif event_type == "worker":
                    yield data_event("worker-result", {
                        "worker": event.get("worker"),
                        "success": event.get("success"),
                        "content_preview": event.get("content_preview", ""),
                    })

                elif event_type == "planning":
                    yield data_event("planning", {
                        "content": event.get("content", ""),
                    })

                elif event_type == "final":
                    result = event.get("result", {})
                    run_id = event.get("run_id") or run_id
                    final_stats = result.get("stats")

                    final_answer = result.get("answer", "")
                    if not answer_parts and final_answer:
                        if not text_started:
                            yield text_start(text_part_id)
                            text_started = True
                        answer_parts.append(final_answer)
                        yield text_delta(text_part_id, final_answer)

                    yield data_event("final", {
                        "run_id": run_id,
                        "stats": _safe_stats(final_stats),
                        "worker_results": result.get("worker_results", []),
                        "iterations": result.get("iterations", 0),
                        "timing": result.get("timing", {}),
                    })

                elif event_type == "error":
                    error_msg = event.get("error", "Unknown error")
                    had_error = True
                    yield error_event(error_msg)

        except GeneratorExit:
            log_info("Client disconnected mid-stream (regenerate)")
            return
        except Exception as exc:
            log_error(f"Regeneration streaming error: {exc}")
            had_error = True
            yield error_event(str(exc))

        if text_started:
            yield text_end(text_part_id)

        full_answer = "".join(answer_parts)

        try:
            if full_answer:
                svc.persist_assistant_message(
                    user_id=prep.user_id,
                    thread_id=prep.thread_id,
                    content=full_answer,
                    run_id=run_id,
                    character_id=prep.config.character,
                    parent_id=parent_msg_id,
                )
        except Exception as persist_err:
            log_error(f"Failed to persist regenerated message: {persist_err}")

        finish_reason = "error" if had_error else "stop"
        yield finish_step()
        yield finish_message(finish_reason)
        yield done()

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "X-Thread-Id": prep.thread_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/threads/{thread_id}/edit")
async def edit_message(
    thread_id: str,
    body: EditRequest,
    user: User = Depends(get_current_user),
    svc: ChatService = Depends(get_chat_service),
):
    """Edit a previously-sent user message, creating a new sibling branch.

    The edit produces a new user message (sibling of the original via
    shared parent_id) plus a streamed assistant response as its child.
    The original branch stays intact; the frontend's branch carousel
    lets users flip between the two.
    """
    prep = svc.prepare_edit(
        user=user,
        thread_id=thread_id,
        message_id=body.message_id,
        new_content=body.new_content,
        character=body.character,
    )

    # The assistant reply's parent is the new user message we just created.
    parent_msg_id = prep.user_message_id

    def _generate():
        answer_parts: list[str] = []
        run_id = None
        final_stats = None
        text_part_id = uuid4().hex[:12]
        text_started = False
        had_error = False

        yield start_message()
        yield start_step()

        try:
            for event in AgentService().stream_query(
                question=prep.effective_question,
                config=prep.config,
                history=prep.history,
                thread_id=prep.thread_id,
                user_id=str(prep.user_id),
                user_api_key=prep.user_api_key,
                user_model_params=prep.user_model_params,
                user_api_keys=prep.user_api_keys,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    chunk = event.get("content", "")
                    if not text_started:
                        yield text_start(text_part_id)
                        text_started = True
                    answer_parts.append(chunk)
                    yield text_delta(text_part_id, chunk)

                elif event_type == "run_started":
                    run_id = event.get("run_id")
                    yield data_event("run-started", {
                        "run_id": run_id,
                        "thread_id": event.get("thread_id"),
                        "character": prep.config.character,
                    })

                elif event_type == "supervisor":
                    decision = event.get("decision", {})
                    yield data_event("supervisor-decision", {
                        "action": decision.get("action"),
                        "worker": decision.get("worker") or decision.get("next_worker"),
                        "reasoning": decision.get("reasoning", ""),
                        "confidence": decision.get("confidence"),
                        "iteration": event.get("iteration", 0),
                    })

                elif event_type == "worker":
                    yield data_event("worker-result", {
                        "worker": event.get("worker"),
                        "success": event.get("success"),
                        "content_preview": event.get("content_preview", ""),
                    })

                elif event_type == "planning":
                    yield data_event("planning", {
                        "content": event.get("content", ""),
                    })

                elif event_type == "final":
                    result = event.get("result", {})
                    run_id = event.get("run_id") or run_id
                    final_stats = result.get("stats")

                    final_answer = result.get("answer", "")
                    if not answer_parts and final_answer:
                        if not text_started:
                            yield text_start(text_part_id)
                            text_started = True
                        answer_parts.append(final_answer)
                        yield text_delta(text_part_id, final_answer)

                    yield data_event("final", {
                        "run_id": run_id,
                        "stats": _safe_stats(final_stats),
                        "worker_results": result.get("worker_results", []),
                        "iterations": result.get("iterations", 0),
                        "timing": result.get("timing", {}),
                    })

                elif event_type == "error":
                    error_msg = event.get("error", "Unknown error")
                    had_error = True
                    yield error_event(error_msg)

        except GeneratorExit:
            log_info("Client disconnected mid-stream (edit)")
            return
        except Exception as exc:
            log_error(f"Edit streaming error: {exc}")
            had_error = True
            yield error_event(str(exc))

        if text_started:
            yield text_end(text_part_id)

        full_answer = "".join(answer_parts)

        try:
            if full_answer:
                svc.persist_assistant_message(
                    user_id=prep.user_id,
                    thread_id=prep.thread_id,
                    content=full_answer,
                    run_id=run_id,
                    character_id=prep.config.character,
                    parent_id=parent_msg_id,
                )
        except Exception as persist_err:
            log_error(f"Failed to persist edited-branch message: {persist_err}")

        finish_reason = "error" if had_error else "stop"
        yield finish_step()
        yield finish_message(finish_reason)
        yield done()

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "X-Thread-Id": prep.thread_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service),
):
    """List the authenticated user's conversation threads."""
    uid_str = str(user.id)

    cached = cache.get_cached_threads(uid_str)
    if cached is not None:
        return ThreadListResponse(
            threads=[ThreadResponse(**t) for t in cached[:limit]]
        )

    def _query():
        threads = chat_history_service.list_threads(user_id=user.id, limit=limit)
        thread_list = [
            ThreadResponse(
                id=str(t.id),
                title=t.title,
                status=t.status.value if hasattr(t.status, "value") else str(t.status),
                is_starred=getattr(t, "is_starred", False),
                is_pinned=getattr(t, "is_pinned", False),
                created_at=t.created_at.isoformat() if t.created_at else "",
                updated_at=t.updated_at.isoformat() if t.updated_at else "",
            )
            for t in threads
        ]

        best_effort(cache.set_cached_threads, uid_str, [t.model_dump() for t in thread_list])

        return ThreadListResponse(threads=thread_list)

    return await concurrency_manager.run_in_thread(_query)


@router.get("/threads/{thread_id}/messages", response_model=MessageListResponse)
async def get_thread_messages(
    thread_id: str,
    limit: int = Query(200, ge=1, le=1000),
    user: User = Depends(get_current_user),
):
    """Retrieve messages for a specific thread (must be owned by user)."""
    try:
        tid = UUID(thread_id)
    except ValueError:
        raise ValidationError("Invalid thread ID")

    def _query():
        thread = chat_history_service.get_thread_if_owned(tid, user.id)
        if not thread:
            raise NotFoundError("Thread not found")

        messages = chat_history_service.get_messages(thread_id=tid, limit=limit)
        return MessageListResponse(
            messages=[
                MessageResponse(
                    id=str(m.id),
                    role=m.role.value if hasattr(m.role, "value") else str(m.role),
                    content=m.content,
                    created_at=m.created_at.isoformat() if m.created_at else "",
                    character_id=getattr(m, "character_id", None),
                    parent_id=str(m.parent_id) if getattr(m, "parent_id", None) else None,
                    metadata=getattr(m, "metadata_", None),
                )
                for m in messages
            ]
        )

    return await concurrency_manager.run_in_thread(_query)


@router.get("/threads/{thread_id}/memories", response_model=MemoryListResponse)
async def get_thread_memories(
    thread_id: str,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    """Retrieve persisted memories for a specific thread (must be owned by user)."""
    from workflows.memory_store import memory_store_context, list_memories_by_thread

    try:
        tid = UUID(thread_id)
    except ValueError:
        raise ValidationError("Invalid thread ID")

    def _query():
        thread = chat_history_service.get_thread_if_owned(tid, user.id)
        if not thread:
            raise NotFoundError("Thread not found")

        try:
            with memory_store_context() as store:
                memories = list_memories_by_thread(
                    store,
                    user_id=str(user.id),
                    thread_id=thread_id,
                    limit=limit,
                )
        except Exception as e:
            log_error(f"Failed to fetch memories for thread {thread_id}: {e}")
            memories = []

        return MemoryListResponse(
            thread_id=thread_id,
            memories=[MemoryResponse(**m) for m in memories],
        )

    return await concurrency_manager.run_in_thread(_query)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service),
):
    """Delete a conversation thread (soft-archive or hard delete)."""
    try:
        tid = UUID(thread_id)
    except ValueError:
        raise ValidationError("Invalid thread ID")

    def _query():
        thread = chat_history_service.get_thread_if_owned(tid, user.id)
        if not thread:
            raise NotFoundError("Thread not found")

        chat_history_service.hard_delete_thread(tid)

        uid_str = str(user.id)
        best_effort(cache.invalidate_threads, uid_str)
        best_effort(cache.invalidate_dashboard, uid_str)

    await concurrency_manager.run_in_thread(_query)
    return None


@router.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str,
    body: ThreadPatchRequest,
    user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service),
):
    """Partially update a thread (rename, star, pin, archive)."""
    try:
        tid = UUID(thread_id)
    except ValueError:
        raise ValidationError("Invalid thread ID")

    def _query():
        thread_snapshot = chat_history_service.update_thread(
            thread_id=tid,
            user_id=user.id,
            title=body.title,
            status=body.status,
            is_starred=body.is_starred,
            is_pinned=body.is_pinned,
        )
        if not thread_snapshot:
            raise NotFoundError("Thread not found")

        best_effort(cache.invalidate_threads, str(user.id))

        return ThreadResponse(
            id=thread_snapshot["id"],
            title=thread_snapshot["title"],
            status=thread_snapshot["status"],
            is_starred=thread_snapshot["is_starred"],
            is_pinned=thread_snapshot["is_pinned"],
            created_at=thread_snapshot["created_at"],
            updated_at=thread_snapshot["updated_at"],
        )

    return await concurrency_manager.run_in_thread(_query)
