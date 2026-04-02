"""Core application primitives.

Exports configuration, exceptions, and lifecycle hooks.
"""

from core.settings import (
    TOOL_PREVIEW_LENGTH,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_CHECKPOINT_NS,
    WORKER_TIMEOUT_SECONDS,
    MAX_CONTEXT_LENGTH,
    MAX_RESPONSE_LENGTH,
    STREAM_TOKEN_BATCH_SIZE,
    HUMAN_INTERRUPT_TIMEOUT,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    RETRY_BACKOFF_MAX,
    AgentConfig,
    VectorDBConfig,
    RedisConfig,
    AppConfig,
    get_app_config,
    get_vectordb_config,
    get_redis_config,
)
from core.exceptions import (
    AppException,
    DatabaseError,
    NotFoundError,
    DuplicateError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    WorkflowError,
    ExternalServiceError,
)

def run_startup_tasks() -> None:
    from core.startup import run_startup_tasks as _run_startup_tasks

    return _run_startup_tasks()


def run_shutdown_tasks() -> None:
    from core.startup import run_shutdown_tasks as _run_shutdown_tasks

    return _run_shutdown_tasks()


def create_database_tables() -> None:
    from core.startup import create_database_tables as _create_database_tables

    return _create_database_tables()

__all__ = [
    "TOOL_PREVIEW_LENGTH",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_CHECKPOINT_NS",
    "WORKER_TIMEOUT_SECONDS",
    "MAX_CONTEXT_LENGTH",
    "MAX_RESPONSE_LENGTH",
    "STREAM_TOKEN_BATCH_SIZE",
    "HUMAN_INTERRUPT_TIMEOUT",
    "MAX_RETRIES",
    "RETRY_BACKOFF_BASE",
    "RETRY_BACKOFF_MAX",
    "AgentConfig",
    "VectorDBConfig",
    "RedisConfig",
    "AppConfig",
    "get_app_config",
    "get_vectordb_config",
    "get_redis_config",
    "AppException",
    "DatabaseError",
    "NotFoundError",
    "DuplicateError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ConfigurationError",
    "WorkflowError",
    "ExternalServiceError",
    "run_startup_tasks",
    "run_shutdown_tasks",
    "create_database_tables",
]
