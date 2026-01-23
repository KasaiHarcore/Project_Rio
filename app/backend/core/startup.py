"""Startup and shutdown hooks for initializing resources."""

from backend.db.base import Base
from backend.db.session import get_engine
from backend.core.settings import get_app_config
from backend.utils.log import log_info, log_success, configure_logging_from_env
import backend.db.models

def create_database_tables() -> None:
    """Ensure all database tables exist."""
    config = get_app_config()
    if not getattr(config, "enable_db_autocreate", False):
        return

    log_info("Checking database schema...")
    engine = get_engine()
    Base.metadata.create_all(engine)
    log_success("Database schema verified")


def run_startup_tasks() -> None:
    """Execute startup tasks."""
    configure_logging_from_env()
    create_database_tables()
