"""Memory-Related Schemas and Enums.

Memory Types:
    - SHORT_TERM: Conversation context within a session
    - LONG_TERM: Persistent user preferences and facts
    - SUMMARY: Condensed conversation summaries
"""

from __future__ import annotations

from enum import Enum


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SUMMARY = "summary"
