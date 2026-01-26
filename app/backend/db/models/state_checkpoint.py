"""StateCheckpoint model for mapping LangGraph checkpoints to SQL threads/runs."""

from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from backend.db.base import Base, TimestampMixin


class StateCheckpoint(Base, TimestampMixin):
	"""Persisted mapping between LangGraph checkpoints and SQL threads/runs."""

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		default=uuid.uuid4,
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
		ForeignKey("run.id", ondelete="SET NULL"),
		nullable=True,
		index=True,
	)

	checkpoint_id: Mapped[str] = mapped_column(
		String(128),
		nullable=False,
		index=True,
	)

	checkpoint_ns: Mapped[str] = mapped_column(
		String(64),
		nullable=False,
		index=True,
		default="",
	)

	parent_checkpoint_id: Mapped[Optional[str]] = mapped_column(
		String(128),
		nullable=True,
		index=True,
	)

	round_index: Mapped[int] = mapped_column(
		Integer,
		nullable=False,
		default=1,
		index=True,
	)

	node_count: Mapped[Optional[int]] = mapped_column(
		Integer,
		nullable=True,
	)

	checkpoint_metadata: Mapped[Optional[dict]] = mapped_column(
		JSONB,
		nullable=True,
	)

	thread: Mapped["Thread"] = relationship(
		"Thread",
		backref="state_checkpoints",
	)

	run: Mapped[Optional["Run"]] = relationship(
		"Run",
		backref="state_checkpoints",
	)

	__table_args__ = (
		Index("ix_state_checkpoint_thread_round", "thread_id", "round_index"),
		Index("ix_state_checkpoint_thread_created", "thread_id", "created_at"),
	)

	def __repr__(self) -> str:
		return (
			f"<StateCheckpoint(id={self.id}, thread_id={self.thread_id}, "
			f"checkpoint_id={self.checkpoint_id}, round_index={self.round_index})>"
		)
