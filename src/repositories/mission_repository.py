"""Mission repository — data access for Mission model."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import func

from models.mission import Mission, MissionStatus, MissionPriority
from repositories.base import BaseRepository


class MissionRepository(BaseRepository):
    """Data access for Mission entities."""

    def find_by_id(self, mission_id: UUID, user_id: UUID) -> Optional[Mission]:
        return (
            self.db.query(Mission)
            .filter(Mission.id == mission_id, Mission.user_id == user_id)
            .first()
        )

    def find_by_id_for_update(self, mission_id: UUID, user_id: UUID) -> Optional[Mission]:
        """Find by ID with SELECT ... FOR UPDATE to prevent concurrent JSONB mutations."""
        return (
            self.db.query(Mission)
            .filter(Mission.id == mission_id, Mission.user_id == user_id)
            .with_for_update()
            .first()
        )

    def list_by_user(
        self,
        user_id: UUID,
        status: Optional[MissionStatus] = None,
        category: Optional[str] = None,
        priority: Optional[MissionPriority] = None,
        overdue_only: bool = False,
        deadline_before: Optional[datetime] = None,
        deadline_after: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Mission]:
        q = self.db.query(Mission).filter(Mission.user_id == user_id)
        if status:
            q = q.filter(Mission.status == status)
        if category:
            q = q.filter(Mission.category == category)
        if priority:
            q = q.filter(Mission.priority == priority)
        if overdue_only:
            now = datetime.now(timezone.utc)
            q = q.filter(
                Mission.deadline.isnot(None),
                Mission.deadline < now,
                Mission.status.in_([MissionStatus.ACTIVE, MissionStatus.DRAFT]),
            )
        if deadline_before:
            q = q.filter(Mission.deadline.isnot(None), Mission.deadline <= deadline_before)
        if deadline_after:
            q = q.filter(Mission.deadline.isnot(None), Mission.deadline >= deadline_after)
        return (
            q.order_by(Mission.sort_order.asc(), Mission.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def find_urgent(
        self, user_id: UUID, deadline_threshold: datetime, limit: int = 5
    ) -> List[Mission]:
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

    def count_by_status(self, user_id: UUID, status: MissionStatus) -> int:
        return (
            self.db.query(func.count(Mission.id))
            .filter(Mission.user_id == user_id, Mission.status == status)
            .scalar() or 0
        )

    def count_total(self, user_id: UUID) -> int:
        return (
            self.db.query(func.count(Mission.id))
            .filter(Mission.user_id == user_id)
            .scalar() or 0
        )

    def count_overdue(self, user_id: UUID) -> int:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(func.count(Mission.id))
            .filter(
                Mission.user_id == user_id,
                Mission.deadline.isnot(None),
                Mission.deadline < now,
                Mission.status.in_([MissionStatus.ACTIVE, MissionStatus.DRAFT]),
            )
            .scalar() or 0
        )

    def count_completed_since(self, user_id: UUID, since: datetime) -> int:
        return (
            self.db.query(func.count(Mission.id))
            .filter(
                Mission.user_id == user_id,
                Mission.status == MissionStatus.COMPLETED,
                Mission.updated_at >= since,
            )
            .scalar() or 0
        )

    def get_distinct_categories(self, user_id: UUID) -> List[str]:
        rows = (
            self.db.query(Mission.category)
            .filter(Mission.user_id == user_id, Mission.category.isnot(None))
            .distinct()
            .all()
        )
        return sorted([r[0] for r in rows if r[0]])

    def create(self, mission: Mission) -> Mission:
        self.db.add(mission)
        self.db.flush()
        return mission

    def delete_by_id(self, mission_id: UUID, user_id: UUID) -> int:
        return (
            self.db.query(Mission)
            .filter(Mission.id == mission_id, Mission.user_id == user_id)
            .delete()
        )
