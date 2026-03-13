"""Chat endpoints: streaming conversation, thread listing, message history.

The streaming endpoint uses the **Vercel AI SDK data-stream protocol**
so that both text tokens *and* structured sidebar events (supervisor
decisions, worker results, stats …) travel in a single HTTP response.

Protocol reference (ai@6 / @ai-sdk/react@3):
  0:"text chunk"\\n          – text delta
  2:[{json}, …]\\n           – data annotation (sidebar events)
  d:{"finishReason":"stop"}\\n – finish signal
  e:{"finishReason":"error","message":"…"}\\n – error
"""

from __future__ import annotations

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

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


# ── Data-stream protocol helpers ────────────────────────────────────────────

def _text_line(chunk: str) -> str:
    """AI SDK text-delta: ``0:"chunk"\\n``."""
    return f"0:{json.dumps(chunk)}\n"


def _data_line(payload: list | dict) -> str:
    """AI SDK data annotation: ``2:[{...}]\\n``.

    *payload* should be a single dict (auto-wrapped) or a list of dicts.
    """
    if isinstance(payload, dict):
        payload = [payload]
    return f"2:{json.dumps(payload)}\n"


def _finish_line(reason: str = "stop") -> str:
    """AI SDK finish signal: ``d:{...}\\n``."""
    return f'd:{json.dumps({"finishReason": reason})}\n'


def _error_line(message: str) -> str:
    """AI SDK error signal: ``e:{...}\\n``."""
    return f'e:{json.dumps({"finishReason": "error", "message": message})}\n'


# ── Request / Response schemas ──────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: user | assistant")
    content: str = Field(..., description="Message text")


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
    """Body sent by the Vercel AI SDK useChat hook."""
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    thread_id: Optional[str] = Field(None, description="Existing thread ID to continue")
    mode: Optional[str] = Field("chat", description="Agent mode: chat | rag | web | sql")
    character: Optional[str] = Field("rio", description="Persona ID: rio")
    workspace_context: Optional[WorkspaceContext] = Field(None, description="Smart-chunked code context from workspace files")


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
    prep = svc.prepare_chat(
        user=user,
        messages=body.messages,
        thread_id=body.thread_id,
        mode=body.mode,
        character=body.character,
        workspace_context=body.workspace_context,
    )

    def _generate():
        """Sync generator – emits AI SDK data-stream protocol lines."""
        answer_parts: list[str] = []
        run_id = None
        final_stats = None

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
                    answer_parts.append(chunk)
                    yield _text_line(chunk)

                # ── Run started ─────────────────────────────────
                elif event_type == "run_started":
                    run_id = event.get("run_id")
                    yield _data_line({
                        "type": "run_started",
                        "run_id": run_id,
                        "thread_id": event.get("thread_id"),
                        "character": prep.config.character,
                    })

                # ── Supervisor decision ─────────────────────────
                elif event_type == "supervisor":
                    decision = event.get("decision", {})
                    yield _data_line({
                        "type": "supervisor_decision",
                        "action": decision.get("action"),
                        "worker": decision.get("next_worker"),
                        "reasoning": decision.get("reasoning", ""),
                        "confidence": decision.get("confidence", 1.0),
                        "iteration": event.get("iteration", 0),
                    })

                # ── Worker result ───────────────────────────────
                elif event_type == "worker":
                    yield _data_line({
                        "type": "worker_result",
                        "worker": event.get("worker"),
                        "success": event.get("success"),
                        "content_preview": event.get("content_preview", ""),
                    })

                # ── Planning ────────────────────────────────────
                elif event_type == "planning":
                    yield _data_line({
                        "type": "planning",
                        "content": event.get("content", ""),
                    })

                # ── Note result (sticky notes for sidebar) ─────
                elif event_type == "note_result":
                    yield _data_line({
                        "type": "note_result",
                        "notes": event.get("notes", []),
                    })

                # ── Artifact result (AI-generated files) ────────
                elif event_type == "artifact_result":
                    yield _data_line({
                        "type": "artifact_result",
                        "artifacts": event.get("artifacts", []),
                        "persisted_ids": event.get("persisted_ids", []),
                    })

                # ── Mission result (persistent missions) ───────
                elif event_type == "mission_result":
                    yield _data_line({
                        "type": "mission_result",
                        "missions": event.get("missions", []),
                        "persisted_ids": event.get("persisted_ids", []),
                    })

                # ── SQL approval request (interrupt) ──────────
                elif event_type == "sql_approval_request":
                    yield _data_line({
                        "type": "sql_approval_request",
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
                    yield _data_line({
                        "type": "emotional_update",
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
                        answer_parts.append(final_answer)
                        yield _text_line(final_answer)

                    # Emit rich metadata for the sidebar
                    yield _data_line({
                        "type": "final",
                        "run_id": run_id,
                        "stats": _safe_stats(final_stats),
                        "worker_results": result.get("worker_results", []),
                        "iterations": result.get("iterations", 0),
                        "timing": result.get("timing", {}),
                    })

                # ── Error ───────────────────────────────────────
                elif event_type == "error":
                    error_msg = event.get("error", "Unknown error")
                    yield _error_line(error_msg)

        except Exception as exc:
            log_error(f"Streaming error: {exc}")
            yield _error_line(str(exc))

        # ── Finish signal ───────────────────────────────────────
        yield _finish_line("stop")

        # Persist the assistant message asynchronously
        full_answer = "".join(answer_parts)
        svc.persist_assistant_message(
            user_id=prep.user_id,
            thread_id=prep.thread_id,
            content=full_answer,
            run_id=run_id,
            character_id=prep.config.character,
        )

    return StreamingResponse(
        _generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Thread-Id": prep.thread_id,
            "X-Vercel-AI-Data-Stream": "v1",
            "Cache-Control": "no-cache",
            "Transfer-Encoding": "chunked",
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
