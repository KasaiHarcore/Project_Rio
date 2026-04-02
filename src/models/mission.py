"""Mission model for task/goal tracking.

Missions are created either by the agent (auto-extracted from conversations)
or manually by the user.  Each mission can optionally link back to the
conversation thread that spawned it.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from enum import Enum
from models.base import Base, TimestampMixin


class MissionStatus(str, Enum):
    """Mission lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MissionPriority(str, Enum):
    """Mission priority level."""
    LOW = "low"
    NORMAL = "normal"
    CRITICAL = "critical"


class MissionSource(str, Enum):
    """How the mission was created."""
    AGENT = "agent"   # auto-created by the agent during conversation
    USER = "user"     # manually created by the user


class Mission(Base, TimestampMixin):
    """Mission / task model.

    Attributes:
        id:          UUID primary key
        user_id:     FK → user who owns this mission
        thread_id:   Optional FK → the conversation thread that spawned it
        title:       Short mission title
        description: Longer explanation (nullable)
        status:      draft → active → completed / archived
        priority:    low / normal / critical
        source:      agent or user
        progress:    0-100 percent (computed from steps or set manually)
        tags:        JSONB string array  e.g. ["study", "backend"]
        steps:       JSONB array of step objects  [{text, done}, …]
        sort_order:  Integer for user-defined drag-and-drop ordering
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
        ForeignKey("thread.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[MissionStatus] = mapped_column(
        SQLEnum(MissionStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=MissionStatus.ACTIVE,
        index=True,
    )

    priority: Mapped[MissionPriority] = mapped_column(
        SQLEnum(MissionPriority, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=MissionPriority.NORMAL,
    )

    source: Mapped[MissionSource] = mapped_column(
        SQLEnum(MissionSource, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=MissionSource.AGENT,
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    tags: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    steps: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    scheduled_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    estimated_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    meet_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    thread: Mapped[Optional["Thread"]] = relationship("Thread", foreign_keys=[thread_id])

    __table_args__ = (
        Index("ix_mission_user_status", "user_id", "status"),
        Index("ix_mission_user_deadline", "user_id", "deadline"),
    )
