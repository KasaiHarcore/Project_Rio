"""Experience-point service: award XP and compute level from total XP.

Level formula
-------------
Each level costs ``level x 100`` XP to reach the **next** level.

    Level 1 -> 2 :  100 XP
    Level 2 -> 3 :  200 XP
    Level 5 -> 6 :  500 XP
    Level 10->11 : 1000 XP

Cumulative XP for level *L*:  ``50 x L x (L - 1)``   (triangular sum)

XP sources
----------
+2   per user message sent
+5   first message in a new thread (thread creation)
+15  per document uploaded
+25  when a thread reaches 10+ messages (one-time bonus)
"""

from __future__ import annotations

import math
from typing import Optional

from infrastructure.cache.service import CacheService
from repositories.user_profile_repository import UserProfileRepository
from utils.log import log_info


class XPService:
    """Service for managing user XP, levels, and progress."""

    def __init__(self, profile_repo: UserProfileRepository, cache_service: Optional[CacheService] = None) -> None:
        self._repo = profile_repo
        self._cache = cache_service

    def _xp_for_level(self, level: int) -> int:
        """Cumulative XP required to *reach* ``level`` (from level 1).

        level 1  ->   0  (starting level)
        level 2  -> 100
        level 3  -> 300
        level 10 -> 4500
        """
        if level <= 1:
            return 0
        return 50 * level * (level - 1)

    def _level_from_xp(self, xp: int) -> int:
        """Derive the current level from total XP."""
        if xp <= 0:
            return 1
        # Solve  50 * L * (L-1) <= xp  ->  L^2 - L - xp/50 <= 0
        # L = (1 + sqrt(1 + 4*xp/50)) / 2
        level = int((1 + math.sqrt(1 + 4 * xp / 50)) / 2)
        # Clamp down in case of floating-point overshoot
        while self._xp_for_level(level + 1) <= xp:
            level += 1
        while self._xp_for_level(level) > xp:
            level -= 1
        return max(level, 1)

    def _level_progress(self, xp: int) -> dict:
        """Return current level, XP within that level, and XP needed for next."""
        level = self._level_from_xp(xp)
        current_floor = self._xp_for_level(level)
        next_floor = self._xp_for_level(level + 1)
        return {
            "level": level,
            "total_xp": xp,
            "xp_in_level": xp - current_floor,
            "xp_for_next": next_floor - current_floor,
        }

    # -- DB-backed operations --

    def award_xp(self, user_id, amount: int, reason: str = "") -> int:
        """Add *amount* XP to the user's profile. Returns new total XP."""
        profile = self._repo.get_or_create(user_id)
        old_xp = profile.xp or 0
        profile.xp = old_xp + amount
        self._repo.flush()

        new_level = self._level_from_xp(profile.xp)
        old_level = self._level_from_xp(old_xp)
        if new_level > old_level:
            log_info(f"[XP] user={user_id} leveled up! {old_level} -> {new_level} (+{amount} XP, reason={reason})")

        # Write-through: update Redis cache immediately
        if self._cache:
            try:
                self._cache.set_cached_xp(str(user_id), profile.xp)
            except Exception:
                pass

        return profile.xp

    def get_user_xp(self, user_id) -> int:
        """Return total XP for a user (0 if no profile).

        Uses Redis L2 cache (10 min TTL) to avoid repeated Postgres lookups.
        """
        uid_str = str(user_id)
        if self._cache:
            try:
                cached = self._cache.get_cached_xp(uid_str)
                if cached is not None:
                    return int(cached)
            except Exception:
                pass

        xp = self._repo.get_xp(user_id)

        # Backfill cache
        if self._cache:
            try:
                self._cache.set_cached_xp(uid_str, xp)
            except Exception:
                pass

        return xp

    def get_level_progress(self, user_id) -> dict:
        """Return level progress info for a user."""
        xp = self.get_user_xp(user_id)
        return self._level_progress(xp)


def award_xp(db, user_id, amount: int, reason: str = "") -> int:
    """Convenience wrapper: award XP using a raw db session."""
    from repositories.user_profile_repository import UserProfileRepository
    repo = UserProfileRepository(db)
    svc = XPService(repo)
    return svc.award_xp(user_id, amount, reason)


def get_user_xp(db, user_id) -> int:
    """Convenience wrapper: get user XP using a raw db session."""
    from repositories.user_profile_repository import UserProfileRepository
    repo = UserProfileRepository(db)
    svc = XPService(repo)
    return svc.get_user_xp(user_id)

def xp_for_level(level: int) -> int:
    """Cumulative XP required to *reach* ``level`` (from level 1)."""
    if level <= 1:
        return 0
    return 50 * level * (level - 1)


def level_from_xp(xp: int) -> int:
    """Derive the current level from total XP."""
    if xp <= 0:
        return 1
    level = int((1 + math.sqrt(1 + 4 * xp / 50)) / 2)
    while xp_for_level(level + 1) <= xp:
        level += 1
    while xp_for_level(level) > xp:
        level -= 1
    return max(level, 1)


def level_progress(xp: int) -> dict:
    """Return current level, XP within that level, and XP needed for next."""
    level = level_from_xp(xp)
    current_floor = xp_for_level(level)
    next_floor = xp_for_level(level + 1)
    return {
        "level": level,
        "total_xp": xp,
        "xp_in_level": xp - current_floor,
        "xp_for_next": next_floor - current_floor,
    }
