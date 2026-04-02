"""Administrative endpoints for maintenance and diagnostics.

Provides:
    GET    /admin/stats          - System-wide statistics
    GET    /admin/users          - Paginated user list with stats
    PATCH  /admin/users/{id}     - Update user role
    GET    /admin/audit-logs     - Paginated audit logs
    POST   /admin/reset-database - Full system reset (SQL + vector)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.concurrency import concurrency_manager
from core.dependencies import get_db, require_admin, get_audit_log_repository
from core.exceptions import NotFoundError, ValidationError
from models.user import User, UserRole
from models.thread import Thread, ThreadStatus
from models.message import Message
from models.audit_log import AuditLog
from schemas.admin import (
    AdminSystemStats,
    AdminUserView,
    AdminUserList,
    AdminUserUpdateAction,
    AdminAuditLogView,
    AdminAuditLogList,
)
from repositories.audit_log_repository import AuditLogRepository
from services.admin_service import AdminService
from utils.log import log_info

router = APIRouter(prefix="/admin", tags=["admin"])



@router.get("/stats", response_model=AdminSystemStats)
async def system_stats(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Aggregate system-wide statistics (admin only)."""

    def _query():
        from utils.timezone import utc_now
        from datetime import timedelta

        total_users = db.query(func.count(User.id)).scalar() or 0
        total_threads = db.query(func.count(Thread.id)).scalar() or 0
        total_messages = db.query(func.count(Message.id)).scalar() or 0

        today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        active_users_today = (
            db.query(func.count(func.distinct(Thread.user_id)))
            .filter(Thread.updated_at >= today_start)
            .scalar()
        ) or 0

        active_threads = (
            db.query(func.count(Thread.id))
            .filter(Thread.status == ThreadStatus.ACTIVE)
            .scalar()
        ) or 0

        avg_msg = total_messages / total_threads if total_threads else 0.0
        avg_thr = total_threads / total_users if total_users else 0.0

        return AdminSystemStats(
            total_users=total_users,
            total_threads=total_threads,
            total_messages=total_messages,
            active_users_today=active_users_today,
            active_threads=active_threads,
            avg_messages_per_thread=round(avg_msg, 2),
            avg_threads_per_user=round(avg_thr, 2),
        )

    return await concurrency_manager.run_in_thread(_query)



@router.get("/users", response_model=AdminUserList)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Paginated user list with per-user statistics (admin only)."""

    def _query():
        total = db.query(func.count(User.id)).scalar() or 0
        offset = (page - 1) * page_size

        # Single aggregated query instead of N+1 per-user loop
        thread_stats_sq = (
            db.query(
                Thread.user_id,
                func.count(Thread.id).label("thread_count"),
                func.count(Thread.id).filter(Thread.status == ThreadStatus.ACTIVE).label("active_count"),
            )
            .group_by(Thread.user_id)
            .subquery()
        )

        msg_stats_sq = (
            db.query(
                Thread.user_id,
                func.count(Message.id).label("message_count"),
            )
            .join(Message, Message.thread_id == Thread.id)
            .group_by(Thread.user_id)
            .subquery()
        )

        rows = (
            db.query(
                User,
                func.coalesce(thread_stats_sq.c.thread_count, 0).label("thread_count"),
                func.coalesce(thread_stats_sq.c.active_count, 0).label("active_count"),
                func.coalesce(msg_stats_sq.c.message_count, 0).label("message_count"),
            )
            .outerjoin(thread_stats_sq, User.id == thread_stats_sq.c.user_id)
            .outerjoin(msg_stats_sq, User.id == msg_stats_sq.c.user_id)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        views = [
            AdminUserView(
                id=u.id,
                username=u.username,
                email=u.email,
                role=u.role,
                created_at=u.created_at,
                updated_at=u.updated_at,
                thread_count=tc,
                message_count=mc,
                active_thread_count=ac,
            )
            for u, tc, ac, mc in rows
        ]

        return AdminUserList(
            users=views,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        )

    return await concurrency_manager.run_in_thread(_query)


@router.patch("/users/{user_id}", response_model=AdminUserView)
async def update_user_role(
    user_id: UUID,
    body: AdminUserUpdateAction,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
):
    """Update a user's role (admin only)."""

    def _query():
        target = db.get(User, user_id)
        if not target:
            raise NotFoundError("User not found")

        if body.role is not None:
            old_role = target.role
            target.role = body.role
            db.flush()
            log_info(f"Admin {admin.username} changed role of {target.username}: {old_role} -> {body.role}")
            audit_repo.create(
                user_id=admin.id,
                action="admin.update_user_role",
                details={"target_user_id": str(user_id), "old_role": old_role.value, "new_role": body.role.value},
            )

        return AdminUserView(
            id=target.id,
            username=target.username,
            email=target.email,
            role=target.role,
            created_at=target.created_at,
            updated_at=target.updated_at,
        )

    return await concurrency_manager.run_in_thread(_query)



@router.get("/audit-logs", response_model=AdminAuditLogList)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Paginated audit log (admin only)."""

    def _query():
        total = db.query(func.count(AuditLog.id)).scalar() or 0
        offset = (page - 1) * page_size

        logs = (
            db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        views = []
        for log in logs:
            username = None
            if log.user_id:
                u = db.get(User, log.user_id)
                username = u.username if u else None
            views.append(AdminAuditLogView(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                details=log.details,
                created_at=log.created_at,
                username=username,
            ))

        return AdminAuditLogList(
            logs=views,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        )

    return await concurrency_manager.run_in_thread(_query)



@router.post("/reset-database", status_code=status.HTTP_200_OK)
async def reset_database(
    admin: User = Depends(require_admin),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
):
    """Full system reset: drop/recreate SQL tables and Qdrant collection (admin only)."""

    def _query():
        log_info(f"Admin {admin.username} triggered full system reset")
        AdminService().reset_database()
        return {"message": "System reset completed successfully"}

    return await concurrency_manager.run_in_thread(_query)
