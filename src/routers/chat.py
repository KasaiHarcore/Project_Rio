"""Chat endpoints: streaming conversation, thread listing, message history.

The streaming endpoint uses the **AI SDK v6 UIMessageStream** protocol
(Server-Sent Events) so that both text tokens *and* structured sidebar
events (supervisor decisions, worker results, stats …) travel in a single
HTTP response.

Protocol reference (ai@6.0+ / @ai-sdk/react):
  Each SSE event is: ``data: {json}\\n\\n``
  UIMessageChunk types used:
    {"type":"start"}                          – message start
    {"type":"start-step"}                     – step start
    {"type":"text-start","id":"..."}          – begin text part
    {"type":"text-delta","id":"...","delta":"..."} – text token
    {"type":"text-end","id":"..."}            – end text part
    {"type":"data-<name>","data":{...}}       – custom data (sidebar events)
    {"type":"finish-step"}                    – step finished
    {"type":"finish","finishReason":"stop"}   – message finished
  Final event: ``data: [DONE]\\n\\n``
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from core.concurrency import concurrency_manager
from core.dependencies import (
    get_current_user,
    get_cache_service,
    get_chat_service,
)
from core.exceptions import NotFoundError, ValidationError
from infrastructure.cache.service import CacheService
from models.message import MessageRole
from models.user import User
from services.agent_service import AgentService
from services.chat_history_service import chat_history_service
from services.chat_service import ChatService
from utils.log import log_error


router = APIRouter(prefix="/chat", tags=["chat"])


# ── SSE / UIMessageStream helpers (AI SDK v6) ──────────────────────────────

def _sse(payload: dict | str) -> str:
    """Wrap a JSON payload (or raw string like ``[DONE]``) as an SSE data line."""
    data = payload if isinstance(payload, str) else json.dumps(payload, separators=(",", ":"))
    return f"data: {data}\n\n"


def _text_start(part_id: str) -> str:
    return _sse({"type": "text-start", "id": part_id})


def _text_delta(part_id: str, delta: str) -> str:
    return _sse({"type": "text-delta", "id": part_id, "delta": delta})


def _text_end(part_id: str) -> str:
    return _sse({"type": "text-end", "id": part_id})


def _data_event(name: str, data: dict) -> str:
    """Emit a custom ``data-<name>`` UIMessageChunk.

    AI SDK v6 allows custom data types whose ``type`` starts with ``data-``.
    """
    return _sse({"type": f"data-{name}", "data": data})


def _start_message() -> str:
    return _sse({"type": "start"})


def _start_step() -> str:
    return _sse({"type": "start-step"})


def _finish_step() -> str:
    return _sse({"type": "finish-step"})


def _finish_message(reason: str = "stop") -> str:
    return _sse({"type": "finish", "finishReason": reason})


def _error_event(message: str) -> str:
    return _sse({"type": "error", "errorText": message})


def _done() -> str:
    return _sse("[DONE]")


# ── Request / Response schemas ──────────────────────────────────────────────

class ChatMessage(BaseModel):
    """Single message from the Vercel AI SDK useChat hook.

    AI SDK v6 may omit ``content`` and send ``parts`` instead.
    The validator derives ``content`` from text parts when missing.
    """
    model_config = {"extra": "allow"}
    role: str = Field(..., description="Message role: user | assistant | system | tool")
    content: Optional[str] = Field(None, description="Message text (derived from parts if absent)")
    id: Optional[str] = Field(None, description="AI SDK message ID")
    parts: Optional[List[Dict[str, Any]]] = Field(None, description="Structured message parts from AI SDK")
    tool_invocations: Optional[List[Dict[str, Any]]] = Field(None, alias="toolInvocations", description="Tool call data")

    @model_validator(mode="after")
    def _derive_content_from_parts(self) -> "ChatMessage":
        """If content is missing, build it from text parts."""
        if not self.content and self.parts:
            text_pieces = [
                p.get("text", "") for p in self.parts if p.get("type") == "text"
            ]
            self.content = "".join(text_pieces)
        if not self.content:
            self.content = ""
        return self


class WorkspaceChunk(BaseModel):
    """A single code chunk from a workspace file."""
    filePath: str = Field(..., description="Source file name")
    chunkName: str = Field(..., description="Function/class/block name")
    chunkKind: str = Field(..., description="Kind: function | class | interface | import | module")
    startLine: int = Field(..., description="Start line (1-based)")
    endLine: int = Field(..., description="End line (1-based)")
    content: str = Field(..., description="Chunk source code")


class WorkspaceFileTree(BaseModel):
    """Summary of a file's structure."""
    filePath: str
    tree: str


class WorkspaceContext(BaseModel):
    """Smart-chunked workspace context sent from the frontend."""
    file_trees: List[WorkspaceFileTree] = Field(default_factory=list)
    chunks: List[WorkspaceChunk] = Field(default_factory=list)
    total_tokens: int = Field(0)


class ChatRequest(BaseModel):
    """Body sent by the Vercel AI SDK useChat hook.

    Extra fields from the SDK (e.g. data, options) are preserved via extra="allow".
    Per-request model parameters override saved user settings when provided.
    """
    model_config = {"extra": "allow"}
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    thread_id: Optional[str] = Field(None, description="Existing thread ID to continue")
    mode: Optional[str] = Field("chat", description="Agent mode: chat | rag | web | sql")
    character: Optional[str] = Field("rio", description="Persona ID: rio")
    workspace_context: Optional[WorkspaceContext] = Field(None, description="Smart-chunked code context from workspace files")
    # Per-request model parameter overrides (take precedence over saved settings)
    temperature: Optional[float] = Field(None, ge=0, le=2, description="Sampling temperature (0-2)")
    max_tokens: Optional[int] = Field(None, ge=1, le=100000, description="Max tokens to generate")
    top_p: Optional[float] = Field(None, ge=0, le=1, description="Nucleus sampling (0-1)")
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2, description="Frequency penalty (-2 to 2)")
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2, description="Presence penalty (-2 to 2)")


class ThreadResponse(BaseModel):
    id: str
    title: Optional[str] = None
    status: str
    is_starred: bool = False
    is_pinned: bool = False
    created_at: str
    updated_at: str


class ThreadListResponse(BaseModel):
    success: bool = True
    threads: List[ThreadResponse]


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    character_id: Optional[str] = None


class MessageListResponse(BaseModel):
    success: bool = True
    messages: List[MessageResponse]


class MemoryResponse(BaseModel):
    key: str
    text: str
    memory_type: str = ""
    source: str = ""
    created_at: str = ""
    mode: str = ""


class MemoryListResponse(BaseModel):
    success: bool = True
    thread_id: str
    memories: List[MemoryResponse]


# ── Streaming chat ──────────────────────────────────────────────────────────

@router.post("")
async def chat_stream(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    svc: ChatService = Depends(get_chat_service),
):
    """Stream an AI response.

    Compatible with Vercel AI SDK ``useChat`` – returns a ``text/plain``
    stream of UTF-8 token chunks that the SDK accumulates on the client.
    """
    # Collect per-request model param overrides (only non-None values)
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
        """Sync generator – emits AI SDK v6 UIMessageStream (SSE) lines."""
        answer_parts: list[str] = []
        run_id = None
        final_stats = None
        text_part_id = uuid4().hex[:12]
        text_started = False

        # ── Message envelope ────────────────────────────────────
        yield _start_message()
        yield _start_step()

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

                # ── Text token ──────────────────────────────────
                if event_type == "token":
                    chunk = event.get("content", "")
                    if not text_started:
                        yield _text_start(text_part_id)
                        text_started = True
                    answer_parts.append(chunk)
                    yield _text_delta(text_part_id, chunk)

                # ── Run started ─────────────────────────────────
                elif event_type == "run_started":
                    run_id = event.get("run_id")
                    yield _data_event("run-started", {
                        "run_id": run_id,
                        "thread_id": event.get("thread_id"),
                        "character": prep.config.character,
                    })

                # ── Supervisor decision ─────────────────────────
                elif event_type == "supervisor":
                    decision = event.get("decision", {})
                    yield _data_event("supervisor-decision", {
                        "action": decision.get("action"),
                        "worker": decision.get("next_worker"),
                        "reasoning": decision.get("reasoning", ""),
                        "confidence": decision.get("confidence", 1.0),
                        "iteration": event.get("iteration", 0),
                    })

                # ── Worker result ───────────────────────────────
                elif event_type == "worker":
                    yield _data_event("worker-result", {
                        "worker": event.get("worker"),
                        "success": event.get("success"),
                        "content_preview": event.get("content_preview", ""),
                    })

                # ── Planning ────────────────────────────────────
                elif event_type == "planning":
                    yield _data_event("planning", {
                        "content": event.get("content", ""),
                    })

                # ── Note result (sticky notes for sidebar) ─────
                elif event_type == "note_result":
                    yield _data_event("note-result", {
                        "notes": event.get("notes", []),
                    })

                # ── Artifact result (AI-generated files) ────────
                elif event_type == "artifact_result":
                    yield _data_event("artifact-result", {
                        "artifacts": event.get("artifacts", []),
                        "persisted_ids": event.get("persisted_ids", []),
                    })

                # ── Mission result (persistent missions) ───────
                elif event_type == "mission_result":
                    yield _data_event("mission-result", {
                        "missions": event.get("missions", []),
                        "persisted_ids": event.get("persisted_ids", []),
                    })

                # ── Mission action (toggle step / complete) ────
                elif event_type == "mission_action":
                    yield _data_event("mission-action", {
                        "action": event.get("action"),
                        "mission": event.get("mission", {}),
                        "step_index": event.get("step_index"),
                    })

                # ── SQL approval request (interrupt) ──────────
                elif event_type == "sql_approval_request":
                    yield _data_event("sql-approval-request", {
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

                # ── Emotional state update ─────────────────────
                elif event_type == "emotional_update":
                    yield _data_event("emotional-update", {
                        "mood": event.get("mood"),
                        "energy": event.get("energy"),
                        "affinity": event.get("affinity"),
                        "relationship_tier": event.get("relationship_tier"),
                        "mood_changed": event.get("mood_changed", False),
                        "streak_days": event.get("streak_days", 0),
                        "interaction_count": event.get("interaction_count", 0),
                    })

                # ── Final result ────────────────────────────────
                elif event_type == "final":
                    result = event.get("result", {})
                    run_id = event.get("run_id") or run_id
                    final_stats = result.get("stats")

                    # If the final answer wasn't streamed token-by-token, emit it now
                    final_answer = result.get("answer", "")
                    if not answer_parts and final_answer:
                        if not text_started:
                            yield _text_start(text_part_id)
                            text_started = True
                        answer_parts.append(final_answer)
                        yield _text_delta(text_part_id, final_answer)

                    # Emit rich metadata for the sidebar
                    yield _data_event("final", {
                        "run_id": run_id,
                        "stats": _safe_stats(final_stats),
                        "worker_results": result.get("worker_results", []),
                        "iterations": result.get("iterations", 0),
                        "timing": result.get("timing", {}),
                    })

                # ── Error ───────────────────────────────────────
                elif event_type == "error":
                    error_msg = event.get("error", "Unknown error")
                    yield _error_event(error_msg)

        except Exception as exc:
            log_error(f"Streaming error: {exc}")
            yield _error_event(str(exc))

        # ── Close text part if open ────────────────────────────
        if text_started:
            yield _text_end(text_part_id)

        # Persist the assistant message BEFORE sending finish signals.
        # Once _done() is yielded the client may close the connection,
        # which raises GeneratorExit and skips any code after the yield.
        # persist_assistant_message is fire-and-forget (ThreadPoolExecutor)
        # so it won't block the stream.
        full_answer = "".join(answer_parts)
        svc.persist_assistant_message(
            user_id=prep.user_id,
            thread_id=prep.thread_id,
            content=full_answer,
            run_id=run_id,
            character_id=prep.config.character,
        )

        # ── Finish signals ─────────────────────────────────────
        yield _finish_step()
        yield _finish_message("stop")
        yield _done()

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "X-Thread-Id": prep.thread_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


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


# ── Thread CRUD ─────────────────────────────────────────────────────────────

@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service),
):
    """List the authenticated user's conversation threads."""
    uid_str = str(user.id)

    # L2 cache: try Redis first
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

        # Backfill Redis cache
        try:
            cache.set_cached_threads(
                uid_str, [t.model_dump() for t in thread_list]
            )
        except Exception:
            pass

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

        # Invalidate L2 caches
        try:
            uid_str = str(user.id)
            cache.invalidate_threads(uid_str)
            cache.invalidate_dashboard(uid_str)
        except Exception:
            pass

    await concurrency_manager.run_in_thread(_query)
    return None


# ── Thread update (rename / star / pin / archive) ──────────────────────────

class ThreadPatchRequest(BaseModel):
    """Partial update for a thread."""
    title: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, description="active | archived")
    is_starred: Optional[bool] = None
    is_pinned: Optional[bool] = None


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
        thread = chat_history_service.update_thread(
            thread_id=tid,
            user_id=user.id,
            title=body.title,
            status=body.status,
            is_starred=body.is_starred,
            is_pinned=body.is_pinned,
        )
        if not thread:
            raise NotFoundError("Thread not found")

        # Invalidate L2 caches
        try:
            cache.invalidate_threads(str(user.id))
        except Exception:
            pass

        return ThreadResponse(
            id=str(thread.id),
            title=thread.title,
            status=thread.status.value if hasattr(thread.status, "value") else str(thread.status),
            is_starred=getattr(thread, "is_starred", False),
            is_pinned=getattr(thread, "is_pinned", False),
            created_at=thread.created_at.isoformat() if thread.created_at else "",
            updated_at=thread.updated_at.isoformat() if thread.updated_at else "",
        )

    return await concurrency_manager.run_in_thread(_query)
