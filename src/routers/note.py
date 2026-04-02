"""Note CRUD endpoints.

Provides:
    GET    /notes              – list notes (filter by thread_id, collection_id)
    GET    /notes/{id}         – get single note
    POST   /notes              – create a note manually
    PATCH  /notes/{id}         – partial update
    PATCH  /notes/{id}/todos/{idx}/toggle – toggle one todo item
    DELETE /notes/{id}         – delete a note
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_note_service
from core.exceptions import NotFoundError
from services.note_service import NoteService
from models.user import User
from schemas.note import NoteCreate, NoteUpdate, NoteInDB

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
