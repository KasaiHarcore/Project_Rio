"""ReAct tools for note CRUD and knowledge graph operations.

Wraps NoteKnowledgeTool (read) and NoteService (write) as @tool functions
with user_id captured in closures.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.tools import tool

from infrastructure.database.session import get_session_factory
from infrastructure.tools.note_knowledge_tool import NoteKnowledgeTool
from repositories.note_repository import NoteRepository
from services.note_service import NoteService
from schemas.note import NoteCreate, NoteUpdate
from utils.log import log_info, log_warning


def _get_note_service(db_session) -> NoteService:
    """Build a NoteService with its dependencies from a DB session."""
    note_repo = NoteRepository(db_session)
    try:
        from repositories.note_link_repository import NoteLinkRepository
        from services.note_link_service import NoteLinkService

        link_repo = NoteLinkRepository(db_session)
        link_svc = NoteLinkService(link_repo)
    except Exception:
        link_svc = None
    return NoteService(note_repo, note_link_service=link_svc)


def find_contextual_notes(
    query: str,
    user_id: str,
    k: int = 3,
    score_threshold: float = 0.55,
) -> list[dict]:
    """Search for notes semantically relevant to the current conversation.

    Called from the chat streaming handler (not as an agent tool) to
    surface related notes in the sidebar.

    Returns lightweight note summaries: [{id, title, snippet, score, created_at}]
    """
    SessionFactory = get_session_factory()
    try:
        with SessionFactory() as db:
            tool_instance = NoteKnowledgeTool(db)
            raw = tool_instance.search_notes(query, user_id, k=k)

        results = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(results, list):
            return []

        contextual = []
        for note in results:
            score = note.get("score", 0)
            if score >= score_threshold:
                contextual.append({
                    "id": note.get("id"),
                    "title": note.get("title", "Untitled"),
                    "snippet": (note.get("content", ""))[:200],
                    "score": round(score, 3),
                    "created_at": note.get("created_at"),
                })

        return contextual[:k]
    except Exception as e:
        log_warning(f"[ContextualNotes] Failed to find contextual notes: {e}")
        return []


def build_note_tools(user_id: str) -> list:
    """Build note tools with user_id baked into closures."""

    SessionFactory = get_session_factory()

    # ── Read tools (use NoteKnowledgeTool) ──

    @tool
    def search_notes(query: str, collection_id: Optional[str] = None, k: int = 10) -> str:
        """Search notes using semantic similarity with graph-enhanced expansion.

        Args:
            query: Natural language search query.
            collection_id: Optional collection UUID to scope the search.
            k: Maximum number of results.

        Returns:
            JSON array of matching notes with id, title, content preview,
            relevance score, and collection_ids.
        """
        with SessionFactory() as db:
            tool_instance = NoteKnowledgeTool(db)
            return tool_instance.search_notes(query, user_id, collection_id=collection_id, k=k)

    @tool
    def get_note(note_id: str) -> str:
        """Get full note content with metadata, outbound links, and backlinks.

        Args:
            note_id: The note UUID to retrieve.

        Returns:
            JSON with full note object including content, todos, links, backlinks.
        """
        with SessionFactory() as db:
            tool_instance = NoteKnowledgeTool(db)
            return tool_instance.get_note(user_id, note_id)

    @tool
    def list_note_collections() -> str:
        """List all note collections with note counts.

        Returns:
            JSON array of collections with id, name, and note_count.
        """
        with SessionFactory() as db:
            tool_instance = NoteKnowledgeTool(db)
            return tool_instance.list_collections(user_id)

    @tool
    def get_collection_notes(collection_id: str) -> str:
        """Get all notes in a specific collection.

        Args:
            collection_id: The collection UUID.

        Returns:
            JSON array of notes in the collection.
        """
        with SessionFactory() as db:
            tool_instance = NoteKnowledgeTool(db)
            return tool_instance.get_collection_notes(user_id, collection_id)

    @tool
    def get_note_graph(note_id: Optional[str] = None) -> str:
        """Get note relationship graph. If note_id given, returns 1-hop subgraph.

        Args:
            note_id: Optional note UUID for local subgraph. Omit for full graph.

        Returns:
            JSON with nodes, edges, and graph statistics.
        """
        with SessionFactory() as db:
            tool_instance = NoteKnowledgeTool(db)
            return tool_instance.get_note_graph(user_id, note_id=note_id)

    @tool
    def get_backlinks(note_id: str) -> str:
        """Get all notes that reference a given note (backlinks).

        Args:
            note_id: The target note UUID.

        Returns:
            JSON array of notes linking to this note, with preview text.
        """
        with SessionFactory() as db:
            tool_instance = NoteKnowledgeTool(db)
            return tool_instance.get_backlinks(user_id, note_id)

    # ── Write tools (use NoteService) ──

    @tool
    def create_note(
        title: str,
        content: str,
        collection_ids: Optional[List[str]] = None,
        is_important: bool = False,
    ) -> str:
        """Create a new note.

        Args:
            title: Note title.
            content: Note text content.
            collection_ids: Optional list of collection UUIDs to add the note to.
            is_important: Whether to mark the note as important.

        Returns:
            JSON with the created note object including its id.
        """
        data = NoteCreate(
            title=title,
            content=content,
            collection_ids=collection_ids,
            is_important=is_important,
        )
        with SessionFactory() as db:
            svc = _get_note_service(db)
            note = svc.create_note(UUID(user_id), data)
            db.commit()
            return json.dumps({
                "success": True,
                "note_id": str(note.id),
                "title": note.title,
                "content": note.content[:500],
            }, default=str)

    @tool
    def update_note(
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        pinned: Optional[bool] = None,
        is_important: Optional[bool] = None,
        collection_ids: Optional[List[str]] = None,
    ) -> str:
        """Update an existing note's fields. Only provided fields are changed.

        Args:
            note_id: The note UUID to update.
            title: New title (optional).
            content: New content (optional).
            pinned: Pin/unpin the note (optional).
            is_important: Mark as important (optional).
            collection_ids: New collection UUIDs (optional, replaces existing).

        Returns:
            JSON with the updated note object, or an error.
        """
        data = NoteUpdate(
            title=title,
            content=content,
            pinned=pinned,
            is_important=is_important,
            collection_ids=collection_ids,
        )
        with SessionFactory() as db:
            svc = _get_note_service(db)
            note = svc.update_note(UUID(user_id), UUID(note_id), data)
            if not note:
                return json.dumps({"error": f"Note {note_id} not found or not owned by user"})
            db.commit()
            return json.dumps({
                "success": True,
                "note_id": str(note.id),
                "title": note.title,
                "content": note.content[:500],
                "updated_fields": [k for k, v in data.model_dump(exclude_none=True).items()],
            }, default=str)

    @tool
    def delete_note(note_id: str) -> str:
        """Delete a note permanently.

        Args:
            note_id: The note UUID to delete.

        Returns:
            JSON with success status.
        """
        with SessionFactory() as db:
            svc = _get_note_service(db)
            success = svc.delete_note(UUID(user_id), UUID(note_id))
            if success:
                db.commit()
            return json.dumps({"success": success, "note_id": note_id})

    @tool
    def toggle_note_todo(note_id: str, todo_index: int) -> str:
        """Toggle a note's todo item completion status.

        Args:
            note_id: The note UUID.
            todo_index: Zero-based index of the todo item to toggle.

        Returns:
            JSON with the updated note object.
        """
        with SessionFactory() as db:
            svc = _get_note_service(db)
            note = svc.toggle_todo(UUID(user_id), UUID(note_id), todo_index)
            if not note:
                return json.dumps({"error": f"Note {note_id} not found or todo index out of range"})
            db.commit()
            return json.dumps({
                "success": True,
                "note_id": str(note.id),
                "title": note.title,
                "todos": [t.model_dump() for t in note.todos],
            }, default=str)

    return [
        search_notes,
        get_note,
        list_note_collections,
        get_collection_notes,
        get_note_graph,
        get_backlinks,
        create_note,
        update_note,
        delete_note,
        toggle_note_todo,
    ]
