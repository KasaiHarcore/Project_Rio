"""Run repository for CRUD operations."""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from backend.infrastructure.dto.models.run import Run, RunStatus
from backend.core.exceptions import DatabaseError, NotFoundError
from backend.utils.log import log_debug, log_error, log_success


class RunRepository:
    """Repository for Run model CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, run: Run) -> Run:
        try:
            log_debug(f"Creating run {run.id}")
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)
            log_success(f"Run created: {run.id}")
            return run
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error creating run: {str(e)}")
            raise DatabaseError(f"Failed to create run: {str(e)}")

    def get_by_id(self, run_id: str) -> Optional[Run]:
        try:
            return self.db.query(Run).filter(Run.id == run_id).first()
        except SQLAlchemyError as e:
            log_error(f"Database error fetching run: {str(e)}")
            raise DatabaseError(f"Failed to fetch run: {str(e)}")

    def update_status(self, run_id: str, *, status: RunStatus, error: Optional[str] = None) -> Run:
        try:
            db_run = self.get_by_id(run_id)
            if not db_run:
                raise NotFoundError(f"Run with ID {run_id} not found")
            db_run.status = status
            db_run.error = error
            self.db.commit()
            self.db.refresh(db_run)
            log_success(f"Run updated: {run_id} -> {status}")
            return db_run
        except (NotFoundError, DatabaseError):
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error updating run: {str(e)}")
            raise DatabaseError(f"Failed to update run: {str(e)}")
