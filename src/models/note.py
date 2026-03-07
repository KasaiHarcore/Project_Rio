"""Note model for persistent sticky notes tied to threads.

Notes are created either by the agent (auto-extracted from conversations)
or manually by the user.  Each note links to the conversation thread that
spawned it and is automatically deleted when the thread is removed.

V2 additions: title, is_important, collection_id, blocks (JSONB), audio (JSONB).
"""

from typing import List, Optional
from sqlalchemy import Boolean, String, Text, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from enum import Enum
from models.base import Base, TimestampMixin


class NoteSource(str, Enum):
    """How the note was created."""
    AGENT = "agent"   # auto-created by the agent during conversation
    USER = "user"     # manually created by the user


class Note(Base, TimestampMixin):
    """Persistent sticky note model.

    Attributes:
        id:             UUID primary key
        user_id:        FK -> user who owns this note
        thread_id:      FK -> the conversation thread (CASCADE delete)
        title:          Note title / heading
        content:        Note text / summary (legacy plain text)
        todos:          JSONB array of todo objects [{text, done}, ...]
        pinned:         Whether the note is pinned to the top
        is_important:   Whether the note is marked as important
        source:         agent or user
        collection_id:  FK -> note_collection (SET NULL on delete)
        blocks:         JSONB array of block objects [{id, type, content, checked}, ...]
        audio:          JSONB audio metadata {id, url, duration, transcript}
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

    thread_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("thread.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    title: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default="",
        server_default="",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    todos: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    is_important: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    source: Mapped[NoteSource] = mapped_column(
        SQLEnum(NoteSource),
        nullable=False,
        default=NoteSource.AGENT,
    )

    collection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("note_collection.id", ondelete="SET NULL"),
        nullable=True,
    )

    blocks: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    audio: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # -- Relationships --
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    thread: Mapped[Optional["Thread"]] = relationship("Thread", foreign_keys=[thread_id])
    collection: Mapped[Optional["NoteCollection"]] = relationship(
        "NoteCollection",
        back_populates="notes",
        foreign_keys=[collection_id],
    )

    # -- Composite indexes --
    __table_args__ = (
        Index("ix_note_user_thread", "user_id", "thread_id"),
        Index("ix_note_collection_id_fk", "collection_id"),
    )
