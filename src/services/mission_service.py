"""Mission service — CRUD operations for persistent missions.

Uses MissionRepository for data access. No direct session.query() calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from models.mission import (
    Mission,
    MissionStatus,
    MissionPriority,
    MissionSource,
)
from schemas.mission import (
    MissionCreate,
    MissionUpdate,
    MissionInDB,
    MissionStepSchema,
)
from repositories.mission_repository import MissionRepository
from utils.log import log_info


def _parse_iso(val: Any) -> Optional[datetime]:
    """Attempt to parse an ISO-8601 string into a timezone-aware datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        s = str(val).strip()
        if not s:
            return None
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


class MissionService:
    """Service for mission CRUD operations."""

    def __init__(self, mission_repo: MissionRepository):
        self.mission_repo = mission_repo

    def _invalidate_cache(self, user_id: UUID) -> None:
        """Invalidate mission stats + dashboard cache after any mutation."""
        try:
            from infrastructure.cache import cache_service
            uid_str = str(user_id)
            cache_service.invalidate_mission_stats(uid_str)
            cache_service.invalidate_dashboard(uid_str)
        except Exception:
            pass

    # ── Read ──────────────────────────────────────────────────────────────

    def list_missions(
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
    ) -> List[MissionInDB]:
        rows = self.mission_repo.list_by_user(
            user_id=user_id,
            status=status,
            category=category,
            priority=priority,
            overdue_only=overdue_only,
            deadline_before=deadline_before,
            deadline_after=deadline_after,
            limit=limit,
            offset=offset,
        )
        return [MissionInDB.model_validate(r) for r in rows]

    def get_mission(self, user_id: UUID, mission_id: UUID) -> Optional[MissionInDB]:
        row = self.mission_repo.find_by_id(mission_id, user_id)
        return MissionInDB.model_validate(row) if row else None

    def get_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get aggregate mission stats for dashboard widgets."""
        uid_str = str(user_id)
        try:
            from infrastructure.cache import cache_service
            cached = cache_service.get_cached_mission_stats(uid_str)
            if cached is not None:
                return cached
        except Exception:
            pass

        total = self.mission_repo.count_total(user_id)
        active = self.mission_repo.count_by_status(user_id, MissionStatus.ACTIVE)
        completed = self.mission_repo.count_by_status(user_id, MissionStatus.COMPLETED)
        overdue = self.mission_repo.count_overdue(user_id)
        categories = self.mission_repo.get_distinct_categories(user_id)

        result = {
            "total": total,
            "active": active,
            "completed": completed,
            "overdue": overdue,
            "categories": categories,
        }

        try:
            from infrastructure.cache import cache_service as cs
            cs.set_cached_mission_stats(uid_str, result)
        except Exception:
            pass

        return result

    # ── Create ────────────────────────────────────────────────────────────

    def create_mission(self, user_id: UUID, data: MissionCreate) -> MissionInDB:
        mission = Mission(
            user_id=user_id,
            thread_id=UUID(data.thread_id) if data.thread_id else None,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            source=data.source,
            tags=[str(t) for t in data.tags],
            steps=[s.model_dump() for s in data.steps],
            progress=self._compute_progress(data.steps),
            deadline=data.deadline,
            scheduled_start=data.scheduled_start,
            estimated_minutes=data.estimated_minutes,
            meet_url=data.meet_url,
            category=data.category,
            notes=data.notes,
        )
        mission = self.mission_repo.create(mission)
        log_info(f"Created mission {mission.id} for user {user_id}")
        self._invalidate_cache(user_id)
        return MissionInDB.model_validate(mission)

    def create_missions_from_agent(
        self,
        user_id: UUID,
        missions_json: List[Dict[str, Any]],
        thread_id: Optional[str] = None,
    ) -> List[MissionInDB]:
        """Bulk-create missions extracted by the agent."""
        created: List[MissionInDB] = []
        for m in missions_json[:5]:
            steps_raw = m.get("steps", [])
            steps = []
            for s in steps_raw:
                if isinstance(s, dict) and s.get("text"):
                    steps.append({"text": str(s["text"])[:300], "done": bool(s.get("done", False))})

            mission = Mission(
                user_id=user_id,
                thread_id=UUID(thread_id) if thread_id else None,
                title=str(m.get("title", "Untitled"))[:500],
                description=str(m.get("description", ""))[:2000] or None,
                status=MissionStatus.ACTIVE,
                priority=MissionPriority(m.get("priority", "normal"))
                    if m.get("priority") in {"low", "normal", "critical"}
                    else MissionPriority.NORMAL,
                source=MissionSource.AGENT,
                tags=[str(t)[:50] for t in (m.get("tags") or [])[:8]],
                steps=steps,
                progress=self._compute_progress_from_dicts(steps),
                deadline=_parse_iso(m.get("deadline")),
                estimated_minutes=int(m["estimated_minutes"]) if m.get("estimated_minutes") else None,
                meet_url=str(m["meet_url"])[:500] if m.get("meet_url") else None,
                category=str(m["category"])[:100] if m.get("category") else None,
            )
            mission = self.mission_repo.create(mission)
            created.append(MissionInDB.model_validate(mission))
            log_info(f"Agent-created mission {mission.id}: {mission.title}")

        if created:
            self._invalidate_cache(user_id)
        return created

    # ── Update ────────────────────────────────────────────────────────────

    def update_mission(self, user_id: UUID, mission_id: UUID, data: MissionUpdate) -> Optional[MissionInDB]:
        mission = self.mission_repo.find_by_id(mission_id, user_id)
        if not mission:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "steps" and value is not None:
                value = [s.model_dump() if hasattr(s, "model_dump") else s for s in value]
            setattr(mission, field, value)

        if "steps" in update_data:
            mission.progress = self._compute_progress_from_dicts(mission.steps)

        self.mission_repo.flush()
        self._invalidate_cache(user_id)
        return MissionInDB.model_validate(mission)

    def toggle_step(self, user_id: UUID, mission_id: UUID, step_index: int) -> Optional[MissionInDB]:
        mission = self.mission_repo.find_by_id(mission_id, user_id)
        if not mission or not mission.steps:
            return None

        steps = list(mission.steps)
        if step_index < 0 or step_index >= len(steps):
            return None

        steps[step_index]["done"] = not steps[step_index].get("done", False)
        mission.steps = steps
        mission.progress = self._compute_progress_from_dicts(steps)

        if mission.progress == 100 and mission.status == MissionStatus.ACTIVE:
            mission.status = MissionStatus.COMPLETED

        self.mission_repo.flush()
        self._invalidate_cache(user_id)
        return MissionInDB.model_validate(mission)

    # ── Delete ────────────────────────────────────────────────────────────

    def delete_mission(self, user_id: UUID, mission_id: UUID) -> bool:
        deleted = self.mission_repo.delete_by_id(mission_id, user_id)
        if deleted > 0:
            self._invalidate_cache(user_id)
        return deleted > 0

    # ── Helpers ───────────────────────────────────────────────────────────

    def _compute_progress(self, steps: List[MissionStepSchema]) -> int:
        if not steps:
            return 0
        done = sum(1 for s in steps if s.done)
        return round(done / len(steps) * 100)

    def _compute_progress_from_dicts(self, steps: List[Dict[str, Any]]) -> int:
        if not steps:
            return 0
        done = sum(1 for s in steps if s.get("done", False))
        return round(done / len(steps) * 100)
