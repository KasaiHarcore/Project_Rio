"""Background scheduler for automation execution.

Uses a simple threading-based approach to check for due automations
every 60 seconds. Avoids heavy dependencies like APScheduler.
"""

from __future__ import annotations

import threading
from utils.log import log_info, log_warning, log_error

_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _automation_loop() -> None:
    """Background thread that checks for and executes due automations."""
    log_info("[Scheduler] Automation checker started (60s interval)")

    while not _stop_event.is_set():
        # Wait 60 seconds between checks (interruptible)
        if _stop_event.wait(timeout=60):
            break

        try:
            _check_due_automations()
        except Exception as e:
            log_error(f"[Scheduler] Automation check failed: {e}")


def _check_due_automations() -> None:
    """Find and execute all due automations."""
    from infrastructure.database.session import get_session_factory
    from repositories.automation_repository import AutomationRepository
    from services.automation_service import AutomationService

    SessionFactory = get_session_factory()
    with SessionFactory() as db:
        repo = AutomationRepository(db)
        svc = AutomationService(repo)
        due = svc.get_due_automations()

        if not due:
            return

        log_info(f"[Scheduler] Found {len(due)} due automation(s)")
        for automation in due:
            try:
                svc.execute_automation(automation)
                db.commit()
            except Exception as e:
                db.rollback()
                log_warning(f"[Scheduler] Automation '{automation.name}' failed: {e}")


def start_scheduler() -> None:
    """Start the automation scheduler background thread."""
    global _scheduler_thread

    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        log_warning("[Scheduler] Already running")
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_automation_loop,
        name="automation-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()
    log_info("[Scheduler] Background scheduler started")


def stop_scheduler() -> None:
    """Stop the automation scheduler background thread."""
    global _scheduler_thread

    if _scheduler_thread is None:
        return

    _stop_event.set()
    _scheduler_thread.join(timeout=5)
    _scheduler_thread = None
    log_info("[Scheduler] Background scheduler stopped")
