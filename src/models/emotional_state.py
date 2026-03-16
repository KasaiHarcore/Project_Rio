"""Emotional state model for character-user relationship tracking.

Tracks the AI character's emotional state, mood, energy, and relationship
affinity with each user. Supports the "Living AI" persona system where
characters feel alive and react based on relationship history.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, String, ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from enum import Enum
from models.base import Base, TimestampMixin


class Mood(str, Enum):
    """Character mood states."""
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"
    EXCITED = "excited"
    FRUSTRATED = "frustrated"
    TIRED = "tired"


class EmotionalState(Base, TimestampMixin):
    """Tracks a character's emotional state relative to a specific user.

    Each user-character pair has exactly one EmotionalState record.
    The emotional engine updates this after every interaction.

    Attributes:
        mood:               Current mood (affects response tone + Spine animation)
        energy:             0.0-1.0, decays over time, restored by interaction
        affinity:           0-1000 relationship score (stranger → bonded)
        interaction_count:  Total number of conversations
        streak_days:        Consecutive days of interaction
        mood_history:       Last 20 mood transitions with timestamps
        preferences_learned: Dict of confirmed user preferences
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
        doc="Character identifier (rio, etc.)",
    )

    mood: Mapped[Mood] = mapped_column(
        SQLEnum(Mood, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=Mood.NEUTRAL,
    )

    energy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        server_default="1.0",
        doc="Energy level 0.0-1.0, decays over time",
    )

    affinity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Relationship score 0-1000",
    )

    interaction_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    daily_greeting_done: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether today's greeting has been delivered",
    )

    streak_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Consecutive days of interaction",
    )

    mood_history: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        doc="Last 20 mood transitions: [{from, to, trigger, timestamp}, ...]",
    )

    preferences_learned: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Confirmed user preferences: {coding_language: python, ...}",
    )

    # ── Relationships ──────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    # ── Constraints & Indexes ──────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("user_id", "character_id", name="uq_emotional_state_user_character"),
        Index("ix_emotional_state_user_character", "user_id", "character_id"),
    )
