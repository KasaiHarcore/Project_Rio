"""Emotional state endpoints: mood, affinity, headpat, relationship history.

These endpoints expose the Living AI emotional engine to the frontend,
enabling real-time mood display, headpat interactions, and relationship
history viewing.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_db
from services.emotional_engine import EmotionalEngine
from core.exceptions import ValidationError
from models.user import User
from schemas.emotional_state import (
    EmotionalStateResponse,
    HeadpatRequest,
    HeadpatResponse,
    MoodTransition,
    RelationshipEventResponse,
    RelationshipHistoryResponse,
)

router = APIRouter(prefix="/emotional", tags=["emotional"])

VALID_CHARACTERS = {"rio"}


@router.get("/state", response_model=EmotionalStateResponse)
def get_emotional_state(
    character_id: str = Query("rio", description="Character ID"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current emotional state for a user-character pair."""
    if character_id not in VALID_CHARACTERS:
        raise ValidationError(f"Unknown character: {character_id}")

    state = EmotionalEngine.get_or_create_state(db, user.id, character_id)
    tier = EmotionalEngine.get_relationship_tier(state.affinity)

    # Parse mood_history into structured objects
    mood_history: List[MoodTransition] = []
    for entry in (state.mood_history or [])[-20:]:
        try:
            mood_history.append(MoodTransition(**entry))
        except Exception:
            pass

    return EmotionalStateResponse(
        character_id=character_id,
        mood=state.mood,
        energy=state.energy,
        affinity=state.affinity,
        relationship_tier=tier,
        interaction_count=state.interaction_count,
        streak_days=state.streak_days,
        daily_greeting_done=state.daily_greeting_done or False,
        last_interaction_at=state.last_interaction_at,
        mood_history=mood_history,
        preferences_learned=state.preferences_learned or {},
    )


@router.post("/headpat", response_model=HeadpatResponse)
def record_headpat(
    body: HeadpatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a headpat interaction — boosts mood and affinity."""
    if body.character_id not in VALID_CHARACTERS:
        raise ValidationError(f"Unknown character: {body.character_id}")

    state, affinity_delta, mood_changed = EmotionalEngine.record_headpat(
        db, user.id, body.character_id,
    )

    # Choose animation cue based on mood
    animation_map = {
        "happy": "Pat_01_M",
        "excited": "Pat_01_A",
        "neutral": "Pat_01_M",
        "sad": "Pat_01_M",
        "frustrated": "Pat_01_M",
        "tired": "Pat_01_M",
    }
    animation_cue = animation_map.get(state.mood.value, "Pat_01_M")

    return HeadpatResponse(
        mood=state.mood,
        affinity=state.affinity,
        affinity_delta=affinity_delta,
        mood_changed=mood_changed,
        animation_cue=animation_cue,
        voice_line=None,
    )


@router.get("/history", response_model=RelationshipHistoryResponse)
def get_relationship_history(
    character_id: str = Query("rio", description="Character ID"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get recent relationship events for a user-character pair."""
    if character_id not in VALID_CHARACTERS:
        raise ValidationError(f"Unknown character: {character_id}")

    events = EmotionalEngine.get_relationship_history(
        db, user.id, character_id, limit=limit,
    )

    state = EmotionalEngine.get_or_create_state(db, user.id, character_id)

    return RelationshipHistoryResponse(
        events=[
            RelationshipEventResponse(
                id=e.id,
                event_type=e.event_type,
                affinity_delta=e.affinity_delta,
                mood_before=e.mood_before,
                mood_after=e.mood_after,
                context=e.context,
                created_at=e.created_at,
            )
            for e in events
        ],
        total_affinity=state.affinity,
    )
