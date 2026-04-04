"""ReAct tools for mission CRUD operations.

Wraps MissionTool (read) and MissionService (write) as @tool functions
with user_id captured in closures.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.tools import tool

from infrastructure.data_access.mission_tool import MissionTool, get_mission_service_session
from schemas.mission import MissionCreate, MissionStepSchema, MissionUpdate
from utils.log import log_info, log_warning


def build_mission_tools(user_id: str) -> list:
    """Build mission tools with user_id baked into closures."""

    mission_tool = MissionTool()

    @tool
    def list_missions(status: str = "active", limit: int = 20) -> str:
        """List user's missions with full details including steps, progress, and deadlines.

        Args:
            status: Filter by status. Use "active" for current missions,
                    or pass a specific filter value.
            limit: Maximum number of missions to return.

        Returns:
            JSON array of mission objects with id, title, status, priority,
            progress, steps (with index and done flag), deadline, category, tags.
        """
        if status == "active":
            missions = mission_tool.list_active_missions(user_id, limit=limit)
        else:
            result = mission_tool.query_missions(user_id, status=status)
            missions = result.get("missions", [])[:limit]
        return json.dumps(missions, default=str)

    @tool
    def query_missions(
        status: Optional[str] = None,
        deadline_before: Optional[str] = None,
        deadline_after: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        overdue_only: bool = False,
        urgent_only: bool = False,
        tag: Optional[str] = None,
    ) -> str:
        """Query missions with rich filters and get stats.

        Args:
            status: Filter by mission status.
            deadline_before: ISO date — missions due before this date.
            deadline_after: ISO date — missions due after this date.
            category: Filter by category label.
            priority: Filter by priority (low/normal/high/critical).
            overdue_only: Only return overdue missions.
            urgent_only: Only return missions due within 3 days.
            tag: Filter by tag label.

        Returns:
            JSON with stats (total, active, completed, overdue, completion_rate)
            and matching missions array.
        """
        result = mission_tool.query_missions(
            user_id,
            status=status,
            deadline_before=deadline_before,
            deadline_after=deadline_after,
            category=category,
            priority=priority,
            overdue_only=overdue_only,
            urgent_only=urgent_only,
            tag=tag,
        )
        return json.dumps(result, default=str)

    @tool
    def create_mission(
        title: str,
        description: Optional[str] = None,
        priority: str = "normal",
        steps: Optional[List[str]] = None,
        deadline: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        estimated_minutes: Optional[int] = None,
    ) -> str:
        """Create a new mission/goal/task.

        Args:
            title: Mission title (required).
            description: Longer description of the mission.
            priority: Priority level — low, normal, high, or critical.
            steps: List of step descriptions (checklist items).
            deadline: Due date in ISO 8601 format (e.g. "2025-03-30T18:00:00").
            category: Category label for organization.
            tags: Tag labels for filtering.
            estimated_minutes: Estimated time to complete in minutes.

        Returns:
            JSON with the created mission object including its id.
        """
        step_schemas = [MissionStepSchema(text=s) for s in (steps or [])]
        data = MissionCreate(
            title=title,
            description=description,
            priority=priority,
            steps=step_schemas,
            deadline=deadline,
            category=category,
            tags=tags or [],
            estimated_minutes=estimated_minutes,
        )
        with get_mission_service_session() as (svc, _db):
            mission, err = svc.create_mission(UUID(user_id), data)
            if err:
                return json.dumps({"error": str(err)})
            return json.dumps(MissionTool._mission_to_dict(mission), default=str)

    @tool
    def update_mission(mission_id: str, updates: Dict[str, Any]) -> str:
        """Update an existing mission's fields.

        Args:
            mission_id: The mission UUID to update.
            updates: Dict of fields to update. Allowed keys: title, description,
                     priority, deadline, scheduled_start, estimated_minutes,
                     category, tags, steps, meet_url, notes.

        Returns:
            JSON with the updated mission object, or an error.
        """
        data = MissionUpdate(**updates)
        with get_mission_service_session() as (svc, _db):
            mission, err = svc.update_mission(UUID(user_id), UUID(mission_id), data)
            if err:
                return json.dumps({"error": str(err)})
            return json.dumps(MissionTool._mission_to_dict(mission), default=str)

    @tool
    def toggle_mission_step(mission_id: str, step_index: int) -> str:
        """Toggle a mission step's completion status (done/undone).

        Args:
            mission_id: The mission UUID.
            step_index: Zero-based index of the step to toggle.

        Returns:
            JSON with the updated mission object showing new step status.
        """
        with get_mission_service_session() as (svc, _db):
            mission, err = svc.toggle_step(UUID(user_id), UUID(mission_id), step_index)
            if err:
                return json.dumps({"error": str(err)})
            return json.dumps(MissionTool._mission_to_dict(mission), default=str)

    @tool
    def complete_mission(mission_id: str) -> str:
        """Mark an entire mission as completed.

        Args:
            mission_id: The mission UUID to complete.

        Returns:
            JSON with the completed mission object.
        """
        with get_mission_service_session() as (svc, _db):
            mission, err = svc.complete_mission(UUID(user_id), UUID(mission_id))
            if err:
                return json.dumps({"error": str(err)})
            return json.dumps(MissionTool._mission_to_dict(mission), default=str)

    @tool
    def delete_mission(mission_id: str) -> str:
        """Delete a mission.

        Args:
            mission_id: The mission UUID to delete.

        Returns:
            JSON with success status.
        """
        with get_mission_service_session() as (svc, _db):
            success, err = svc.delete_mission(UUID(user_id), UUID(mission_id))
            if err:
                return json.dumps({"error": str(err)})
            return json.dumps({"success": success, "mission_id": mission_id})

    return [
        list_missions,
        query_missions,
        create_mission,
        update_mission,
        toggle_mission_step,
        complete_mission,
        delete_mission,
    ]
