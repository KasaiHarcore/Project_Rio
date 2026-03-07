"""Thread repository — data access for Thread model."""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import func

from models.thread import Thread, ThreadStatus
from repositories.base import BaseRepository


class ThreadRepository(BaseRepository):
    """Data access for Thread entities."""

    def find_by_id(self, thread_id: UUID) -> Optional[Thread]:
        return self.db.get(Thread, thread_id)

    def find_owned(self, thread_id: UUID, user_id: UUID) -> Optional[Thread]:
        return (
            self.db.query(Thread)
            .filter(Thread.id == thread_id, Thread.user_id == user_id)
            .first()
        )

    def list_by_user(self, user_id: UUID, limit: int = 20) -> List[Thread]:
        return (
            self.db.query(Thread)
            .filter(Thread.user_id == user_id)
            .order_by(Thread.updated_at.desc())
            .limit(limit)
            .all()
        )

    def list_active_by_user(self, user_id: UUID, limit: int = 3) -> List[Thread]:
        return (
            self.db.query(Thread)
            .filter(Thread.user_id == user_id, Thread.status == ThreadStatus.ACTIVE)
            .order_by(Thread.updated_at.desc())
            .limit(limit)
            .all()
        )

    def count_by_user(self, user_id: UUID) -> int:
        return (
            self.db.query(func.count(Thread.id))
            .filter(Thread.user_id == user_id)
            .scalar() or 0
        )

    def count_active_by_user(self, user_id: UUID) -> int:
        return (
            self.db.query(func.count(Thread.id))
            .filter(Thread.user_id == user_id, Thread.status == ThreadStatus.ACTIVE)
            .scalar() or 0
        )

    def user_thread_ids_subquery(self, user_id: UUID):
        """Return a subquery of thread IDs for a user (for joins with messages)."""
        return self.db.query(Thread.id).filter(Thread.user_id == user_id).subquery()

    def create(self, thread: Thread) -> Thread:
        self.db.add(thread)
        self.db.flush()
        return thread

    def hard_delete(self, thread: Thread) -> None:
        self.db.delete(thread)
