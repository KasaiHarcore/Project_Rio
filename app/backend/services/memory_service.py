"""Services for agent memory and thread summaries."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.db.models.agent_memory import AgentMemory, MemoryType
from backend.db.models.thread_summary import ThreadSummary
from backend.db.session import get_db_context, get_engine
from backend.utils.log import log_debug


def _parse_uuid(value: Optional[str | UUID]) -> Optional[UUID]:
    if not value:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except Exception:
        return None


class MemoryService:
    """Persist long-term agent memories and thread summaries."""

    @staticmethod
    def _agent_table_exists() -> bool:
        try:
            engine = get_engine()
            inspector = inspect(engine)
            return inspector.has_table("agent_memories")
        except Exception:
            return False

    @staticmethod
    def _summary_table_exists() -> bool:
        try:
            engine = get_engine()
            inspector = inspect(engine)
            return inspector.has_table("thread_summaries")
        except Exception:
            return False

    def add_agent_memory(
        self,
        *,
        user_id: UUID | str,
        thread_id: UUID | str,
        run_id: Optional[str],
        memory_type: MemoryType,
        content: str,
        embedding: Optional[list[float]] = None,
    ) -> None:
        if not content or not memory_type:
            return
        if not self._agent_table_exists():
            return

        user_uuid = _parse_uuid(user_id)
        thread_uuid = _parse_uuid(thread_id)
        if not user_uuid or not thread_uuid:
            return
        def _write(sess: Session) -> None:
            memory = AgentMemory(
                user_id=user_uuid,
                thread_id=thread_uuid,
                run_id=run_id,
                memory_type=memory_type,
                content=content,
                embedding=embedding,
            )
            sess.add(memory)

        try:
            with get_db_context() as db:
                _write(db)
        except Exception as e:
            log_debug(f"Agent memory write skipped: {e}")

    def upsert_thread_summary(
        self,
        *,
        thread_id: UUID | str,
        summary: str,
    ) -> None:
        if not summary:
            return
        if not self._summary_table_exists():
            return
        thread_uuid = _parse_uuid(thread_id)
        if not thread_uuid:
            return
        def _write(sess: Session) -> None:
            existing = sess.query(ThreadSummary).filter(ThreadSummary.thread_id == thread_uuid).first()
            if existing:
                existing.summary = summary
                existing.updated_at = datetime.utcnow()
                return
            sess.add(ThreadSummary(thread_id=thread_uuid, summary=summary))

        try:
            with get_db_context() as db:
                _write(db)
        except Exception as e:
            log_debug(f"Thread summary write skipped: {e}")

    def get_thread_summary(self, *, thread_id: UUID | str) -> Optional[str]:
        if not self._summary_table_exists():
            return None
        thread_uuid = _parse_uuid(thread_id)
        if not thread_uuid:
            return None

        try:
            with get_db_context() as db:
                record = db.query(ThreadSummary).filter(ThreadSummary.thread_id == thread_uuid).first()
                if record and record.summary:
                    return record.summary
        except Exception as e:
            log_debug(f"Thread summary read skipped: {e}")
        return None


memory_service = MemoryService()
