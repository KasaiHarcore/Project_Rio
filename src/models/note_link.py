"""NoteLink model for Obsidian-style linking between notes and resources.

Links are embedded in note content using custom syntax, parsed on save,
and stored as NoteLink rows.  Supports linking to other notes, documents,
artifacts, media (video/audio), and arbitrary URLs.
"""

from typing import Optional
from enum import Enum

import uuid
from sqlalchemy import String, Integer, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base, TimestampMixin


class NoteLinkTargetType(str, Enum):
    """Type of resource a NoteLink points to."""
    NOTE = "note"
    DOCUMENT = "document"
    ARTIFACT = "artifact"
    MEDIA = "media"
    URL = "url"


class NoteLink(Base, TimestampMixin):
    """Obsidian-style link from a note to another resource.

    Attributes:
        id:                  UUID primary key
        user_id:             FK -> user who owns this link
        note_id:             FK -> source note (CASCADE delete)
        label:               Anchor text / display name
        target_type:         note | document | artifact | media | url
        target_note_id:      FK -> target note (SET NULL on delete)
        target_document_id:  FK -> target document (SET NULL on delete)
        target_artifact_id:  FK -> target artifact (SET NULL on delete)
        target_url:          URL for media/url types
        media_meta:          JSONB metadata (video timestamp, slide page, etc.)
        position:            Character offset in note content
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

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("note.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    target_type: Mapped[NoteLinkTargetType] = mapped_column(
        SQLEnum(NoteLinkTargetType, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )

    target_note_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("note.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_url: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True,
    )

    media_meta: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    position: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # -- Relationships --
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    note: Mapped["Note"] = relationship(
        "Note", foreign_keys=[note_id], backref="links",
    )
    target_note: Mapped[Optional["Note"]] = relationship(
        "Note", foreign_keys=[target_note_id],
    )
    target_document: Mapped[Optional["Document"]] = relationship(
        "Document", foreign_keys=[target_document_id],
    )
    target_artifact: Mapped[Optional["Artifact"]] = relationship(
        "Artifact", foreign_keys=[target_artifact_id],
    )

    # -- Composite indexes --
    __table_args__ = (
        Index("ix_note_link_note_target_type", "note_id", "target_type"),
        Index("ix_note_link_target_note_id", "target_note_id"),
    )
