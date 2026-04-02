"""NoteLink repository — data access for NoteLink model."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from models.note_link import NoteLink, NoteLinkTargetType
from repositories.base import BaseRepository


class NoteLinkRepository(BaseRepository):
    """Data access for NoteLink entities."""

    def find_by_id(self, link_id: UUID, user_id: UUID) -> Optional[NoteLink]:
        return (
            self.db.query(NoteLink)
            .filter(NoteLink.id == link_id, NoteLink.user_id == user_id)
            .first()
        )

    def find_links_by_note(
        self,
        note_id: UUID,
        user_id: UUID,
        target_type: Optional[NoteLinkTargetType] = None,
    ) -> List[NoteLink]:
        q = self.db.query(NoteLink).filter(
            NoteLink.note_id == note_id,
            NoteLink.user_id == user_id,
        )
        if target_type:
            q = q.filter(NoteLink.target_type == target_type)
        return q.order_by(NoteLink.position.asc().nulls_last()).all()

    def find_backlinks(self, target_note_id: UUID, user_id: UUID) -> List[NoteLink]:
        """Find all links that point TO a given note."""
        return (
            self.db.query(NoteLink)
            .filter(
                NoteLink.target_note_id == target_note_id,
                NoteLink.user_id == user_id,
            )
            .order_by(NoteLink.created_at.desc())
            .all()
        )

    def find_links_by_user(
        self,
        user_id: UUID,
        target_type: Optional[NoteLinkTargetType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[NoteLink]:
        q = self.db.query(NoteLink).filter(NoteLink.user_id == user_id)
        if target_type:
            q = q.filter(NoteLink.target_type == target_type)
        return q.order_by(NoteLink.created_at.desc()).offset(offset).limit(limit).all()

    def create(self, link: NoteLink) -> NoteLink:
        self.db.add(link)
        self.db.flush()
        return link

    def create_bulk(self, links: List[NoteLink]) -> List[NoteLink]:
        self.db.add_all(links)
        self.db.flush()
        return links

    def delete_by_id(self, link_id: UUID, user_id: UUID) -> bool:
        count = (
            self.db.query(NoteLink)
            .filter(NoteLink.id == link_id, NoteLink.user_id == user_id)
            .delete()
        )
        return count > 0

    def delete_by_note(self, note_id: UUID, user_id: UUID) -> int:
        """Delete all links FROM a given note."""
        return (
            self.db.query(NoteLink)
            .filter(NoteLink.note_id == note_id, NoteLink.user_id == user_id)
            .delete()
        )

    def get_graph_data(self, user_id: UUID) -> List[NoteLink]:
        """Load all links for a user with eager-loaded relationships."""
        return (
            self.db.query(NoteLink)
            .options(
                joinedload(NoteLink.note),
                joinedload(NoteLink.target_note),
                joinedload(NoteLink.target_document),
                joinedload(NoteLink.target_artifact),
            )
            .filter(NoteLink.user_id == user_id)
            .all()
        )

    def get_graph_data_limited(
        self, user_id: UUID, limit: int = 1000,
    ) -> List[NoteLink]:
        """Load links for a user with eager-loaded relationships, capped at limit.

        Ordered by created_at DESC so the most recently active parts of the
        graph are prioritised when the limit truncates.
        """
        return (
            self.db.query(NoteLink)
            .options(
                joinedload(NoteLink.note),
                joinedload(NoteLink.target_note),
                joinedload(NoteLink.target_document),
                joinedload(NoteLink.target_artifact),
            )
            .filter(NoteLink.user_id == user_id)
            .order_by(NoteLink.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_subgraph_data(
        self, user_id: UUID, center_note_id: UUID,
    ) -> List[NoteLink]:
        """Load 1-hop subgraph: all links FROM or TO center_note_id."""
        return (
            self.db.query(NoteLink)
            .options(
                joinedload(NoteLink.note),
                joinedload(NoteLink.target_note),
                joinedload(NoteLink.target_document),
                joinedload(NoteLink.target_artifact),
            )
            .filter(
                NoteLink.user_id == user_id,
                or_(
                    NoteLink.note_id == center_note_id,
                    NoteLink.target_note_id == center_note_id,
                ),
            )
            .all()
        )

    def count_by_user(self, user_id: UUID) -> int:
        return (
            self.db.query(NoteLink)
            .filter(NoteLink.user_id == user_id)
            .count()
        )
