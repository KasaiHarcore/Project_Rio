"""Automation model for cron-based scheduled agent execution."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy import Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from models.base import Base, TimestampMixin


class AutomationDelivery(str, Enum):
    """How the automation result is delivered to the user."""
    CHAT_THREAD = "chat_thread"
    NOTE = "note"
    NOTIFICATION = "notification"


class Automation(Base, TimestampMixin):
    """Scheduled autonomous agent execution.

    Attributes:
        id:                UUID primary key
        user_id:           FK -> user who owns this automation
        name:              Display name
        description:       Optional description
        cron_expression:   Cron schedule (e.g. '0 9 * * *' = every day at 9am)
        timezone:          IANA timezone for cron evaluation
        agent_instruction: What Rio should do when this fires
        agent_mode:        Agent mode: chat | rag | web
        result_delivery:   How to deliver the result
        enabled:           Whether the automation is active
        last_run_at:       When it last executed
        next_run_at:       Next scheduled execution
        run_count:         Total executions
        max_runs:          Maximum executions (None = unlimited)
        last_result:       JSONB with last execution result
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

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True, default="", server_default="")

    # Schedule
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC", server_default="UTC")

    # Agent instruction
    agent_instruction: Mapped[str] = mapped_column(Text, nullable=False)
    agent_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="chat", server_default="chat")

    # Delivery
    result_delivery: Mapped[AutomationDelivery] = mapped_column(
        SQLEnum(AutomationDelivery, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AutomationDelivery.NOTIFICATION,
    )

    # State
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_runs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_automation_user_enabled", "user_id", "enabled"),
        Index("ix_automation_next_run", "next_run_at"),
    )
