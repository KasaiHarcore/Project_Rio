"""Repository for AudioOverview data access."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models.audio_overview import AudioOverview
from repositories.base import BaseRepository


class AudioOverviewRepository(BaseRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_by_user(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[AudioOverview]:
        return (
            self.db.query(AudioOverview)
            .filter(AudioOverview.user_id == user_id)
            .order_by(AudioOverview.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_by_id(self, overview_id: UUID, user_id: UUID) -> Optional[AudioOverview]:
        return (
            self.db.query(AudioOverview)
            .filter(AudioOverview.id == overview_id, AudioOverview.user_id == user_id)
            .first()
        )

    def create(self, overview: AudioOverview) -> AudioOverview:
        return self.add(overview)

    def delete_by_id(self, overview_id: UUID, user_id: UUID) -> bool:
        overview = self.get_by_id(overview_id, user_id)
        if overview:
            self.delete(overview)
            return True
        return False
