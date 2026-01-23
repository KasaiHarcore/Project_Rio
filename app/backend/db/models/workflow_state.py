"""Deprecated WorkflowState model (no longer used).

LangGraph Postgres checkpoints now handle state persistence keyed by thread ID.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import String, Integer
import uuid
from datetime import datetime
from backend.db.base import Base


class WorkflowState(Base):
    """Persisted LangGraph state snapshots."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    thread_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    run_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    step: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
    )

    node_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    state: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<WorkflowState(id={self.id}, node={self.node_name}, thread_id={self.thread_id})>"
