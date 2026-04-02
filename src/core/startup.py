"""Startup and Shutdown Hooks for Application Lifecycle.

This module provides initialization functions that run when the
application starts. These ensure all required resources are
properly configured before handling requests.

Startup sequence:
1. Register LLM models (fast, no I/O)
2. Validate configuration
3. Configure logging
4. Parallel I/O: database tables + vector DB + Redis cache
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from models.base import Base
from infrastructure.database.session import get_engine
from core.settings import get_app_config
from core.exceptions import ConfigurationError
from infrastructure.llm.registry import register_all_models
from utils.log import (
    log_info,
    log_success,
    log_warning,
    log_error,
    configure_logging_from_env,
)
import models  # noqa: F401
from infrastructure.tools.qdrant_tool import get_vector_db_tool
from infrastructure.cache.redis_cache import redis_tool


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


def _init_vector_db() -> None:
    """Initialize vector DB (heavy: downloads embedding models)."""
    try:
        get_vector_db_tool().startup_check()
    except Exception as e:
        log_warning(f"Vector DB initialization failed (will retry lazily): {e}")


def _init_redis_cache() -> None:
    """Enable Redis LLM cache."""
    try:
        redis_tool.enable_llm_cache()
    except Exception as e:
        log_warning(f"Redis LLM cache init failed: {e}")


def run_startup_tasks() -> None:
    """
    Execute all startup tasks. I/O-bound tasks run in parallel.
    """
    log_info("Running startup tasks...")

    # 1. Register LLM models (fast, no I/O)
    register_all_models()

    # 2. Validate configuration
    config = get_app_config()
    ok, errors = config.validate()
    if not ok:
        for err in errors:
            log_error(f"Config validation: {err}")
        raise ConfigurationError(
            "Application configuration is invalid",
            details={"errors": errors},
        )
    log_success("Configuration validated")

    # 3. Configure logging
    configure_logging_from_env()

    # 4. Parallel I/O: database + vector DB + Redis
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="startup") as pool:
        fut_db = pool.submit(create_database_tables)
        fut_vec = pool.submit(_init_vector_db)
        fut_redis = pool.submit(_init_redis_cache)

        # Wait for all — database is required, others are best-effort
        fut_db.result()  # raises on failure
        fut_vec.result()
        fut_redis.result()

    # 5. Start automation scheduler
    try:
        from core.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        log_warning(f"Automation scheduler failed to start: {e}")

    log_success("All startup tasks completed")


def run_shutdown_tasks() -> None:
    """
    Execute cleanup tasks on application shutdown.
    
    Call this when the application is shutting down gracefully.
    """
    log_info("Running shutdown tasks...")
    try:
        from core.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    log_success("Shutdown tasks completed")
