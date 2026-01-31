"""Startup and Shutdown Hooks for Application Lifecycle.

This module provides initialization functions that run when the
application starts. These ensure all required resources are
properly configured before handling requests.

Startup sequence:
1. Load secrets from environment
2. Register LLM models
3. Configure logging
4. Create database tables (if enabled)
5. Initialize vector DB
6. Enable Redis LLM cache
"""

from backend.db.base import Base
from backend.db.session import get_engine
from backend.core.settings import get_app_config
from backend.security.secrets import load_secrets
from backend.services.llm.registry import register_all_models
from backend.utils.log import (
    log_info,
    log_success,
    log_warning,
    log_error,
    configure_logging_from_env,
)
import backend.db.models  # noqa: F401 - imports for side effects (model registration)
from backend.services.tools.qdrant_tool import vector_db_tool
from backend.services.tools.redis_tool import redis_tool


def create_database_tables() -> None:
    """
    Ensure all database tables exist.
    
    Only runs if enable_db_autocreate is True in AppConfig.
    This is typically used in development; production should
    use migrations (Alembic).
    """
    config = get_app_config()
    if not getattr(config, "enable_db_autocreate", False):
        log_info("Database auto-create disabled, skipping schema check")
        return

    log_info("Checking database schema...")
    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
        log_success("Database schema verified")
    except Exception as e:
        log_error(f"Failed to create database tables: {e}")
        raise


def run_startup_tasks() -> None:
    """
    Execute all startup tasks in order.
    
    This is the main entry point for application initialization.
    Call this once when the application starts.
    """
    log_info("Running startup tasks...")
    
    # 1. Load secrets from environment
    load_secrets()
    
    # 2. Register LLM models
    register_all_models()
    
    # 3. Configure logging
    configure_logging_from_env()
    
    # 4. Create database tables (if enabled)
    create_database_tables()
    
    # 5. Initialize vector DB
    vector_db_tool.startup_check()
    
    # 6. Enable Redis LLM cache
    redis_tool.enable_llm_cache()
    
    log_success("All startup tasks completed")


def run_shutdown_tasks() -> None:
    """
    Execute cleanup tasks on application shutdown.
    
    Call this when the application is shutting down gracefully.
    """
    log_info("Running shutdown tasks...")
    # Add cleanup tasks here as needed
    log_success("Shutdown tasks completed")
