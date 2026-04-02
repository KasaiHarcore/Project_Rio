"""Document repository — data access for Document model."""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import func

from models.document import Document, DocumentStatus
from repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    """Data access for Document entities."""

    def find_by_id(self, doc_id: UUID, user_id: UUID) -> Optional[Document]:
        return (
            self.db.query(Document)
            .filter(Document.id == doc_id, Document.user_id == user_id)
            .first()
        )

    def list_by_user(self, user_id: UUID, limit: int = 50) -> List[Document]:
        return (
            self.db.query(Document)
            .filter(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .all()
        )

    def count_by_user(self, user_id: UUID) -> int:
        return (
            self.db.query(func.count(Document.id))
            .filter(Document.user_id == user_id)
            .scalar() or 0
        )

    def count_ready_by_user(self, user_id: UUID) -> int:
        return (
            self.db.query(func.count(Document.id))
            .filter(Document.user_id == user_id, Document.status == DocumentStatus.READY)
            .scalar() or 0
        )

    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        return document

    def delete_by_id(self, doc_id: UUID, user_id: UUID) -> bool:
        count = (
            self.db.query(Document)
            .filter(Document.id == doc_id, Document.user_id == user_id)
            .delete()
        )
        return count > 0
