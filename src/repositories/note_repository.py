"""Note repository — data access for Note model."""

from typing import Optional, List
from uuid import UUID

from models.note import Note
from repositories.base import BaseRepository


class NoteRepository(BaseRepository):
    """Data access for Note entities."""

    def find_by_id(self, note_id: UUID, user_id: UUID) -> Optional[Note]:
        return (
            self.db.query(Note)
            .filter(Note.id == note_id, Note.user_id == user_id)
            .first()
        )

    def list_by_user(
        self,
        user_id: UUID,
        thread_id: Optional[UUID] = None,
        collection_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Note]:
        q = self.db.query(Note).filter(Note.user_id == user_id)
        if thread_id:
            q = q.filter(Note.thread_id == thread_id)
        if collection_id:
            q = q.filter(Note.collection_id == collection_id)
        return (
            q.order_by(Note.pinned.desc(), Note.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create(self, note: Note) -> Note:
        self.db.add(note)
        self.db.flush()
        return note

    def delete_by_id(self, note_id: UUID, user_id: UUID) -> int:
        return (
            self.db.query(Note)
            .filter(Note.id == note_id, Note.user_id == user_id)
            .delete()
        )
