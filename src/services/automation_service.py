"""Automation service for cron-based scheduled agent execution."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from croniter import croniter

from core.exceptions import ValidationError
from models.automation import Automation, AutomationDelivery
from models.note import NoteSource
from repositories.automation_repository import AutomationRepository
from schemas.automation import AutomationCreate, AutomationUpdate, AutomationInDB
from utils.log import log_info, log_warning, log_error


class AutomationService:
    def __init__(self, repo: AutomationRepository) -> None:
        self._repo = repo

    def list_automations(self, user_id: UUID) -> List[AutomationInDB]:
        automations = self._repo.list_by_user(user_id)
        return [AutomationInDB.model_validate(a) for a in automations]

    def get_automation(self, user_id: UUID, automation_id: UUID) -> Optional[AutomationInDB]:
        auto = self._repo.get_by_id(automation_id, user_id)
        if not auto:
            return None
        return AutomationInDB.model_validate(auto)

    def create_automation(self, user_id: UUID, data: AutomationCreate) -> AutomationInDB:
        if not croniter.is_valid(data.cron_expression):
            raise ValidationError(f"Invalid cron expression: {data.cron_expression}")

        now = datetime.now(timezone.utc)
        cron = croniter(data.cron_expression, now)
        next_run = cron.get_next(datetime)

        automation = Automation(
            id=uuid4(),
            user_id=user_id,
            name=data.name,
            description=data.description,
            cron_expression=data.cron_expression,
            timezone=data.timezone,
            agent_instruction=data.agent_instruction,
            agent_mode=data.agent_mode,
            result_delivery=AutomationDelivery(data.result_delivery),
            next_run_at=next_run,
            max_runs=data.max_runs,
        )
        automation = self._repo.create(automation)
        log_info(f"[Automation] Created '{automation.name}' next_run={next_run}")
        return AutomationInDB.model_validate(automation)

    def update_automation(
        self,
        user_id: UUID,
        automation_id: UUID,
        data: AutomationUpdate,
    ) -> Optional[AutomationInDB]:
        auto = self._repo.get_by_id(automation_id, user_id)
        if not auto:
            return None

        if data.name is not None:
            auto.name = data.name
        if data.description is not None:
            auto.description = data.description
        if data.agent_instruction is not None:
            auto.agent_instruction = data.agent_instruction
        if data.agent_mode is not None:
            auto.agent_mode = data.agent_mode
        if data.result_delivery is not None:
            auto.result_delivery = AutomationDelivery(data.result_delivery)
        if data.enabled is not None:
            auto.enabled = data.enabled
        if data.max_runs is not None:
            auto.max_runs = data.max_runs
        if data.timezone is not None:
            auto.timezone = data.timezone

        if data.cron_expression is not None:
            if not croniter.is_valid(data.cron_expression):
                raise ValidationError(f"Invalid cron expression: {data.cron_expression}")
            auto.cron_expression = data.cron_expression
            now = datetime.now(timezone.utc)
            cron = croniter(data.cron_expression, now)
            auto.next_run_at = cron.get_next(datetime)

        self._repo.flush()
        return AutomationInDB.model_validate(auto)

    def delete_automation(self, user_id: UUID, automation_id: UUID) -> bool:
        return self._repo.delete_by_id(automation_id, user_id)

    def run_now(self, user_id: UUID, automation_id: UUID) -> Optional[dict]:
        """Manually trigger an automation immediately."""
        auto = self._repo.get_by_id(automation_id, user_id)
        if not auto:
            return None
        return self._execute(auto)

    def get_due_automations(self) -> List[Automation]:
        return self._repo.get_due_automations()

    def execute_automation(self, automation: Automation) -> Optional[dict]:
        """Execute a due automation."""
        return self._execute(automation)

    def _execute(self, automation: Automation) -> dict:
        """Run the agent instruction through the workflow pipeline."""
        from workflows.executor import run_workflow
        from core.settings import AgentConfig

        log_info(f"[Automation] Executing '{automation.name}' (id={automation.id})")

        config = AgentConfig(mode=automation.agent_mode)
        thread_id = str(uuid4())

        try:
            result = run_workflow(
                question=automation.agent_instruction,
                config=config,
                history=[],
                thread_id=thread_id,
                user_id=str(automation.user_id),
            )
        except Exception as e:
            log_error(f"[Automation] '{automation.name}' failed: {e}")
            result = {"answer": f"Automation error: {e}", "stats": {}}

        # Update state
        now = datetime.now(timezone.utc)
        cron = croniter(automation.cron_expression, now)
        automation.last_run_at = now
        automation.next_run_at = cron.get_next(datetime)
        automation.run_count += 1
        automation.last_result = {
            "answer": (result.get("answer", ""))[:2000],
            "thread_id": thread_id,
            "executed_at": now.isoformat(),
            "delivery": automation.result_delivery.value,
        }

        # Check max_runs limit
        if automation.max_runs and automation.run_count >= automation.max_runs:
            automation.enabled = False
            log_info(f"[Automation] '{automation.name}' reached max_runs, disabled")

        self._repo.flush()

        # Deliver result via configured channel (never raises)
        delivery_meta = self._deliver_result(automation, result, thread_id)

        # Merge delivery metadata — full reassign required (no MutableDict on JSONB)
        automation.last_result = {**automation.last_result, **delivery_meta}
        self._repo.flush()

        return result

    # ------------------------------------------------------------------
    # Result delivery
    # ------------------------------------------------------------------

    def _deliver_result(
        self,
        automation: Automation,
        result: dict,
        thread_id: str,
    ) -> dict:
        """Dispatch result to the configured delivery channel.

        Returns a metadata dict to merge into ``last_result``.  Never raises.
        """
        delivery = automation.result_delivery
        answer = (result.get("answer", ""))[:5000]

        if delivery == AutomationDelivery.NOTIFICATION:
            return {}

        if delivery == AutomationDelivery.NOTE:
            try:
                return self._deliver_as_note(automation, answer)
            except Exception as e:
                log_error(f"[Automation] Note delivery failed for '{automation.name}': {e}")
                return {"delivery_error": f"Note delivery failed: {e}"[:200]}

        if delivery == AutomationDelivery.CHAT_THREAD:
            try:
                return self._deliver_as_chat_thread(automation, answer)
            except Exception as e:
                log_error(f"[Automation] Chat delivery failed for '{automation.name}': {e}")
                return {"delivery_error": f"Chat delivery failed: {e}"[:200]}

        return {}

    def _deliver_as_note(self, automation: Automation, answer: str) -> dict:
        """Create a note containing the automation result."""
        from repositories.note_repository import NoteRepository
        from services.note_service import NoteService
        from schemas.note import NoteCreate

        db = self._repo.db
        note_repo = NoteRepository(db)
        try:
            from repositories.note_link_repository import NoteLinkRepository
            from services.note_link_service import NoteLinkService
            link_svc = NoteLinkService(NoteLinkRepository(db))
        except Exception:
            link_svc = None

        note_svc = NoteService(note_repo, note_link_service=link_svc)
        data = NoteCreate(
            title=f"Automation: {automation.name}"[:500],
            content=answer,
            source=NoteSource.AGENT,
        )
        note = note_svc.create_note(automation.user_id, data)
        log_info(f"[Automation] Delivered note {note.id} for '{automation.name}'")
        return {"delivered_note_id": str(note.id)}

    def _deliver_as_chat_thread(self, automation: Automation, answer: str) -> dict:
        """Create a chat thread with the instruction and result."""
        from services.chat_history_service import chat_history_service
        from models.message import MessageRole

        title = f"Automation: {automation.name}"[:60]
        chat_thread_id = chat_history_service.ensure_thread(
            user_id=automation.user_id,
            thread_id=None,
            title=title,
        )
        chat_history_service.append_message_async(
            user_id=automation.user_id,
            thread_id=chat_thread_id,
            role=MessageRole.USER,
            content=automation.agent_instruction,
        )
        chat_history_service.append_message_async(
            user_id=automation.user_id,
            thread_id=chat_thread_id,
            role=MessageRole.ASSISTANT,
            content=answer,
        )
        log_info(f"[Automation] Delivered chat thread {chat_thread_id} for '{automation.name}'")
        return {"delivered_thread_id": chat_thread_id}
