"""Centralised timezone helpers."""

from __future__ import annotations

import os
from datetime import datetime, timezone, tzinfo
from zoneinfo import ZoneInfo

__all__ = [
    "APP_TZ",
    "UTC",
    "utc_now",
    "local_now",
    "as_local",
]

# ── Constants ────────────────────────────────────────────────────────────────

UTC: tzinfo = timezone.utc

_tz_name: str = os.getenv("APP_TIMEZONE", "UTC").strip() or "UTC"
APP_TZ: tzinfo = ZoneInfo(_tz_name)

# ── Helpers ──────────────────────────────────────────────────────────────────


def utc_now() -> datetime:
    """
    Return the current **timezone-aware** UTC datetime.
    """
    return datetime.now(UTC)


def local_now() -> datetime:
    """
    Return the current datetime in the configured `APP_TIMEZONE`.
    """
    return datetime.now(APP_TZ)


def as_local(dt: datetime) -> datetime:
    """
    Convert any datetime to the configured `APP_TIMEZONE`.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(APP_TZ)
