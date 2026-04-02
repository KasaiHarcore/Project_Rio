"""Repository for Automation data access."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models.automation import Automation
from repositories.base import BaseRepository


class AutomationRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_by_user(
        self,
        user_id: UUID,
        enabled_only: bool = False,
    ) -> List[Automation]:
        q = self.db.query(Automation).filter(Automation.user_id == user_id)
        if enabled_only:
            q = q.filter(Automation.enabled == True)  # noqa: E712
        return q.order_by(Automation.created_at.desc()).all()

    def get_by_id(self, automation_id: UUID, user_id: UUID) -> Optional[Automation]:
        return (
            self.db.query(Automation)
            .filter(Automation.id == automation_id, Automation.user_id == user_id)
            .first()
        )

    def get_due_automations(self) -> List[Automation]:
        """Get all enabled automations whose next_run_at is in the past."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(Automation)
            .filter(
                Automation.enabled == True,  # noqa: E712
                Automation.next_run_at != None,  # noqa: E711
                Automation.next_run_at <= now,
            )
            .all()
        )

    def create(self, automation: Automation) -> Automation:
        return self.add(automation)

    def delete_by_id(self, automation_id: UUID, user_id: UUID) -> bool:
        auto = self.get_by_id(automation_id, user_id)
        if auto:
            self.delete(auto)
            return True
        return False
