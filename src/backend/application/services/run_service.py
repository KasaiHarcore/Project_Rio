"""Service to persist LangGraph run metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import inspect

from backend.infrastructure.dto.session import get_db_context, get_engine
from backend.infrastructure.dto.models.run import Run, RunStatus
from backend.infrastructure.dto.repositories.run_repo import RunRepository
from backend.utils.log import log_debug, log_warning


class RunService:
    """Persist LangGraph run metadata to SQL."""

    @staticmethod
    def _table_exists() -> bool:
        """Check if run table exists in database.
        
        Returns False on any error to ensure service degrades gracefully.
        """
        try:
            engine = get_engine()
            inspector = inspect(engine)
            return "run" in inspector.get_table_names()
        except (ConnectionError, TimeoutError) as e:
            log_warning(f"Database connection issue in _table_exists: {e}")
            return False
        except Exception as e:
            # Catch-all for unexpected errors - log but don't crash
            log_warning(f"Unexpected error checking run table existence: {e}")
            return False

    def start_run(
        self,
        *,
        run_id: str,
        thread_id: Optional[str],
        mode: Optional[str],
        model_name: Optional[str],
    ) -> None:
        if not self._table_exists():
            return
        try:
            thread_uuid = None
            if thread_id:
                try:
                    thread_uuid = UUID(thread_id)
                except (ValueError, AttributeError):
                    # ValueError: Invalid UUID format
                    # AttributeError: thread_id doesn't support UUID operations
                    thread_uuid = None
            with get_db_context() as session:
                repo = RunRepository(session)
                run = Run(
                    id=run_id,
                    thread_id=thread_uuid,
                    mode=mode,
                    model_name=model_name,
                    status=RunStatus.RUNNING,
                    started_at=datetime.utcnow(),
                )
                repo.create(run)
        except Exception as e:
            log_warning(f"Failed to start run record: {e}")

    def finish_run(self, *, run_id: str, status: RunStatus, error: Optional[str] = None) -> None:
        if not self._table_exists():
            return
        try:
            with get_db_context() as session:
                repo = RunRepository(session)
                run = repo.get_by_id(run_id)
                if not run:
                    return
                run.status = status
                run.error = error
                run.ended_at = datetime.utcnow()
                session.commit()
        except Exception as e:
            log_warning(f"Failed to finish run record: {e}")


run_service = RunService()
