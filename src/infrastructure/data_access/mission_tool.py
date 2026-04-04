"""Mission Tool — Read-only DB access and dict serialisation.

This tool handles:
- Session management
- Listing / querying missions (read-only)
- Serialising MissionInDB models to plain dicts

This tool does NOT:
- Perform mutations (create, update, delete, toggle, complete)
- Enforce business rules
- Make domain decisions

All mutations go through MissionService directly from the handlers.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple
from uuid import UUID

from models.mission import MissionStatus
from repositories.mission_repository import MissionRepository
from services.mission_service import MissionService
from infrastructure.database.session import get_session_factory
from utils.log import log_info, log_warning


# ------------------------------------------------------------------
# Shared session helper — used by handlers for mutations
# ------------------------------------------------------------------

@contextmanager
def get_mission_service_session() -> Generator[Tuple[MissionService, Any], None, None]:
    """Yield (MissionService, db_session) inside a managed session.

    Handlers use this to call MissionService directly for mutations.
    Commits on clean exit, rolls back on exception.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        repo = MissionRepository(db)
        try:
            from infrastructure.cache.service import CacheService
            cache = CacheService()
        except Exception:
            cache = None
        svc = MissionService(repo, cache_service=cache)
        yield svc, db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class MissionTool:
    """Read-only DB access for the Mission subgraph.

    Used by:
    - load_missions_node (list active missions)
    - query_node (filtered queries with stats)
    - verify_node (re-read after mutation)
    """

    @contextmanager
    def _session_service(self) -> Generator[Tuple[MissionService, Any], None, None]:
        """Yield (MissionService, db_session) inside a managed session."""
        with get_mission_service_session() as (svc, db):
            yield svc, db

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def list_active_missions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the user's active (and draft) missions as plain dicts."""
        uid = UUID(str(user_id))
        log_info(f"MissionTool.list_active_missions: user_id={uid}, limit={limit}")
        with self._session_service() as (svc, _db):
            missions: list = []
            for status in (MissionStatus.ACTIVE, MissionStatus.DRAFT):
                batch = svc.list_missions(uid, status=status, limit=limit)
                log_info(f"MissionTool: status={status.value} -> {len(batch)} mission(s)")
                missions.extend(batch)
            all_count = svc.mission_repo.count_total(uid)
            log_info(f"MissionTool: total missions across all statuses for user={uid}: {all_count}")
            result = [self._mission_to_dict(m) for m in missions]
            log_info(f"MissionTool.list_active_missions: returning {len(result)} active/draft")
            return result

    def query_missions(
        self,
        user_id: str,
        *,
        status: Optional[str] = None,
        deadline_before: Optional[str] = None,
        deadline_after: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        overdue_only: bool = False,
        completed_since: Optional[str] = None,
        urgent_only: bool = False,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a filtered query and return rich stats + matching missions."""
        from datetime import datetime, timezone, timedelta
        from models.mission import MissionPriority

        uid = UUID(str(user_id))

        with self._session_service() as (svc, _db):
            repo = svc.mission_repo

            stats: Dict[str, Any] = {
                "total": repo.count_total(uid),
                "active": repo.count_by_status(uid, MissionStatus.ACTIVE),
                "completed": repo.count_by_status(uid, MissionStatus.COMPLETED),
                "draft": repo.count_by_status(uid, MissionStatus.DRAFT),
                "archived": repo.count_by_status(uid, MissionStatus.ARCHIVED),
                "overdue": repo.count_overdue(uid),
            }

            if completed_since:
                try:
                    since_dt = datetime.fromisoformat(completed_since)
                    if since_dt.tzinfo is None:
                        since_dt = since_dt.replace(tzinfo=timezone.utc)
                    stats["completed_since"] = repo.count_completed_since(uid, since_dt)
                    stats["completed_since_label"] = completed_since
                except ValueError:
                    pass

            if stats["total"] > 0:
                stats["completion_rate_pct"] = round(
                    stats["completed"] / stats["total"] * 100, 1
                )
            else:
                stats["completion_rate_pct"] = 0.0

            categories = repo.get_distinct_categories(uid)
            stats["categories"] = categories

            ms = None
            if status and status != "all":
                try:
                    ms = MissionStatus(status)
                except ValueError:
                    ms = None

            dl_before = None
            if deadline_before:
                try:
                    dl_before = datetime.fromisoformat(deadline_before)
                    if dl_before.tzinfo is None:
                        dl_before = dl_before.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            dl_after = None
            if deadline_after:
                try:
                    dl_after = datetime.fromisoformat(deadline_after)
                    if dl_after.tzinfo is None:
                        dl_after = dl_after.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            mp = None
            if priority:
                try:
                    mp = MissionPriority(priority)
                except ValueError:
                    pass

            urgent_missions: List[Dict[str, Any]] = []
            if urgent_only:
                threshold = datetime.now(timezone.utc) + timedelta(days=3)
                raw_urgent = repo.find_urgent(uid, deadline_threshold=threshold, limit=10)
                urgent_missions = [self._mission_to_dict(m) for m in raw_urgent]

            missions = repo.list_by_user(
                uid,
                status=ms,
                category=category,
                priority=mp,
                overdue_only=overdue_only,
                deadline_before=dl_before,
                deadline_after=dl_after,
                limit=50,
            )

            if tag:
                tag_lower = tag.lower()
                missions = [
                    m for m in missions
                    if any(tag_lower in t.lower() for t in (m.tags or []))
                ]

            mission_dicts = [self._mission_to_dict(m) for m in missions]

            total_steps = 0
            done_steps = 0
            total_estimated_minutes = 0
            remaining_estimated_minutes = 0
            for m in missions:
                steps = m.steps or []
                total_steps += len(steps)
                for s in steps:
                    done = s.get("done", False) if isinstance(s, dict) else getattr(s, "done", False)
                    if done:
                        done_steps += 1
                est = m.estimated_minutes or 0
                total_estimated_minutes += est
                if steps:
                    incomplete_ratio = 1 - (sum(
                        1 for s in steps
                        if (s.get("done", False) if isinstance(s, dict) else getattr(s, "done", False))
                    ) / len(steps))
                    remaining_estimated_minutes += int(est * incomplete_ratio)
                elif m.status != MissionStatus.COMPLETED:
                    remaining_estimated_minutes += est

            aggregation = {
                "total_steps": total_steps,
                "done_steps": done_steps,
                "pending_steps": total_steps - done_steps,
                "total_estimated_minutes": total_estimated_minutes,
                "remaining_estimated_minutes": remaining_estimated_minutes,
                "remaining_estimated_hours": round(remaining_estimated_minutes / 60, 1),
            }

            result: Dict[str, Any] = {
                "stats": stats,
                "aggregation": aggregation,
                "matching_count": len(mission_dicts),
                "missions": mission_dicts,
            }
            if urgent_only:
                result["urgent_missions"] = urgent_missions
                result["urgent_count"] = len(urgent_missions)

            return result

    # ------------------------------------------------------------------
    # Serialisation (used by read ops and verify_node)
    # ------------------------------------------------------------------

    @staticmethod
    def _step_to_dict(index: int, step: Any) -> Dict[str, Any]:
        if isinstance(step, dict):
            return {"index": index, "text": step.get("text", ""), "done": step.get("done", False)}
        return {"index": index, "text": getattr(step, "text", ""), "done": getattr(step, "done", False)}

    @classmethod
    def _mission_to_dict(cls, m: Any) -> Dict[str, Any]:
        steps = [cls._step_to_dict(i, s) for i, s in enumerate(m.steps)]
        steps_done = sum(1 for s in steps if s["done"])
        return {
            "id": str(m.id),
            "title": m.title,
            "description": m.description,
            "status": m.status.value if hasattr(m.status, "value") else m.status,
            "priority": m.priority.value if hasattr(m.priority, "value") else m.priority,
            "progress": m.progress,
            "steps": steps,
            "steps_total": len(steps),
            "steps_done": steps_done,
            "category": m.category,
            "deadline": m.deadline.isoformat() if m.deadline else None,
            "scheduled_start": m.scheduled_start.isoformat() if getattr(m, "scheduled_start", None) else None,
            "estimated_minutes": m.estimated_minutes if hasattr(m, "estimated_minutes") else None,
            "tags": m.tags if hasattr(m, "tags") else [],
        }
