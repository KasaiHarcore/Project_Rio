"""Settings repository — data access for UserSettings model."""

from typing import Optional
from uuid import UUID

from models.user_settings import UserSettings
from repositories.base import BaseRepository


class SettingsRepository(BaseRepository):
    """Data access for UserSettings entities."""

    def find_by_user(self, user_id: UUID) -> Optional[UserSettings]:
        return (
            self.db.query(UserSettings)
            .filter(UserSettings.user_id == user_id)
            .first()
        )

    def get_or_create(self, user_id: UUID) -> UserSettings:
        """Get existing settings or create defaults."""
        settings = self.find_by_user(user_id)
        if settings is None:
            settings = UserSettings(user_id=user_id)
            self.db.add(settings)
            self.db.flush()
        return settings

    def create(self, settings: UserSettings) -> UserSettings:
        self.db.add(settings)
        self.db.flush()
        return settings
