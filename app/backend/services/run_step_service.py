"""Service to persist per-run step metadata.

This is best-effort: step tracking must never break agent execution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import inspect

from backend.db.models.run_step import RunStep, RunStepStatus, RunStepType
from backend.db.repositories.run_step_repo import RunStepRepository
from backend.db.session import get_db_context, get_engine
from backend.utils.log import log_warning


class RunStepService:
	"""Persist LangGraph run step metadata to SQL."""

	@staticmethod
	def _table_exists() -> bool:
		"""Check if run_steps table exists in database.
		
		Returns False on any error to ensure service degrades gracefully.
		"""
		try:
			engine = get_engine()
			inspector = inspect(engine)
			# SQLAlchemy inspector API is stable across dialects.
			return inspector.has_table("run_steps")
		except (ConnectionError, TimeoutError) as e:
			log_warning(f"Database connection issue in _table_exists: {e}")
			return False
		except Exception as e:
			# Catch-all for unexpected errors - log but don't crash
			log_warning(f"Unexpected error checking run_steps table: {e}")
			return False

	def start_step(
		self,
		*,
		run_id: str,
		step_index: int,
		step_type: RunStepType,
		name: str,
	) -> Optional[UUID]:
		"""Create a running RunStep and return its id."""
		if not self._table_exists():
			return None
		try:
			with get_db_context() as session:
				repo = RunStepRepository(session)
				step = RunStep(
					run_id=run_id,
					step_index=int(step_index),
					step_type=step_type,
					name=name,
					status=RunStepStatus.RUNNING,
					started_at=datetime.utcnow(),
				)
				repo.create(step)
				return step.id
		except Exception as e:
			log_warning(f"Failed to start run step record: {e}")
			return None

	def finish_step(self, *, step_id: UUID, status: RunStepStatus) -> None:
		"""Mark a RunStep as finished (succeeded/failed)."""
		if not step_id:
			return
		if not self._table_exists():
			return
		try:
			with get_db_context() as session:
				repo = RunStepRepository(session)
				ended_at = datetime.utcnow()
				repo.update_status(step_id, status=status, ended_at=ended_at)
		except Exception as e:
			log_warning(f"Failed to finish run step record: {e}")


run_step_service = RunStepService()
