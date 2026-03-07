"""Artifact model for AI-generated files (code, docs, data).

Artifacts are created by the agent during conversations and stored
persistently. They support versioning via parent_id references.
"""

from typing import Optional
from sqlalchemy import String, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from models.base import Base, TimestampMixin


class Artifact(Base, TimestampMixin):
    """AI-generated artifact model.

    Attributes:
        id:             UUID primary key
        user_id:        FK -> user who owns this artifact
        thread_id:      FK -> the conversation thread (CASCADE delete)
        name:           File name (e.g. "binary_search.py")
        artifact_type:  code | document | data | image
        language:       Programming language or format (optional)
        content:        Full file content
        version:        Version number (starts at 1)
        parent_id:      FK -> previous version of this artifact (optional)
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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    artifact_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="code",
    )

    language: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact.id", ondelete="SET NULL"),
        nullable=True,
    )

    # -- Relationships --
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    thread: Mapped[Optional["Thread"]] = relationship("Thread", foreign_keys=[thread_id])
    parent: Mapped[Optional["Artifact"]] = relationship("Artifact", remote_side=[id], foreign_keys=[parent_id])

    # -- Composite indexes --
    __table_args__ = (
        Index("ix_artifact_user_thread", "user_id", "thread_id"),
    )
