"""AgentMemory model for storing per-user/per-thread agent memories."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

import uuid
from sqlalchemy.types import UserDefinedType
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector as PGVector

from backend.db.base import Base

class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SUMMARY = "summary"


class AgentMemory(Base):
    __tablename__ = "agent_memories"

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

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("thread.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    run_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("run.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    memory_type: Mapped[MemoryType] = mapped_column(
        SQLEnum(MemoryType, name="memory_type"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[Optional[list[float]]] = mapped_column(
        PGVector(),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    user: Mapped["User"] = relationship("User")
    thread: Mapped["Thread"] = relationship("Thread")
    run: Mapped[Optional["Run"]] = relationship("Run")

    __table_args__ = (
        Index("ix_agent_memories_user_thread_created", "user_id", "thread_id", "created_at"),
        Index("ix_agent_memories_run_created", "run_id", "created_at"),
    )
