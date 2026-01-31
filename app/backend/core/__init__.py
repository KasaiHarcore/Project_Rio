"""Core application primitives.

This module provides:
- Configuration management (settings)
- Custom exceptions for error handling
- Startup/shutdown hooks
"""

from backend.core.settings import (
    # Workflow Constants
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
    # Config Classes
    AgentConfig,
    VectorDBConfig,
    RedisConfig,
    AppConfig,
    # Config Getters
    get_app_config,
    get_vectordb_config,
    get_redis_config,
)
from backend.core.exceptions import (
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
from backend.core.startup import (
    run_startup_tasks,
    run_shutdown_tasks,
    create_database_tables,
)

__all__ = [
    # Constants
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
    # Config Classes
    "AgentConfig",
    "VectorDBConfig",
    "RedisConfig",
    "AppConfig",
    # Config Getters
    "get_app_config",
    "get_vectordb_config",
    "get_redis_config",
    # Exceptions
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
    # Startup/Shutdown
    "run_startup_tasks",
    "run_shutdown_tasks",
    "create_database_tables",
]
