"""NoteCollectionMembership — junction table for note <-> collection M2M.

A note can belong to zero or more collections.
A collection can only contain notes (never other collections).
"""

from datetime import datetime
from sqlalchemy import ForeignKey, Index, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
from models.base import Base


class NoteCollectionMembership(Base):
    """Junction table for the note <-> collection many-to-many relationship.

    Attributes:
        note_id:        FK -> note (CASCADE delete)
        collection_id:  FK -> note_collection (CASCADE delete)
        added_at:       When the note was added to this collection
    """

    __tablename__ = "note_collection_membership"

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("note.id", ondelete="CASCADE"),
        primary_key=True,
    )

    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("note_collection.id", ondelete="CASCADE"),
        primary_key=True,
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_ncm_note_id", "note_id"),
        Index("ix_ncm_collection_id", "collection_id"),
    )
