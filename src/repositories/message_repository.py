"""Message repository — data access for Message model."""

from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy import func

from models.message import Message, MessageRole
from repositories.base import BaseRepository


class MessageRepository(BaseRepository):
    """Data access for Message entities."""

    def find_by_thread(
        self, thread_id: UUID, limit: int = 200, order_asc: bool = True
    ) -> List[Message]:
        q = self.db.query(Message).filter(Message.thread_id == thread_id)
        if order_asc:
            q = q.order_by(Message.created_at.asc())
        else:
            q = q.order_by(Message.created_at.desc())
        return q.limit(limit).all()

    def count_by_thread(self, thread_id: UUID) -> int:
        return (
            self.db.query(func.count(Message.id))
            .filter(Message.thread_id == thread_id)
            .scalar() or 0
        )

    def count_by_thread_ids_since(self, thread_ids_subquery, since: datetime) -> int:
        return (
            self.db.query(func.count(Message.id))
            .filter(
                Message.thread_id.in_(self.db.query(thread_ids_subquery)),
                Message.created_at >= since,
            )
            .scalar() or 0
        )

    def count_by_thread_ids_range(
        self, thread_ids_subquery, start: datetime, end: datetime
    ) -> int:
        return (
            self.db.query(func.count(Message.id))
            .filter(
                Message.thread_id.in_(self.db.query(thread_ids_subquery)),
                Message.created_at >= start,
                Message.created_at < end,
            )
            .scalar() or 0
        )

    def count_total_by_user_threads(self, thread_ids_subquery) -> int:
        return (
            self.db.query(func.count(Message.id))
            .filter(Message.thread_id.in_(self.db.query(thread_ids_subquery)))
            .scalar() or 0
        )

    def count_distinct_days_since(self, thread_ids_subquery, since: datetime) -> int:
        return (
            self.db.query(func.count(func.distinct(func.date(Message.created_at))))
            .filter(
                Message.thread_id.in_(self.db.query(thread_ids_subquery)),
                Message.created_at >= since,
            )
            .scalar() or 0
        )

    def create(self, message: Message) -> Message:
        self.db.add(message)
        self.db.flush()
        return message

    def delete_batch(self, messages: List[Message]) -> None:
        for msg in messages:
            self.db.delete(msg)
