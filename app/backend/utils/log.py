from __future__ import annotations

import os
import sys
import time
from os import get_terminal_size
from typing import Final

from loguru import logger
from rich.console import Console

# Configuration
PRINT_STDOUT: bool = True
MAX_WIDTH: Final = 120

console = Console()


def terminal_width() -> int:
    try:
        return get_terminal_size().columns
    except OSError:
        return MAX_WIDTH


WIDTH: Final = min(MAX_WIDTH, max(40, terminal_width() - 10))


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
    global PRINT_STDOUT
    PRINT_STDOUT = stdout and not json_logs

    logger.remove()

    sink_options = {
        "level": level,
        "backtrace": backtrace,
        "diagnose": diagnose,
        "enqueue": True,
        "colorize": not json_logs,
        "serialize": json_logs,
    }

    logger.add(sys.stdout, **sink_options)

    if log_file:
        logger.add(
            log_file,
            **sink_options,
            rotation=rotation,
            retention=retention,
        )


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


def _timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# Logging Utilities with proper log levels
def log_debug(msg: str, print_console: bool = False, **kwargs) -> None:
    """Log debug message. Optionally print to console."""
    logger.debug(msg)
    if print_console and PRINT_STDOUT:
        console.print(f"[dim][DEBUG][/dim] {msg}", **kwargs)


def log_info(msg: str, print_console: bool = True, **kwargs) -> None:
    """Log info message. By default prints to console."""
    logger.info(msg)
    if print_console and PRINT_STDOUT:
        console.print(f"[cyan][INFO][/cyan] {msg}", **kwargs)


def log_warning(msg: str, print_console: bool = True, **kwargs) -> None:
    """Log warning message. Always prints to console by default."""
    logger.warning(msg)
    if print_console and PRINT_STDOUT:
        console.print(f"[yellow][WARNING][/yellow] {msg}", **kwargs)


def log_error(msg: str, print_console: bool = True, **kwargs) -> None:
    """Log error message. Always prints to console by default."""
    logger.error(msg)
    if print_console and PRINT_STDOUT:
        console.print(f"[red][ERROR][/red] {msg}", **kwargs)


def log_success(msg: str, print_console: bool = True, **kwargs) -> None:
    """Log success message (info level). Prints to console by default."""
    logger.info(msg)
    if print_console and PRINT_STDOUT:
        console.print(f"[green][SUCCESS][/green] {msg}", **kwargs)