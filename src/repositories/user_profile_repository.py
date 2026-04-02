"""User profile repository — data access for UserProfile model."""

from typing import Optional
from uuid import UUID

from models.user_profile import UserProfile
from repositories.base import BaseRepository


class UserProfileRepository(BaseRepository):
    """Data access for UserProfile entities."""

    def find_by_user(self, user_id: UUID) -> Optional[UserProfile]:
        return (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )

    def get_or_create(self, user_id: UUID) -> UserProfile:
        """Get existing profile or create an empty one."""
        profile = self.find_by_user(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            self.db.flush()
        return profile

    def create(self, profile: UserProfile) -> UserProfile:
        self.db.add(profile)
        self.db.flush()
        return profile

    def get_xp(self, user_id: UUID) -> int:
        """Get user XP, returning 0 if no profile exists."""
        profile = self.find_by_user(user_id)
        return profile.xp if profile else 0
