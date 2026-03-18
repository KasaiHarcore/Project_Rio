"""Logging configuration"""

from __future__ import annotations

import os
import sys
from typing import Final

from loguru import logger


def configure_logging(
    *,
    level: str = "INFO",
    json_logs: bool = False,
    log_file: str | None = None,
    rotation: str = "10 MB",
    retention: str = "14 days",
    backtrace: bool = False,
    diagnose: bool = False,
    stdout: bool = True,
) -> None:
    """Configure loguru sinks for production use."""
    logger.remove()

    sink_options = {
        "level": level,
        "backtrace": backtrace,
        "diagnose": diagnose,
        "enqueue": True,
        "colorize": not json_logs,
        "serialize": json_logs,
    }

    if stdout:
        logger.add(sys.stdout, **sink_options)

    if log_file:
        logger.add(
            log_file,
            **sink_options,
            rotation=rotation,
            retention=retention,
        )

    # Add log buffer sink for web streaming
    from utils.log_buffer import log_buffer_sink
    logger.add(log_buffer_sink, level=level, format="{message}", colorize=False)


def configure_logging_from_env(default_level: str = "INFO") -> None:
    """Configure logging using environment variables."""
    level = os.getenv("LOG_LEVEL", default_level)
    json_logs = os.getenv("LOG_JSON", "False").lower() == "true"
    log_file = os.getenv("LOG_FILE")
    rotation = os.getenv("LOG_ROTATION", "10 MB")
    retention = os.getenv("LOG_RETENTION", "14 days")
    backtrace = os.getenv("LOG_BACKTRACE", "False").lower() == "true"
    diagnose = os.getenv("LOG_DIAGNOSE", "False").lower() == "true"
    stdout = os.getenv("LOG_STDOUT", "True").lower() == "true"

    configure_logging(
        level=level,
        json_logs=json_logs,
        log_file=log_file,
        rotation=rotation,
        retention=retention,
        backtrace=backtrace,
        diagnose=diagnose,
        stdout=stdout,
    )


# Helpers
def log_exception(exception: Exception) -> None:
    logger.exception(exception)


def log_debug(msg: str, print_console: bool = False, **kwargs) -> None:
    """Log debug message."""
    logger.debug(msg)


def log_info(msg: str, print_console: bool = True, **kwargs) -> None:
    """Log info message."""
    logger.info(msg)


def log_warning(msg: str, print_console: bool = True, **kwargs) -> None:
    """Log warning message."""
    logger.warning(msg)


def log_error(msg: str, print_console: bool = True, **kwargs) -> None:
    """Log error message."""
    logger.error(msg)


def log_success(msg: str, print_console: bool = True, **kwargs) -> None:
    """Log success message (info level)."""
    logger.info(msg)
