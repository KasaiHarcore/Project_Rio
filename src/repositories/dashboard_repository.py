"""Dashboard repository — read-only cross-model projections for dashboard stats."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.document import Document, DocumentStatus
from models.message import Message
from models.mission import Mission, MissionStatus
from models.thread import Thread, ThreadStatus
from models.user_profile import UserProfile
from repositories.base import BaseRepository


class DashboardRepository(BaseRepository):
    """Read-only data access for dashboard aggregate queries."""

    def get_thread_stats(self, user_id: UUID) -> Dict[str, int]:
        """Return total and active thread counts."""
        total = (
            self.db.query(func.count(Thread.id))
            .filter(Thread.user_id == user_id)
            .scalar() or 0
        )
        active = (
            self.db.query(func.count(Thread.id))
            .filter(Thread.user_id == user_id, Thread.status == ThreadStatus.ACTIVE)
            .scalar() or 0
        )
        return {"total": total, "active": active}

    def get_message_stats(self, user_id: UUID) -> Dict[str, int]:
        """Return total messages and messages today."""
        user_thread_ids = self.db.query(Thread.id).filter(Thread.user_id == user_id).subquery()
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total = (
            self.db.query(func.count(Message.id))
            .filter(Message.thread_id.in_(self.db.query(user_thread_ids)))
            .scalar() or 0
        )
        today = (
            self.db.query(func.count(Message.id))
            .filter(
                Message.thread_id.in_(self.db.query(user_thread_ids)),
                Message.created_at >= today_start,
            )
            .scalar() or 0
        )
        return {"total": total, "today": today}

    def get_messages_by_day(self, user_id: UUID, days: int = 7) -> List[int]:
        """Return message counts per day for the last N days (single GROUP BY query)."""
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        user_thread_ids = self.db.query(Thread.id).filter(Thread.user_id == user_id).subquery()

        rows = (
            self.db.query(
                func.date(Message.created_at).label("day"),
                func.count(Message.id).label("cnt"),
            )
            .filter(
                Message.thread_id.in_(self.db.query(user_thread_ids)),
                Message.created_at >= start,
            )
            .group_by(func.date(Message.created_at))
            .all()
        )

        counts_by_date = {str(r.day): r.cnt for r in rows}
        result = []
        for days_ago in range(days - 1, -1, -1):
            day = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            result.append(counts_by_date.get(day, 0))
        return result

    def get_document_stats(self, user_id: UUID) -> Dict[str, int]:
        """Return total and ready document counts."""
        total = (
            self.db.query(func.count(Document.id))
            .filter(Document.user_id == user_id)
            .scalar() or 0
        )
        ready = (
            self.db.query(func.count(Document.id))
            .filter(Document.user_id == user_id, Document.status == DocumentStatus.READY)
            .scalar() or 0
        )
        return {"total": total, "ready": ready}

    def get_recent_threads_with_msg_count(
        self, user_id: UUID, limit: int = 6
    ) -> List[Tuple]:
        """Return recent threads with message counts using LEFT JOIN (no N+1)."""
        rows = (
            self.db.query(
                Thread,
                func.count(Message.id).label("msg_count"),
            )
            .outerjoin(Message, Message.thread_id == Thread.id)
            .filter(Thread.user_id == user_id)
            .group_by(Thread.id)
            .order_by(Thread.updated_at.desc())
            .limit(limit)
            .all()
        )
        return rows

    def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Return user profile if exists."""
        return (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )

    def get_missions_completed_since(self, user_id: UUID, since: datetime) -> int:
        """Count missions completed since a given time."""
        return (
            self.db.query(func.count(Mission.id))
            .filter(
                Mission.user_id == user_id,
                Mission.status == MissionStatus.COMPLETED,
                Mission.updated_at >= since,
            )
            .scalar() or 0
        )

    def get_sessions_since(self, user_id: UUID, since: datetime) -> int:
        """Count distinct days with messages since a given time."""
        user_thread_ids = self.db.query(Thread.id).filter(Thread.user_id == user_id).subquery()
        return (
            self.db.query(func.count(func.distinct(func.date(Message.created_at))))
            .filter(
                Message.thread_id.in_(self.db.query(user_thread_ids)),
                Message.created_at >= since,
            )
            .scalar() or 0
        )

    def get_urgent_missions(
        self, user_id: UUID, deadline_threshold: datetime, limit: int = 5
    ) -> List[Mission]:
        """Return active missions with deadlines within threshold."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(Mission)
            .filter(
                Mission.user_id == user_id,
                Mission.status == MissionStatus.ACTIVE,
                Mission.deadline.isnot(None),
                Mission.deadline <= deadline_threshold,
                Mission.deadline >= now,
            )
            .order_by(Mission.deadline.asc())
            .limit(limit)
            .all()
        )

    def get_active_threads(self, user_id: UUID, limit: int = 3) -> List[Thread]:
        """Return recent active threads."""
        return (
            self.db.query(Thread)
            .filter(Thread.user_id == user_id, Thread.status == ThreadStatus.ACTIVE)
            .order_by(Thread.updated_at.desc())
            .limit(limit)
            .all()
        )
