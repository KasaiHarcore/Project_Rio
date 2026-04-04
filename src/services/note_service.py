"""Note service — CRUD operations for persistent sticky notes.

Handles creation, retrieval, update, deletion, and todo-toggling of notes.
Notes can be created by the agent (auto-extracted from conversations) or
manually by the user.  Each note is tied to a thread and auto-deleted when
the thread is removed (CASCADE).

V2: Supports title, blocks, collections, audio, is_important.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from uuid import UUID

from models.note import Note, NoteSource
from models.note_collection_membership import NoteCollectionMembership
from schemas.note import (
    NoteCreate,
    NoteUpdate,
    NoteInDB,
)
from repositories.note_repository import NoteRepository
from repositories.collection_repository import CollectionRepository
from core.concurrency import concurrency_manager
from utils.log import log_info, log_warning


class NoteService:
    """Service for note CRUD operations."""

    def __init__(
        self,
        note_repo: NoteRepository,
        note_link_service: Optional[object] = None,
        collection_repo: Optional[CollectionRepository] = None,
    ) -> None:
        self._repo = note_repo
        self._link_service = note_link_service
        self._collection_repo = collection_repo
        # Cache storage dir at init to avoid repeated config lookups
        self._notes_dir: Optional[str] = None

    def _get_notes_dir(self) -> str:
        """Lazily resolve and cache the notes storage directory."""
        if self._notes_dir is None:
            import os
            from core.settings import get_app_config
            config = get_app_config()
            self._notes_dir = os.path.join(config.storage_dir, "notes")
            os.makedirs(self._notes_dir, exist_ok=True)
        return self._notes_dir

    def _save_note_to_disk(self, note: Note) -> None:
        try:
            import os
            filepath = os.path.join(self._get_notes_dir(), f"{note.id}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(note.content or "")
        except Exception as e:
            log_warning(f"Failed to save note to disk: {e}")

    def _delete_note_from_disk(self, note_id: UUID) -> None:
        try:
            import os
            filepath = os.path.join(self._get_notes_dir(), f"{note_id}.md")
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            log_warning(f"Failed to delete note from disk: {e}")

    def _set_note_collections(self, note_id: UUID, user_id: UUID, collection_ids: List[str]) -> None:
        """Replace all collection memberships for a note via repository."""
        valid_ids: List[UUID] = []
        for cid in collection_ids:
            try:
                valid_ids.append(UUID(cid))
            except (ValueError, Exception) as e:
                log_warning(f"Invalid collection_id '{cid}': {e}")

        if self._collection_repo:
            self._collection_repo.set_note_collections(note_id, valid_ids)
        else:
            # Fallback: use note repo's session directly
            from models.note_collection_membership import NoteCollectionMembership
            self._repo.db.query(NoteCollectionMembership).filter(
                NoteCollectionMembership.note_id == note_id
            ).delete()
            for cid in valid_ids:
                self._repo.db.add(NoteCollectionMembership(note_id=note_id, collection_id=cid))
            self._repo.db.flush()

    def _embed_note_async(self, note: Note) -> None:
        """Upsert note embedding into Qdrant via shared thread pool (non-blocking)."""
        # Capture values before submitting — note ORM may be detached later
        note_id = str(note.id)
        user_id = str(note.user_id)
        title = note.title or ""
        content = note.content or ""
        collection_ids = [str(c.id) for c in note.collections]
        source = note.source.value if note.source else "user"

        def _run():
            try:
                from infrastructure.data_access.note_vector_tool import get_note_vector_tool
                get_note_vector_tool().upsert_note(
                    note_id=note_id, user_id=user_id,
                    title=title, content=content,
                    collection_ids=collection_ids, source=source,
                )
            except Exception as e:
                log_warning(f"Note embedding upsert failed for {note_id}: {e}")
        concurrency_manager.submit_fire_and_forget(_run)

    def _delete_note_embedding_async(self, note_id: UUID) -> None:
        """Remove note embedding from Qdrant via shared thread pool."""
        nid = str(note_id)
        def _run():
            try:
                from infrastructure.data_access.note_vector_tool import get_note_vector_tool
                get_note_vector_tool().delete_note(nid)
            except Exception as e:
                log_warning(f"Note embedding delete failed for {nid}: {e}")
        concurrency_manager.submit_fire_and_forget(_run)

    def _note_to_schema(self, note: Note) -> NoteInDB:
        """Convert Note ORM to NoteInDB schema, including collection_ids."""
        data = NoteInDB.model_validate(note)
        data.collection_ids = [c.id for c in note.collections]
        return data


    def list_notes(
        self,
        user_id: UUID,
        thread_id: Optional[UUID] = None,
        collection_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[NoteInDB]:
        """List notes for a user, optionally filtered by thread or collection."""
        rows = self._repo.list_by_user(
            user_id=user_id,
            thread_id=thread_id,
            collection_id=collection_id,
            limit=limit,
            offset=offset,
        )
        return [self._note_to_schema(r) for r in rows]

    def get_note(self, user_id: UUID, note_id: UUID) -> Optional[NoteInDB]:
        """Get a single note by ID (scoped to user)."""
        row = self._repo.find_by_id(note_id=note_id, user_id=user_id)
        return self._note_to_schema(row) if row else None


    def create_note(self, user_id: UUID, data: NoteCreate) -> NoteInDB:
        """Create a new note."""
        note = Note(
            user_id=user_id,
            thread_id=UUID(data.thread_id) if data.thread_id else None,
            title=data.title or "",
            content=data.content,
            todos=[t.model_dump() for t in data.todos],
            blocks=[b.model_dump() for b in data.blocks],
            pinned=False,
            is_important=data.is_important,
            source=data.source,
            audio=data.audio.model_dump() if data.audio else None,
        )
        self._repo.create(note)
        if data.collection_ids:
            self._set_note_collections(note.id, user_id, data.collection_ids)
        self._save_note_to_disk(note)
        self._sync_links(user_id, note.id, note.content)
        self._embed_note_async(note)
        log_info(f"Created note {note.id} for user {user_id}")
        return self._note_to_schema(note)

    def create_notes_from_agent(
        self,
        user_id: UUID,
        notes_json: List[Dict[str, Any]],
        thread_id: Optional[str] = None,
    ) -> List[NoteInDB]:
        """Bulk-create notes extracted by the agent.

        Called by the executor when the note worker produces results.
        """
        created: List[NoteInDB] = []
        for n in notes_json[:5]:  # hard-cap
            content = str(n.get("content", "")).strip()
            if not content:
                continue

            todos_raw = n.get("todos", [])
            todos = []
            for t in (todos_raw or []):
                if isinstance(t, dict) and t.get("text"):
                    todos.append({
                        "text": str(t["text"]).strip()[:200],
                        "done": bool(t.get("done", False)),
                    })

            note = Note(
                user_id=user_id,
                thread_id=UUID(thread_id) if thread_id else None,
                title=content[:80],  # Use first part of content as title
                content=content[:5000],
                todos=todos,
                pinned=False,
                is_important=False,
                source=NoteSource.AGENT,
            )
            self._repo.create(note)
            self._save_note_to_disk(note)
            self._embed_note_async(note)
            created.append(self._note_to_schema(note))
            log_info(f"Agent-created note {note.id}: {content[:80]}")
        return created


    def update_note(self, user_id: UUID, note_id: UUID, data: NoteUpdate) -> Optional[NoteInDB]:
        """Partially update a note."""
        note = self._repo.find_by_id(note_id=note_id, user_id=user_id)
        if not note:
            return None

        update_data = data.model_dump(exclude_unset=True)
        collection_ids = update_data.pop("collection_ids", None)

        for field, value in update_data.items():
            if field == "todos" and value is not None:
                value = [t.model_dump() if hasattr(t, "model_dump") else t for t in value]
            if field == "blocks" and value is not None:
                value = [b.model_dump() if hasattr(b, "model_dump") else b for b in value]
            if field == "audio" and value is not None:
                value = value.model_dump() if hasattr(value, "model_dump") else value
            setattr(note, field, value)

        self._repo.flush()

        if collection_ids is not None:
            self._set_note_collections(note_id, user_id, collection_ids)

        self._save_note_to_disk(note)
        if "content" in update_data:
            self._sync_links(user_id, note_id, note.content)
        self._embed_note_async(note)
        return self._note_to_schema(note)

    def toggle_todo(self, user_id: UUID, note_id: UUID, todo_index: int) -> Optional[NoteInDB]:
        """Toggle a single todo item's done status."""
        note = self._repo.find_by_id_for_update(note_id=note_id, user_id=user_id)
        if not note or not note.todos:
            return None

        todos = list(note.todos)  # JSONB — make a mutable copy
        if todo_index < 0 or todo_index >= len(todos):
            return None

        todos[todo_index]["done"] = not todos[todo_index].get("done", False)
        note.todos = todos

        self._repo.flush()
        return self._note_to_schema(note)


    def _sync_links(self, user_id: UUID, note_id: UUID, content: str) -> None:
        """Auto-sync note links from content if link service is available."""
        if not self._link_service:
            return
        try:
            self._link_service.sync_links_from_content(user_id, note_id, content)
        except Exception as e:
            log_warning(f"Failed to sync links for note {note_id}: {e}")

    def delete_note(self, user_id: UUID, note_id: UUID) -> bool:
        """Delete a note. Returns True if deleted."""
        deleted = self._repo.delete_by_id(note_id=note_id, user_id=user_id)
        if deleted:
            self._delete_note_from_disk(note_id)
            self._delete_note_embedding_async(note_id)
        return deleted
