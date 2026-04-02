"""Mission service — Domain logic and CRUD operations for persistent missions.

This is the SOURCE OF TRUTH for all mission business rules:
- State machine transitions
- Validation before every mutation
- Progress computation
- Idempotency guarantees

Handlers and MissionTool are thin callers. They resolve targets and
format responses. ALL domain logic lives here.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set, Tuple
from uuid import UUID

from sqlalchemy.orm.attributes import flag_modified

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
from infrastructure.cache.service import CacheService
from utils.log import log_info, log_warning


# ---------------------------------------------------------------------------
# Domain errors — structured failures, not exceptions thrown to the user.
# Every mutation returns (result, error) so callers never guess.
# ---------------------------------------------------------------------------

class MissionDomainError:
    """Structured domain error. Not an exception — returned, not raised."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "message": self.message}


# ---------------------------------------------------------------------------
# State machine — explicit allowed transitions
# ---------------------------------------------------------------------------

# Map: current_status -> set of statuses it CAN transition to.
_ALLOWED_TRANSITIONS: Dict[MissionStatus, Set[MissionStatus]] = {
    MissionStatus.DRAFT:     {MissionStatus.ACTIVE, MissionStatus.ARCHIVED},
    MissionStatus.ACTIVE:    {MissionStatus.COMPLETED, MissionStatus.ARCHIVED},
    MissionStatus.COMPLETED: {MissionStatus.ARCHIVED},
    MissionStatus.ARCHIVED:  set(),  # terminal — no transitions out
}


def _is_valid_transition(current: MissionStatus, target: MissionStatus) -> bool:
    """Check if a status transition is allowed by the state machine."""
    if current == target:
        return False  # no-op / duplicate — reject explicitly
    return target in _ALLOWED_TRANSITIONS.get(current, set())


def _describe_allowed(current: MissionStatus) -> str:
    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if not allowed:
        return f"'{current.value}' is a terminal state — no transitions allowed"
    names = sorted(s.value for s in allowed)
    return f"'{current.value}' can only transition to: {', '.join(names)}"


# ---------------------------------------------------------------------------
# Fields the AI is allowed to update
# ---------------------------------------------------------------------------

_AI_UPDATABLE_FIELDS: Set[str] = {
    "title", "description", "priority", "deadline", "scheduled_start",
    "estimated_minutes", "category", "tags", "steps", "meet_url", "notes",
}

# Status is NOT in the set above. Status changes go through
# dedicated methods (complete_mission, archive_mission) that
# enforce the state machine. The AI cannot set status arbitrarily.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _validate_steps(steps_raw: List[Any]) -> List[Dict[str, Any]]:
    """Validate and normalise a list of step dicts. Returns clean list."""
    clean: List[Dict[str, Any]] = []
    for s in steps_raw[:15]:  # hard cap
        if isinstance(s, dict) and s.get("text"):
            text = str(s["text"]).strip()[:300]
            if text:
                clean.append({"text": text, "done": bool(s.get("done", False))})
        elif isinstance(s, str) and s.strip():
            clean.append({"text": s.strip()[:300], "done": False})
    return clean


def _compute_progress(steps: List[Dict[str, Any]]) -> int:
    """Compute progress percentage from step completion. 0 if no steps."""
    if not steps:
        return 0
    done = sum(1 for s in steps if s.get("done", False))
    return round(done / len(steps) * 100)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MissionService:
    """Service for mission domain operations.

    Every public mutation method returns a tuple:
        (MissionInDB | None, MissionDomainError | None)

    Callers check the error field. If error is not None, the operation
    was rejected and no DB change occurred.
    """

    def __init__(self, mission_repo: MissionRepository, cache_service: Optional[CacheService] = None):
        self.mission_repo = mission_repo
        self._cache = cache_service

    def _invalidate_cache(self, user_id: UUID) -> None:
        if not self._cache:
            return
        try:
            uid_str = str(user_id)
            self._cache.invalidate_mission_stats(uid_str)
            self._cache.invalidate_dashboard(uid_str)
        except Exception as e:
            log_warning(f"Mission cache invalidation failed (user={user_id}): {e}")

    # ------------------------------------------------------------------
    # READ operations (no domain rules needed)
    # ------------------------------------------------------------------

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
        uid_str = str(user_id)
        if self._cache:
            try:
                cached = self._cache.get_cached_mission_stats(uid_str)
                if cached is not None:
                    return cached
            except Exception as e:
                log_warning(f"Mission stats cache read failed: {e}")

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

        if self._cache:
            try:
                self._cache.set_cached_mission_stats(uid_str, result)
            except Exception as e:
                log_warning(f"Mission stats cache write failed: {e}")

        return result

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_mission(
        self, user_id: UUID, data: MissionCreate,
    ) -> Tuple[Optional[MissionInDB], Optional[MissionDomainError]]:
        """Create a single mission from a validated schema."""
        # Title must not be empty (schema enforces this, but belt-and-suspenders)
        if not data.title or not data.title.strip():
            return None, MissionDomainError("EMPTY_TITLE", "Mission title cannot be empty.")

        mission = Mission(
            user_id=user_id,
            thread_id=UUID(data.thread_id) if data.thread_id else None,
            title=data.title.strip(),
            description=data.description,
            status=data.status,
            priority=data.priority,
            source=data.source,
            tags=[str(t) for t in data.tags],
            steps=[s.model_dump() for s in data.steps],
            progress=_compute_progress([s.model_dump() for s in data.steps]),
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
        return MissionInDB.model_validate(mission), None

    def create_missions_from_agent(
        self,
        user_id: UUID,
        missions_json: List[Dict[str, Any]],
        thread_id: Optional[str] = None,
    ) -> Tuple[List[MissionInDB], Optional[MissionDomainError]]:
        """Bulk-create missions extracted by the agent.

        Duplicate detection: if a mission with the exact same title
        (case-insensitive) already exists for this user in DRAFT or
        ACTIVE status, skip it and log a warning.
        """
        if not missions_json:
            return [], MissionDomainError("EMPTY_INPUT", "No missions provided to create.")

        # Load existing titles for dedup
        existing_active = self.mission_repo.list_by_user(
            user_id, status=MissionStatus.ACTIVE, limit=200,
        )
        existing_draft = self.mission_repo.list_by_user(
            user_id, status=MissionStatus.DRAFT, limit=200,
        )
        existing_titles: Set[str] = {
            m.title.strip().lower()
            for m in (*existing_active, *existing_draft)
        }

        created: List[MissionInDB] = []
        for m in missions_json[:5]:
            title = str(m.get("title", "")).strip()
            if not title:
                log_warning("Agent create: skipping mission with empty title")
                continue

            # Duplicate guard
            if title.lower() in existing_titles:
                log_warning(
                    f"Agent create: skipping duplicate title '{title}' "
                    f"(already exists for user {user_id})"
                )
                continue

            steps = _validate_steps(m.get("steps", []))

            priority_raw = m.get("priority", "normal")
            priority = (
                MissionPriority(priority_raw)
                if priority_raw in {"low", "normal", "critical"}
                else MissionPriority.NORMAL
            )

            mission = Mission(
                user_id=user_id,
                thread_id=UUID(thread_id) if thread_id else None,
                title=title[:500],
                description=str(m.get("description", "")).strip()[:2000] or None,
                status=MissionStatus.ACTIVE,
                priority=priority,
                source=MissionSource.AGENT,
                tags=[str(t)[:50] for t in (m.get("tags") or [])[:8]],
                steps=steps,
                progress=_compute_progress(steps),
                deadline=_parse_iso(m.get("deadline")),
                scheduled_start=_parse_iso(m.get("scheduled_start")),
                estimated_minutes=int(m["estimated_minutes"]) if m.get("estimated_minutes") else None,
                meet_url=str(m["meet_url"])[:500] if m.get("meet_url") else None,
                category=str(m["category"])[:100] if m.get("category") else None,
            )
            mission = self.mission_repo.create(mission)
            created.append(MissionInDB.model_validate(mission))
            existing_titles.add(title.lower())
            log_info(f"Agent-created mission {mission.id}: {mission.title}")

        if created:
            self._invalidate_cache(user_id)

        return created, None

    # ------------------------------------------------------------------
    # COMPLETE — enforces state machine
    # ------------------------------------------------------------------

    def complete_mission(
        self, user_id: UUID, mission_id: UUID,
    ) -> Tuple[Optional[MissionInDB], Optional[MissionDomainError]]:
        """Mark a mission as COMPLETED.

        Rules:
        - Mission must exist and belong to user.
        - Must be in ACTIVE status (state machine: ACTIVE -> COMPLETED).
        - If already COMPLETED, return idempotent success (no error, no change).
        """
        mission = self.mission_repo.find_by_id(mission_id, user_id)
        if not mission:
            return None, MissionDomainError(
                "NOT_FOUND",
                f"Mission {mission_id} not found for this user.",
            )

        # Idempotent: already completed -> return current state, no error
        if mission.status == MissionStatus.COMPLETED:
            log_info(f"complete_mission: {mission_id} already completed (idempotent)")
            return MissionInDB.model_validate(mission), None

        # State machine check
        if not _is_valid_transition(mission.status, MissionStatus.COMPLETED):
            return None, MissionDomainError(
                "INVALID_TRANSITION",
                f"Cannot complete mission in '{mission.status.value}' status. "
                f"{_describe_allowed(mission.status)}",
            )

        mission.status = MissionStatus.COMPLETED
        mission.progress = 100
        # Mark all steps as done
        if mission.steps:
            steps = copy.deepcopy(mission.steps)
            for s in steps:
                s["done"] = True
            mission.steps = steps

        self.mission_repo.flush()
        self._invalidate_cache(user_id)
        log_info(f"Completed mission {mission_id}")
        return MissionInDB.model_validate(mission), None

    # ------------------------------------------------------------------
    # UPDATE — enforces field whitelist and state machine
    # ------------------------------------------------------------------

    def update_mission(
        self,
        user_id: UUID,
        mission_id: UUID,
        data: MissionUpdate,
    ) -> Tuple[Optional[MissionInDB], Optional[MissionDomainError]]:
        """Apply a partial update to a mission.

        Rules:
        - Mission must exist and belong to user.
        - Cannot update ARCHIVED or COMPLETED missions (except to archive a completed one).
        - Status changes go through the state machine.
        - AI-forbidden fields are stripped silently.
        - Progress is always recomputed from steps, never set directly by AI.
        """
        mission = self.mission_repo.find_by_id(mission_id, user_id)
        if not mission:
            return None, MissionDomainError(
                "NOT_FOUND",
                f"Mission {mission_id} not found for this user.",
            )

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return None, MissionDomainError(
                "EMPTY_UPDATE",
                "No fields to update were provided.",
            )

        # --- Status change: enforce state machine ---
        if "status" in update_data:
            new_status_raw = update_data.pop("status")
            if new_status_raw is not None:
                try:
                    new_status = MissionStatus(new_status_raw) if isinstance(new_status_raw, str) else new_status_raw
                except ValueError:
                    return None, MissionDomainError(
                        "INVALID_STATUS",
                        f"'{new_status_raw}' is not a valid mission status.",
                    )

                if new_status != mission.status:
                    if not _is_valid_transition(mission.status, new_status):
                        return None, MissionDomainError(
                            "INVALID_TRANSITION",
                            f"Cannot change status from '{mission.status.value}' to "
                            f"'{new_status.value}'. {_describe_allowed(mission.status)}",
                        )
                    mission.status = new_status

        # --- Block updates on terminal states ---
        if mission.status in (MissionStatus.ARCHIVED,):
            remaining = {k for k in update_data if k != "status"}
            if remaining:
                return None, MissionDomainError(
                    "IMMUTABLE_STATE",
                    f"Cannot update fields on an archived mission. "
                    f"Rejected fields: {', '.join(sorted(remaining))}",
                )

        # --- Strip fields AI is not allowed to set ---
        # Progress is always computed, never set directly
        update_data.pop("progress", None)
        update_data.pop("sort_order", None)

        # --- Apply allowed fields ---
        for field, value in update_data.items():
            if field not in _AI_UPDATABLE_FIELDS:
                log_warning(f"update_mission: stripping forbidden field '{field}'")
                continue
            if field == "steps" and value is not None:
                value = _validate_steps(
                    [s.model_dump() if hasattr(s, "model_dump") else s for s in value]
                )
            if field == "title" and value is not None:
                value = str(value).strip()
                if not value:
                    return None, MissionDomainError(
                        "EMPTY_TITLE", "Mission title cannot be empty.",
                    )
                value = value[:500]
            setattr(mission, field, value)
            if field == "steps":
                flag_modified(mission, "steps")

        # --- Recompute progress from steps ---
        mission.progress = _compute_progress(mission.steps or [])

        # --- Auto-complete if all steps done ---
        if (
            mission.steps
            and mission.progress == 100
            and mission.status == MissionStatus.ACTIVE
        ):
            mission.status = MissionStatus.COMPLETED
            log_info(f"update_mission: auto-completed {mission_id} (all steps done)")

        self.mission_repo.flush()
        self._invalidate_cache(user_id)
        log_info(f"Updated mission {mission_id}")
        return MissionInDB.model_validate(mission), None

    # ------------------------------------------------------------------
    # TOGGLE STEP — enforces status check
    # ------------------------------------------------------------------

    def toggle_step(
        self, user_id: UUID, mission_id: UUID, step_index: int,
    ) -> Tuple[Optional[MissionInDB], Optional[MissionDomainError]]:
        """Toggle a step's done status.

        Rules:
        - Mission must exist, belong to user, and be ACTIVE.
        - Step index must be valid.
        - If mission was COMPLETED, toggling a step back is allowed
          (reopens mission to ACTIVE).
        - Toggling the same step twice returns to original state (idempotent by nature).
        """
        mission = self.mission_repo.find_by_id_for_update(mission_id, user_id)
        if not mission:
            return None, MissionDomainError(
                "NOT_FOUND",
                f"Mission {mission_id} not found for this user.",
            )

        if mission.status not in (MissionStatus.ACTIVE, MissionStatus.COMPLETED):
            return None, MissionDomainError(
                "INVALID_STATE",
                f"Cannot toggle steps on a '{mission.status.value}' mission. "
                f"Only 'active' or 'completed' missions allow step toggles.",
            )

        if not mission.steps:
            return None, MissionDomainError(
                "NO_STEPS",
                f"Mission '{mission.title}' has no steps to toggle.",
            )

        steps = copy.deepcopy(mission.steps)

        if step_index < 0 or step_index >= len(steps):
            return None, MissionDomainError(
                "STEP_NOT_FOUND",
                f"Step index {step_index} is out of range. "
                f"Mission '{mission.title}' has {len(steps)} steps (0-{len(steps) - 1}).",
            )

        steps[step_index]["done"] = not steps[step_index].get("done", False)
        mission.steps = steps
        flag_modified(mission, "steps")
        mission.progress = _compute_progress(steps)

        # Auto-complete when all steps done
        if mission.progress == 100 and mission.status == MissionStatus.ACTIVE:
            mission.status = MissionStatus.COMPLETED
            log_info(f"toggle_step: auto-completed {mission_id} (all steps done)")

        # Reopen if a step was unchecked on a completed mission
        if mission.progress < 100 and mission.status == MissionStatus.COMPLETED:
            mission.status = MissionStatus.ACTIVE
            log_info(f"toggle_step: reopened {mission_id} (step unchecked)")

        self.mission_repo.flush()
        self._invalidate_cache(user_id)
        log_info(f"Toggled step {step_index} on mission {mission_id}")
        return MissionInDB.model_validate(mission), None

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete_mission(
        self, user_id: UUID, mission_id: UUID,
    ) -> Tuple[bool, Optional[MissionDomainError]]:
        """Delete a mission.

        Rules:
        - Mission must exist and belong to user.
        - Any status can be deleted (user has full control over cleanup).
        """
        mission = self.mission_repo.find_by_id(mission_id, user_id)
        if not mission:
            return False, MissionDomainError(
                "NOT_FOUND",
                f"Mission {mission_id} not found for this user.",
            )

        deleted = self.mission_repo.delete_by_id(mission_id, user_id)
        if deleted > 0:
            self._invalidate_cache(user_id)
            log_info(f"Deleted mission {mission_id}")
        return deleted > 0, None
