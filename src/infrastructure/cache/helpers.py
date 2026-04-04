"""Cache operation helpers for best-effort caching."""

from __future__ import annotations

from typing import Callable, Optional, TypeVar

from utils.log import log_warning

T = TypeVar("T")


def best_effort(fn: Callable[..., T], *args, **kwargs) -> Optional[T]:
    """Call fn and return its result. On any exception, log a warning and return None."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        log_warning(f"Cache operation failed: {e}")
        return None
