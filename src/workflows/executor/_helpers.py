"""
Mission action event builders for workflow executor.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


def _build_standard_mission_action_event(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build mission_action event for standard mission interactions."""
    return {
        "type": "mission_action",
        "action": action,
        "mission": payload.get("mission", {}),
        "step_index": payload.get("step_index"),
    }


def _build_delete_mission_action_event(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build mission_action event for mission deletion."""
    return {
        "type": "mission_action",
        "action": action,
        "mission": {
            "id": payload.get("mission_id"),
            "title": payload.get("title"),
        },
        "step_index": None,
    }


_MISSION_ACTION_EVENT_BUILDERS: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, Any]]] = {
    "toggle_step": _build_standard_mission_action_event,
    "complete_mission": _build_standard_mission_action_event,
    "update_mission": _build_standard_mission_action_event,
    "delete_mission": _build_delete_mission_action_event,
}


def _build_mission_action_event(action: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a mission event from action metadata using declarative dispatch."""
    builder = _MISSION_ACTION_EVENT_BUILDERS.get(action)
    if not builder:
        return None
    return builder(action, payload)
