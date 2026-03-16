"""Collection repository — data access for NoteCollection model."""

from typing import Optional, List, Dict
from uuid import UUID

from sqlalchemy import func

from models.note import Note
from models.note_collection import NoteCollection
from repositories.base import BaseRepository


class CollectionRepository(BaseRepository):
    """Data access for NoteCollection entities."""

    def find_by_id(self, collection_id: UUID, user_id: UUID) -> Optional[NoteCollection]:
        return (
            self.db.query(NoteCollection)
            .filter(NoteCollection.id == collection_id, NoteCollection.user_id == user_id)
            .first()
        )

    def list_by_user(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[NoteCollection]:
        return (
            self.db.query(NoteCollection)
            .filter(NoteCollection.user_id == user_id)
            .order_by(NoteCollection.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_note_counts(self, user_id: UUID) -> Dict[UUID, int]:
        """Get note count per collection for a user."""
        from models.note_collection_membership import NoteCollectionMembership
        count_sq = (
            self.db.query(
                NoteCollectionMembership.collection_id,
                func.count(NoteCollectionMembership.note_id).label("cnt"),
            )
            .join(Note, Note.id == NoteCollectionMembership.note_id)
            .filter(Note.user_id == user_id)
            .group_by(NoteCollectionMembership.collection_id)
            .subquery()
        )
        rows = self.db.query(count_sq.c.collection_id, count_sq.c.cnt).all()
        return {row[0]: row[1] for row in rows if row[0]}

    def count_notes_in(self, collection_id: UUID, user_id: UUID) -> int:
        from models.note_collection_membership import NoteCollectionMembership
        return (
            self.db.query(func.count(NoteCollectionMembership.note_id))
            .join(Note, Note.id == NoteCollectionMembership.note_id)
            .filter(
                NoteCollectionMembership.collection_id == collection_id,
                Note.user_id == user_id,
            )
            .scalar() or 0
        )

    def create(self, collection: NoteCollection) -> NoteCollection:
        self.db.add(collection)
        self.db.flush()
        return collection

    def delete_by_id(self, collection_id: UUID, user_id: UUID) -> int:
        return (
            self.db.query(NoteCollection)
            .filter(NoteCollection.id == collection_id, NoteCollection.user_id == user_id)
            .delete()
        )
