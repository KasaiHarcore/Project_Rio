"""Memory-related schemas and enums."""

from __future__ import annotations

from enum import Enum


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SUMMARY = "summary"
