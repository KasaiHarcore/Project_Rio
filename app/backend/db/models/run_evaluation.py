"""RunEvaluation model for storing evaluation results for a Run."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

import uuid
from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class EvaluationVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class RunEvaluation(Base):
    __tablename__ = "run_evaluations"

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

    evaluator: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    verdict: Mapped[Optional[EvaluationVerdict]] = mapped_column(
        SQLEnum(EvaluationVerdict, name="evaluation_verdict"),
        nullable=True,
        index=True,
    )

    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    run: Mapped["Run"] = relationship("Run")

    __table_args__ = (
        Index("ix_run_evaluations_run_created", "run_id", "created_at"),
    )
