"""Startup and shutdown hooks for initializing resources."""

from backend.db.base import Base
from backend.db.session import get_engine
from backend.core.settings import get_app_config
from backend.security.secrets import load_secrets
from backend.services.llm.registry import register_all_models
from backend.utils.log import (
    log_info,
    log_success,
    log_warning,
    configure_logging_from_env,
)
import backend.db.models
from backend.services.tools.qdrant_tool import vector_db_tool
from backend.services.tools.redis_tool import redis_tool

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
    load_secrets()
    register_all_models()
    configure_logging_from_env()
    create_database_tables()
    vector_db_tool.startup_check()
    redis_tool.enable_llm_cache()
