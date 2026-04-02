"""Relationship event model for tracking character-user interaction history.

Each event records a significant interaction that affected the character's
mood or affinity with the user. Used for relationship analytics and
to inform the character's long-term behavioral adaptation.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Integer, String, Text, ForeignKey, Enum as SQLEnum, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from enum import Enum
from models.base import Base


class RelationshipEventType(str, Enum):
    """Types of relationship-affecting events."""
    POSITIVE_INTERACTION = "positive_interaction"
    NEGATIVE_INTERACTION = "negative_interaction"
    HEADPAT = "headpat"
    LONG_ABSENCE = "long_absence"
    TASK_SUCCESS = "task_success"
    TASK_FAILURE = "task_failure"
    COMPLIMENT = "compliment"
    CRITICISM = "criticism"
    DAILY_GREETING = "daily_greeting"
    STREAK_MILESTONE = "streak_milestone"


class RelationshipEvent(Base):
    """Records a single relationship-affecting event.

    Provides an audit trail of how the user-character relationship
    evolved over time. Used by the emotional engine for trend analysis.

    Attributes:
        event_type:     Category of the interaction
        affinity_delta: Change applied to affinity score
        mood_before:    Character mood before this event
        mood_after:     Character mood after this event
        context:        Brief description of what happened
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

    character_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    event_type: Mapped[RelationshipEventType] = mapped_column(
        SQLEnum(RelationshipEventType, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True,
    )

    affinity_delta: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Change applied to affinity score (positive or negative)",
    )

    mood_before: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Character mood before this event",
    )

    mood_after: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Character mood after this event",
    )

    context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Brief description of what triggered this event",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_relationship_event_user_character", "user_id", "character_id"),
        Index("ix_relationship_event_user_created", "user_id", "created_at"),
    )
