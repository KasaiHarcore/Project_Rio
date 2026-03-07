"""Emotional state repository — data access for EmotionalState and RelationshipEvent models."""

from typing import Optional, List
from uuid import UUID

from models.emotional_state import EmotionalState, Mood
from models.relationship_event import RelationshipEvent
from repositories.base import BaseRepository


class EmotionalStateRepository(BaseRepository):
    """Data access for EmotionalState and RelationshipEvent entities."""

    def find_by_user_and_character(
        self, user_id: UUID, character_id: str
    ) -> Optional[EmotionalState]:
        return (
            self.db.query(EmotionalState)
            .filter(
                EmotionalState.user_id == user_id,
                EmotionalState.character_id == character_id,
            )
            .first()
        )

    def get_or_create(
        self, user_id: UUID, character_id: str
    ) -> EmotionalState:
        """Get existing state or create a new default one."""
        state = self.find_by_user_and_character(user_id, character_id)
        if state is None:
            state = EmotionalState(
                user_id=user_id,
                character_id=character_id,
                mood=Mood.NEUTRAL,
                energy=1.0,
                affinity=0,
                interaction_count=0,
                streak_days=0,
                mood_history=[],
                preferences_learned={},
            )
            self.db.add(state)
            self.db.flush()
        return state

    def create_relationship_event(self, event: RelationshipEvent) -> RelationshipEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def list_relationship_events(
        self, user_id: UUID, character_id: str, limit: int = 50
    ) -> List[RelationshipEvent]:
        return (
            self.db.query(RelationshipEvent)
            .filter(
                RelationshipEvent.user_id == user_id,
                RelationshipEvent.character_id == character_id,
            )
            .order_by(RelationshipEvent.created_at.desc())
            .limit(limit)
            .all()
        )
