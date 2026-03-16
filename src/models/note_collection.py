"""NoteCollection model for organizing notes into folders.

Provides folder-like grouping for notes, similar to Genio.co's
Collections feature. Each collection belongs to a user and can
contain multiple notes.
"""

from typing import Optional
from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from models.base import Base, TimestampMixin


class NoteCollection(Base, TimestampMixin):
    """A named folder for organizing notes.

    Attributes:
        id:       UUID primary key
        user_id:  FK → user who owns this collection
        name:     Collection display name
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    # -- Relationships --
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    notes: Mapped[list["Note"]] = relationship(
        "Note",
        secondary="note_collection_membership",
        back_populates="collections",
    )
