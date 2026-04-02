"""ReAct tools for automation (scheduled task) operations.

Wraps AutomationService as @tool functions with user_id captured in closures.
"""

from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool

from infrastructure.database.session import get_session_factory
from repositories.automation_repository import AutomationRepository
from services.automation_service import AutomationService
from schemas.automation import AutomationCreate, AutomationUpdate
from utils.log import log_info


def build_automation_tools(user_id: str) -> list:
    """Build automation tools with user_id baked into closures."""

    SessionFactory = get_session_factory()

    def _svc(db_session) -> AutomationService:
        return AutomationService(AutomationRepository(db_session))

    @tool
    def list_automations() -> str:
        """List all scheduled automations for the user.

        Returns:
            JSON array of automations with id, name, cron_expression,
            enabled, next_run_at, run_count.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            automations = svc.list_automations(UUID(user_id))
            return json.dumps(
                [a.model_dump(mode="json") for a in automations], default=str,
            )

    @tool
    def create_automation(
        name: str,
        cron_expression: str,
        agent_instruction: str,
        description: str = "",
        timezone: str = "UTC",
        agent_mode: str = "chat",
        result_delivery: str = "notification",
        max_runs: Optional[int] = None,
    ) -> str:
        """Create a new scheduled automation.

        Args:
            name: Display name for the automation.
            cron_expression: Cron schedule (e.g. '0 9 * * *' for daily at 9am,
                '0 * * * *' for every hour, '0 9 * * 1' for every Monday at 9am,
                '0 9 * * 1-5' for weekdays at 9am).
            agent_instruction: What the agent should do when this fires.
                Write it as a clear prompt (e.g. "Summarize my notes from today"
                or "Review my flashcard stats and tell me what to study").
            description: Optional description.
            timezone: IANA timezone (default UTC).
            agent_mode: Agent mode: chat, rag, or web (default chat).
            result_delivery: How to deliver: notification, note, or chat_thread.
            max_runs: Maximum number of executions (None = unlimited).

        Returns:
            JSON with the created automation.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            auto = svc.create_automation(
                UUID(user_id),
                AutomationCreate(
                    name=name,
                    description=description,
                    cron_expression=cron_expression,
                    timezone=timezone,
                    agent_instruction=agent_instruction,
                    agent_mode=agent_mode,
                    result_delivery=result_delivery,
                    max_runs=max_runs,
                ),
            )
            db.commit()
            return json.dumps(auto.model_dump(mode="json"), default=str)

    @tool
    def update_automation(
        automation_id: str,
        enabled: Optional[bool] = None,
        name: Optional[str] = None,
        cron_expression: Optional[str] = None,
        agent_instruction: Optional[str] = None,
    ) -> str:
        """Update an existing automation (enable/disable, change schedule, etc.).

        Args:
            automation_id: UUID of the automation to update.
            enabled: Set to true/false to enable/disable.
            name: New name (optional).
            cron_expression: New cron schedule (optional).
            agent_instruction: New instruction (optional).

        Returns:
            JSON with the updated automation.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            result = svc.update_automation(
                UUID(user_id),
                UUID(automation_id),
                AutomationUpdate(
                    enabled=enabled,
                    name=name,
                    cron_expression=cron_expression,
                    agent_instruction=agent_instruction,
                ),
            )
            if not result:
                return json.dumps({"error": f"Automation {automation_id} not found"})
            db.commit()
            return json.dumps(result.model_dump(mode="json"), default=str)

    @tool
    def delete_automation(automation_id: str) -> str:
        """Delete a scheduled automation.

        Args:
            automation_id: UUID of the automation to delete.

        Returns:
            JSON with success status.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            success = svc.delete_automation(UUID(user_id), UUID(automation_id))
            if success:
                db.commit()
            return json.dumps({"success": success, "automation_id": automation_id})

    @tool
    def run_automation_now(automation_id: str) -> str:
        """Manually trigger an automation to run immediately.

        Args:
            automation_id: UUID of the automation to run.

        Returns:
            JSON with the execution result.
        """
        with SessionFactory() as db:
            svc = _svc(db)
            result = svc.run_now(UUID(user_id), UUID(automation_id))
            if result is None:
                return json.dumps({"error": f"Automation {automation_id} not found"})
            db.commit()
            return json.dumps({
                "success": True,
                "answer": (result.get("answer", ""))[:2000],
            }, default=str)

    return [
        list_automations,
        create_automation,
        update_automation,
        delete_automation,
        run_automation_now,
    ]
