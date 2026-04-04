"""Note CRUD, confirmation, and link endpoints.

Note CRUD provides:
    GET    /notes              - list notes (filter by thread_id, collection_id)
    GET    /notes/{id}         - get single note
    POST   /notes              - create a note manually
    PATCH  /notes/{id}         - partial update
    PATCH  /notes/{id}/todos/{idx}/toggle - toggle one todo item
    DELETE /notes/{id}         - delete a note

Note confirmation provides:
    POST   /note-confirmation/resume - resume workflow after HITL interrupt

Note links provide:
    POST   /note-links              - create link manually
    POST   /note-links/bulk         - bulk create
    GET    /note-links              - list (filter: note_id, target_type)
    GET    /note-links/graph        - graph visualization data
    GET    /note-links/backlinks/{note_id} - backlinks to a note
    GET    /note-links/{link_id}    - get single
    PATCH  /note-links/{link_id}    - update
    DELETE /note-links/{link_id}    - delete
"""

from __future__ import annotations

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_note_service, get_note_link_service
from core.exceptions import NotFoundError
from core.settings import AgentConfig
from models.note_link import NoteLinkTargetType
from models.user import User
from schemas.note import NoteCreate, NoteUpdate, NoteInDB
from schemas.note_link import (
    NoteLinkBulkCreate,
    NoteLinkCreate,
    NoteLinkInDB,
    NoteLinkUpdate,
    NoteGraphResponse,
)
from services.note_service import NoteService
from services.note_link_service import NoteLinkService
from workflows.executor import resume_note_confirmation
from utils.log import log_info, log_error


# ---------------------------------------------------------------------------
# Note CRUD router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=List[NoteInDB])
async def list_notes(
    thread_id: Optional[UUID] = Query(None),
    collection_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    svc: NoteService = Depends(get_note_service),
):
    """List notes for the authenticated user, optionally filtered by thread or collection."""
    return await concurrency_manager.run_in_thread(
        svc.list_notes,
        user.id,
        thread_id=thread_id,
        collection_id=collection_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{note_id}", response_model=NoteInDB)
async def get_note(
    note_id: UUID,
    user: User = Depends(get_current_user),
    svc: NoteService = Depends(get_note_service),
):
    """Get a single note by ID."""
    n = await concurrency_manager.run_in_thread(svc.get_note, user.id, note_id)
    if not n:
        raise NotFoundError("Note not found")
    return n


@router.post("", response_model=NoteInDB, status_code=status.HTTP_201_CREATED)
async def create_note(
    body: NoteCreate,
    user: User = Depends(get_current_user),
    svc: NoteService = Depends(get_note_service),
):
    """Create a new note."""
    return await concurrency_manager.run_in_thread(svc.create_note, user.id, body)


@router.patch("/{note_id}", response_model=NoteInDB)
async def update_note(
    note_id: UUID,
    body: NoteUpdate,
    user: User = Depends(get_current_user),
    svc: NoteService = Depends(get_note_service),
):
    """Partially update a note."""
    n = await concurrency_manager.run_in_thread(svc.update_note, user.id, note_id, body)
    if not n:
        raise NotFoundError("Note not found")
    return n


@router.patch("/{note_id}/todos/{todo_index}/toggle", response_model=NoteInDB)
async def toggle_note_todo(
    note_id: UUID,
    todo_index: int,
    user: User = Depends(get_current_user),
    svc: NoteService = Depends(get_note_service),
):
    """Toggle the done status of a single todo item."""
    n = await concurrency_manager.run_in_thread(svc.toggle_todo, user.id, note_id, todo_index)
    if not n:
        raise NotFoundError("Note or todo not found")
    return n


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: UUID,
    user: User = Depends(get_current_user),
    svc: NoteService = Depends(get_note_service),
):
    """Delete a note."""
    deleted = await concurrency_manager.run_in_thread(svc.delete_note, user.id, note_id)
    if not deleted:
        raise NotFoundError("Note not found")


# ---------------------------------------------------------------------------
# Note Confirmation router  (was note_confirmation.py)
# ---------------------------------------------------------------------------

confirmation_router = APIRouter(prefix="/note-confirmation", tags=["notes"])


def _text_line(chunk: str) -> str:
    return f"0:{json.dumps(chunk)}\n"


def _data_line(payload: list | dict) -> str:
    if isinstance(payload, dict):
        payload = [payload]
    return f"2:{json.dumps(payload)}\n"


def _finish_line(reason: str = "stop") -> str:
    return f'd:{json.dumps({"finishReason": reason})}\n'


def _error_line(message: str) -> str:
    return f'e:{json.dumps({"finishReason": "error", "message": message})}\n'


class NoteConfirmationResumeRequest(BaseModel):
    """Body sent by the frontend when user responds to a note confirmation card."""
    thread_id: str = Field(..., description="Thread with the pending note confirmation")
    decision: str = Field(..., description="User decision: approve | reject")
    mode: Optional[str] = Field("chat", description="Agent mode")
    character: Optional[str] = Field("rio", description="Persona ID")


@confirmation_router.post("/resume")
async def resume_note(
    body: NoteConfirmationResumeRequest,
    user: User = Depends(get_current_user),
):
    """Resume the workflow after a note confirmation decision.

    Returns a streaming response using the AI SDK data-stream protocol,
    identical to the chat endpoint, so the frontend can merge tokens
    and structured events into the existing message list.
    """
    log_info(
        f"[REST] note-confirmation/resume: user={user.username} "
        f"thread={body.thread_id} decision={body.decision}"
    )

    config = AgentConfig(
        mode=body.mode or "chat",
        character=body.character or "rio",
        user_role=user.role.value,
    )

    def _generate():
        answer_parts: list[str] = []
        try:
            for event in resume_note_confirmation(
                thread_id=body.thread_id,
                config=config,
                decision=body.decision,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    chunk = event.get("content", "")
                    answer_parts.append(chunk)
                    yield _text_line(chunk)

                elif event_type == "run_started":
                    yield _data_line({
                        "type": "run_started",
                        "run_id": event.get("run_id"),
                        "thread_id": event.get("thread_id"),
                    })

                elif event_type == "supervisor":
                    decision_data = event.get("decision", {})
                    yield _data_line({
                        "type": "supervisor_decision",
                        "action": decision_data.get("action"),
                        "worker": decision_data.get("next_worker"),
                        "reasoning": decision_data.get("reasoning", ""),
                    })

                elif event_type == "worker":
                    yield _data_line({
                        "type": "worker_result",
                        "worker": event.get("worker"),
                        "success": event.get("success"),
                        "content_preview": event.get("content_preview", ""),
                    })

                elif event_type == "note_result":
                    yield _data_line({
                        "type": "note_result",
                        "action": event.get("action"),
                        "notes": event.get("notes", []),
                        "persisted_ids": event.get("persisted_ids", []),
                    })

                elif event_type == "note_confirmation_request":
                    yield _data_line({
                        "type": "note_confirmation_request",
                        "confirmation_type": event.get("confirmation_type"),
                        "note_id": event.get("note_id", ""),
                        "note_title": event.get("note_title", ""),
                        "action": event.get("action", "delete"),
                        "message": event.get("message", ""),
                        "options": event.get("options", ["approve", "reject"]),
                    })

                elif event_type == "final":
                    result = event.get("result", {})
                    final_answer = result.get("answer", "")
                    if not answer_parts and final_answer:
                        answer_parts.append(final_answer)
                        yield _text_line(final_answer)

                    yield _data_line({
                        "type": "final",
                        "run_id": event.get("run_id"),
                        "stats": _safe_stats(result.get("stats")),
                        "worker_results": result.get("worker_results", []),
                        "timing": result.get("timing", {}),
                        "decision": result.get("decision"),
                    })

                elif event_type == "error":
                    yield _error_line(event.get("error", "Unknown error"))

        except Exception as exc:
            log_error(f"Note confirmation streaming error: {exc}")
            yield _error_line(str(exc))

        yield _finish_line("stop")

    return StreamingResponse(
        _generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Thread-Id": body.thread_id,
            "X-Vercel-AI-Data-Stream": "v1",
            "Cache-Control": "no-cache",
            "Transfer-Encoding": "chunked",
        },
    )


def _safe_stats(stats: dict | None) -> dict:
    if not stats:
        return {}
    return {
        "total_tokens": stats.get("total_tokens", 0),
        "total_input_tokens": stats.get("total_input_tokens", 0),
        "total_output_tokens": stats.get("total_output_tokens", 0),
        "total_cost": stats.get("total_cost", 0),
    }


# ---------------------------------------------------------------------------
# Note Link router  (was note_link.py)
# ---------------------------------------------------------------------------

link_router = APIRouter(prefix="/note-links", tags=["notes"])


@link_router.post("", response_model=NoteLinkInDB, status_code=status.HTTP_201_CREATED)
async def create_link(
    body: NoteLinkCreate,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Create a note link manually."""
    return await concurrency_manager.run_in_thread(svc.create_link, user.id, body)


@link_router.post("/bulk", response_model=List[NoteLinkInDB], status_code=status.HTTP_201_CREATED)
async def bulk_create_links(
    body: NoteLinkBulkCreate,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Bulk create note links."""
    return await concurrency_manager.run_in_thread(
        svc.create_links_bulk, user.id, body.links,
    )


@link_router.get("", response_model=List[NoteLinkInDB])
async def list_links(
    note_id: Optional[UUID] = Query(None),
    target_type: Optional[NoteLinkTargetType] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """List note links, optionally filtered by note_id and target_type."""
    return await concurrency_manager.run_in_thread(
        svc.list_links,
        user.id,
        note_id=note_id,
        target_type=target_type,
        limit=limit,
        offset=offset,
    )


@link_router.get("/graph", response_model=NoteGraphResponse)
async def get_graph(
    center_node_id: Optional[UUID] = Query(None, description="Center note UUID for 1-hop subgraph"),
    limit: int = Query(500, ge=1, le=5000, description="Max nodes to return"),
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Get note graph data for visualization.

    Without center_node_id: returns full graph capped at ``limit`` nodes.
    With center_node_id: returns 1-hop subgraph around that note.
    """
    return await concurrency_manager.run_in_thread(
        svc.get_note_graph, user.id,
        center_node_id=center_node_id,
        limit=limit,
    )


@link_router.get("/backlinks/{note_id}", response_model=List[NoteLinkInDB])
async def get_backlinks(
    note_id: UUID,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Get all links pointing TO a given note."""
    return await concurrency_manager.run_in_thread(
        svc.list_backlinks, user.id, note_id,
    )


@link_router.get("/{link_id}", response_model=NoteLinkInDB)
async def get_link(
    link_id: UUID,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Get a single note link by ID."""
    link = await concurrency_manager.run_in_thread(svc.get_link, user.id, link_id)
    if not link:
        raise NotFoundError("Note link not found")
    return link


@link_router.patch("/{link_id}", response_model=NoteLinkInDB)
async def update_link(
    link_id: UUID,
    body: NoteLinkUpdate,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Partially update a note link."""
    link = await concurrency_manager.run_in_thread(
        svc.update_link, user.id, link_id, body,
    )
    if not link:
        raise NotFoundError("Note link not found")
    return link


@link_router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: UUID,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Delete a note link."""
    deleted = await concurrency_manager.run_in_thread(
        svc.delete_link, user.id, link_id,
    )
    if not deleted:
        raise NotFoundError("Note link not found")
