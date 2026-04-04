"""Flashcard model with SM-2 spaced repetition scheduling fields."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Float, Integer, Text, ForeignKey, DateTime
from sqlalchemy import Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base, TimestampMixin


class FlashcardSource(str, Enum):
    """How the flashcard was created."""
    AGENT = "agent"
    USER = "user"


class Flashcard(Base, TimestampMixin):
    """Flashcard with SM-2 spaced repetition scheduling.

    Attributes:
        id:              UUID primary key
        user_id:         FK -> user who owns this card
        deck_id:         FK -> flashcard_deck (CASCADE delete)
        note_id:         Optional FK -> source note (SET NULL on delete)
        front:           Question / prompt text
        back:            Answer text
        ease_factor:     SM-2 ease factor (>= 1.3, default 2.5)
        interval_days:   Current interval in days
        repetitions:     Number of consecutive correct reviews
        next_review:     Next scheduled review datetime
        source:          agent or user
        tags:            JSONB string array
        is_suspended:    Whether the card is temporarily excluded from review
        total_reviews:   Lifetime review count
        correct_count:   Lifetime correct count
        streak:          Current consecutive-correct streak
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

    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("flashcard_deck.id", ondelete="CASCADE"),
        nullable=False,
    )

    note_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("note.id", ondelete="SET NULL"),
        nullable=True,
    )

    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)

    # SM-2 scheduling fields
    ease_factor: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.5, server_default="2.5",
    )
    interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    repetitions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    next_review: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    # Metadata
    source: Mapped[FlashcardSource] = mapped_column(
        SQLEnum(FlashcardSource, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=FlashcardSource.USER,
    )
    tags: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]",
    )
    is_suspended: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )

    # Review stats
    total_reviews: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    correct_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    streak: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    deck = relationship("FlashcardDeck", back_populates="flashcards")
    note = relationship("Note", foreign_keys=[note_id])

    __table_args__ = (
        Index("ix_flashcard_user_next_review", "user_id", "next_review"),
        Index("ix_flashcard_deck_next_review", "deck_id", "next_review"),
    )
