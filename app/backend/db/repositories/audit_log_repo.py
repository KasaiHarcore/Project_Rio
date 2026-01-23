"""AuditLog repository for CRUD operations."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from backend.db.models.audit_log import AuditLog
from backend.schemas.audit_log import AuditLogCreate
from backend.core.exceptions import DatabaseError
from backend.utils.log import log_info, log_error, log_debug, log_success


class AuditLogRepository:
    """Repository for AuditLog model CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, log_data: AuditLogCreate) -> AuditLog:
        """Create a new audit log entry.
        
        Args:
            log_data: Audit log creation data
            
        Returns:
            Created audit log instance
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Creating audit log: {log_data.action}")
            
            db_log = AuditLog(
                user_id=log_data.user_id,
                action=log_data.action,
                details=log_data.details,
            )
            
            self.db.add(db_log)
            self.db.commit()
            self.db.refresh(db_log)
            
            log_success(f"Audit log created: {db_log.action} ({db_log.id})")
            return db_log
            
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error creating audit log: {str(e)}")
            raise DatabaseError(f"Failed to create audit log: {str(e)}")

    def get_by_id(self, log_id: UUID) -> Optional[AuditLog]:
        """Get audit log by ID.
        
        Args:
            log_id: Audit log UUID
            
        Returns:
            AuditLog instance or None if not found
        """
        try:
            log_debug(f"Fetching audit log by ID: {log_id}")
            audit_log = self.db.query(AuditLog).filter(AuditLog.id == log_id).first()
            
            return audit_log
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching audit log: {str(e)}")
            raise DatabaseError(f"Failed to fetch audit log: {str(e)}")

    def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs by user.
        
        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of audit log instances
        """
        try:
            log_debug(f"Fetching audit logs for user: {user_id}")
            
            logs = (
                self.db.query(AuditLog)
                .filter(AuditLog.user_id == user_id)
                .order_by(AuditLog.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            log_debug(f"Found {len(logs)} audit logs")
            
            return logs
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching audit logs: {str(e)}")
            raise DatabaseError(f"Failed to fetch audit logs: {str(e)}")

    def get_by_action(
        self,
        action: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs by action.
        
        Args:
            action: Action name
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of audit log instances
        """
        try:
            log_debug(f"Fetching audit logs for action: {action}")
            
            logs = (
                self.db.query(AuditLog)
                .filter(AuditLog.action == action)
                .order_by(AuditLog.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            log_debug(f"Found {len(logs)} audit logs")
            
            return logs
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching audit logs: {str(e)}")
            raise DatabaseError(f"Failed to fetch audit logs: {str(e)}")

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get all audit logs with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of audit log instances
        """
        try:
            log_debug(f"Fetching all audit logs (skip={skip}, limit={limit})")
            
            logs = (
                self.db.query(AuditLog)
                .order_by(AuditLog.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            log_debug(f"Found {len(logs)} audit logs")
            
            return logs
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching audit logs: {str(e)}")
            raise DatabaseError(f"Failed to fetch audit logs: {str(e)}")