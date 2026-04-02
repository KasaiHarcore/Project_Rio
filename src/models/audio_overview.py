"""AudioOverview model for AI-generated audio study content."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Integer, String, Text, ForeignKey, DateTime
from sqlalchemy import Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base, TimestampMixin


class AudioFormat(str, Enum):
    """Format of the generated audio overview."""
    SUMMARY = "summary"
    DIALOGUE = "dialogue"
    LECTURE = "lecture"


class AudioSourceType(str, Enum):
    """Type of source material."""
    NOTES = "notes"
    DOCUMENTS = "documents"
    FLASHCARDS = "flashcards"


class AudioStatus(str, Enum):
    """Generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class AudioOverview(Base, TimestampMixin):
    """AI-generated audio overview of study materials.

    Attributes:
        id:               UUID primary key
        user_id:          FK -> user who owns this
        title:            Display title
        source_ids:       JSONB list of note/document IDs used as source
        source_type:      notes | documents | flashcards
        transcript:       The generated script text
        audio_path:       Path to the audio file in storage/
        duration_seconds: Audio duration
        format:           summary | dialogue | lecture
        status:           pending | generating | ready | failed
        error_message:    Error details if status is failed
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

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    source_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]",
    )

    source_type: Mapped[AudioSourceType] = mapped_column(
        SQLEnum(AudioSourceType, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AudioSourceType.NOTES,
    )

    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    format: Mapped[AudioFormat] = mapped_column(
        SQLEnum(AudioFormat, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AudioFormat.SUMMARY,
    )

    status: Mapped[AudioStatus] = mapped_column(
        SQLEnum(AudioStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AudioStatus.PENDING,
    )

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_audio_overview_user_status", "user_id", "status"),
    )
