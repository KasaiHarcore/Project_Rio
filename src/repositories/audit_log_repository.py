"""Audit log repository — data access for AuditLog model."""

from typing import Optional, List, Dict, Any
from uuid import UUID

from models.audit_log import AuditLog
from repositories.base import BaseRepository


class AuditLogRepository(BaseRepository):
    """Data access for AuditLog entities."""

    def create(self, user_id: Optional[UUID], action: str, details: Optional[Dict[str, Any]] = None) -> AuditLog:
        log = AuditLog(user_id=user_id, action=action, details=details or {})
        self.db.add(log)
        self.db.flush()
        return log

    def list_by_user(self, user_id: UUID, limit: int = 50) -> List[AuditLog]:
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
