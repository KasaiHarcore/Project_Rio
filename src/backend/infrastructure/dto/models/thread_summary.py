"""ThreadSummary model for storing latest summary per thread."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import uuid
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.infrastructure.dto.base import Base


class ThreadSummary(Base):
    """
    ThreadSummary model for storing latest summary per thread.
    
    Attributes:
        thread_id: UUID primary key, foreign key to Thread
        summary: Text field for the thread summary
        updated_at: Timestamp when the summary was last updated
    """
    __tablename__ = "thread_summaries"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("thread.id", ondelete="CASCADE"),
        primary_key=True,
    )

    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )

    thread: Mapped["Thread"] = relationship("Thread")
