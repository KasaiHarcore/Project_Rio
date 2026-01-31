"""RunStep repository for CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.core.exceptions import DatabaseError, NotFoundError
from backend.db.models.run_step import RunStep, RunStepStatus
from backend.utils.log import log_debug, log_error, log_success


class RunStepRepository:
	"""Repository for RunStep model CRUD operations."""

	def __init__(self, db: Session):
		self.db = db

	def create(self, step: RunStep) -> RunStep:
		try:
			log_debug(f"Creating run step {step.run_id}:{step.step_index}")
			self.db.add(step)
			self.db.commit()
			self.db.refresh(step)
			log_success(f"Run step created: {step.id}")
			return step
		except SQLAlchemyError as e:
			self.db.rollback()
			log_error(f"Database error creating run step: {str(e)}")
			raise DatabaseError(f"Failed to create run step: {str(e)}")

	def get_by_id(self, step_id: UUID) -> Optional[RunStep]:
		try:
			return self.db.query(RunStep).filter(RunStep.id == step_id).first()
		except SQLAlchemyError as e:
			log_error(f"Database error fetching run step: {str(e)}")
			raise DatabaseError(f"Failed to fetch run step: {str(e)}")

	def update_status(
		self,
		step_id: UUID,
		*,
		status: RunStepStatus,
		ended_at: Optional[datetime] = None,
	) -> RunStep:
		try:
			db_step = self.get_by_id(step_id)
			if not db_step:
				raise NotFoundError(f"RunStep with ID {step_id} not found")
			db_step.status = status
			if ended_at is not None:
				db_step.ended_at = ended_at
			self.db.commit()
			self.db.refresh(db_step)
			log_success(f"Run step updated: {step_id} -> {status}")
			return db_step
		except (NotFoundError, DatabaseError):
			raise
		except SQLAlchemyError as e:
			self.db.rollback()
			log_error(f"Database error updating run step: {str(e)}")
			raise DatabaseError(f"Failed to update run step: {str(e)}")
