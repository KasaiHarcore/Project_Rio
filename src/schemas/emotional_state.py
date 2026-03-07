"""Pydantic Schemas for Emotional State and Relationship Events.

Schemas:
    - EmotionalStateResponse: Full emotional state returned to frontend
    - MoodTransition: A single mood change record
    - RelationshipEventResponse: A single relationship event
    - RelationshipHistoryResponse: List of relationship events
    - HeadpatRequest: Request body for recording a headpat
    - HeadpatResponse: Response with updated state + animation cue
"""

from datetime import datetime
from typing import Dict, List, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from models.emotional_state import Mood
from models.relationship_event import RelationshipEventType


class MoodTransition(BaseModel):
    """A single mood transition record from mood_history."""
    mood_from: str = Field(..., description="Previous mood")
    mood_to: str = Field(..., description="New mood")
    trigger: str = Field(..., description="What caused the transition")
    timestamp: datetime = Field(..., description="When the transition occurred")


class EmotionalStateResponse(BaseModel):
    """Full emotional state returned to the frontend."""
    model_config = ConfigDict(from_attributes=True)

    character_id: str = Field(..., description="Character identifier")
    mood: Mood = Field(..., description="Current mood")
    energy: float = Field(..., ge=0.0, le=1.0, description="Energy level")
    affinity: int = Field(..., ge=0, le=1000, description="Relationship score")
    relationship_tier: str = Field(..., description="Tier name: stranger/acquaintance/friend/close_friend/bonded")
    interaction_count: int = Field(..., description="Total interactions")
    streak_days: int = Field(..., description="Consecutive days of interaction")
    daily_greeting_done: bool = Field(..., description="Whether today's greeting was delivered")
    last_interaction_at: Optional[datetime] = Field(None, description="Last interaction timestamp")
    mood_history: List[MoodTransition] = Field(default_factory=list, description="Recent mood transitions")
    preferences_learned: Dict[str, str] = Field(default_factory=dict, description="Known user preferences")


class RelationshipEventResponse(BaseModel):
    """A single relationship event."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: RelationshipEventType
    affinity_delta: int
    mood_before: str
    mood_after: str
    context: Optional[str] = None
    created_at: datetime


class RelationshipHistoryResponse(BaseModel):
    """List of relationship events."""
    success: bool = True
    events: List[RelationshipEventResponse]
    total_affinity: int = Field(..., description="Current total affinity")


class HeadpatRequest(BaseModel):
    """Request body for recording a headpat interaction."""
    character_id: str = Field("rio", description="Which character was headpatted")


class HeadpatResponse(BaseModel):
    """Response after a headpat with updated emotional state."""
    success: bool = True
    mood: Mood = Field(..., description="Updated mood")
    affinity: int = Field(..., description="Updated affinity")
    affinity_delta: int = Field(..., description="How much affinity changed")
    mood_changed: bool = Field(..., description="Whether mood transitioned")
    animation_cue: str = Field(..., description="Spine animation to play (e.g., happy_reaction)")
    voice_line: Optional[str] = Field(None, description="Voice line ID to play")


class EmotionalUpdateEvent(BaseModel):
    """Streaming event emitted alongside chat responses."""
    type: Literal["emotional_update"] = "emotional_update"
    mood: str
    energy: float
    affinity: int
    relationship_tier: str
    mood_changed: bool
    animation_cue: Optional[str] = None
