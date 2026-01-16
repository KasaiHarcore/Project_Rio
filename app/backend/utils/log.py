from __future__ import annotations

import time
from collections.abc import Callable
from os import get_terminal_size
from typing import Final

from loguru import logger
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Configuration
PRINT_STDOUT: bool = True
MAX_WIDTH: Final = 120

console = Console()


def terminal_width() -> int:
    return get_terminal_size().columns


WIDTH: Final = min(MAX_WIDTH, terminal_width() - 10)

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