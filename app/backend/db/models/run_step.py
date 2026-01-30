"""RunStep model for tracking execution steps within a Run."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

import uuid
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class RunStepType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    RETRIEVAL = "retrieval"
    REFLECTION = "reflection"


class RunStepStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RunStep(Base):
    """
    RunStep model for tracking execution steps within a Run.
    
    Attributes:
        id: UUID primary key
        run_id: Foreign key to Run
        step_index: Index of the step within the run
        step_type: Type of the step (llm, tool, retrieval, reflection)
        name: Optional name of the step
        status: Status of the step (running, succeeded, failed)
        started_at: Timestamp when the step started
        ended_at: Timestamp when the step ended
        run: Relationship to Run model
    """
    __tablename__ = "run_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("run.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    step_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    step_type: Mapped[RunStepType] = mapped_column(
        SQLEnum(RunStepType, name="run_step_type"),
        nullable=False,
        index=True,
    )

    name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[RunStepStatus] = mapped_column(
        SQLEnum(RunStepStatus, name="run_step_status"),
        nullable=False,
        default=RunStepStatus.RUNNING,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    run: Mapped["Run"] = relationship("Run")

    __table_args__ = (
        Index("ix_run_steps_run_step_index", "run_id", "step_index"),
    )
