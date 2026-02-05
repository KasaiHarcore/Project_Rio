"""Run model for LangGraph executions tied to chat threads."""

from typing import List, Optional
from sqlalchemy import String, Enum as SQLEnum, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from enum import Enum
from datetime import datetime
from backend.infrastructure.dto.base import Base


class RunStatus(str, Enum):
    """Run status enumeration."""
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Run(Base):
    """Run model for LangGraph executions.

    Attributes:
        id: Run ID (string hex)
        thread_id: Foreign key to Thread
        mode: Agent mode (rag/web/sql/chat)
        model_name: LLM model name used
        status: Run status
        error: Error message if failed
        started_at: Timestamp when run started
        ended_at: Timestamp when run finished
    """

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        index=True,
    )

    thread_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("thread.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    mode: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    model_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[RunStatus] = mapped_column(
        SQLEnum(RunStatus),
        nullable=False,
        default=RunStatus.RUNNING,
        index=True,
    )

    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    ended_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        index=True,
    )

    thread: Mapped["Thread"] = relationship(
        "Thread",
        back_populates="runs",
    )

    __table_args__ = (
        Index("ix_run_thread_started", "thread_id", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, status={self.status}, thread_id={self.thread_id})>"
