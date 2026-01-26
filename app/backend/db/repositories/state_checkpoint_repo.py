"""StateCheckpoint repository for CRUD operations."""

from __future__ import annotations

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from backend.db.models.state_checkpoint import StateCheckpoint
from backend.core.exceptions import DatabaseError
from backend.utils.log import log_debug, log_error, log_success


class StateCheckpointRepository:
	"""Repository for StateCheckpoint model CRUD operations."""

	def __init__(self, db: Session):
		self.db = db

	def create(self, checkpoint: StateCheckpoint) -> StateCheckpoint:
		try:
			log_debug(f"Creating state checkpoint {checkpoint.checkpoint_id}")
			self.db.add(checkpoint)
			self.db.commit()
			self.db.refresh(checkpoint)
			log_success(f"State checkpoint created: {checkpoint.checkpoint_id}")
			return checkpoint
		except SQLAlchemyError as e:
			self.db.rollback()
			log_error(f"Database error creating state checkpoint: {str(e)}")
			raise DatabaseError(f"Failed to create state checkpoint: {str(e)}")

	def get_latest_for_thread(self, thread_id: UUID) -> Optional[StateCheckpoint]:
		try:
			return (
				self.db.query(StateCheckpoint)
				.filter(StateCheckpoint.thread_id == thread_id)
				.order_by(StateCheckpoint.round_index.desc())
				.first()
			)
		except SQLAlchemyError as e:
			log_error(f"Database error fetching latest state checkpoint: {str(e)}")
			raise DatabaseError(f"Failed to fetch state checkpoint: {str(e)}")

	def get_next_round_index(self, thread_id: UUID) -> int:
		try:
			value = (
				self.db.query(func.max(StateCheckpoint.round_index))
				.filter(StateCheckpoint.thread_id == thread_id)
				.scalar()
			)
			return int(value or 0) + 1
		except SQLAlchemyError as e:
			log_error(f"Database error computing round index: {str(e)}")
			raise DatabaseError(f"Failed to compute round index: {str(e)}")
