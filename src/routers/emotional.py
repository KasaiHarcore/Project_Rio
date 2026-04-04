"""Emotional state endpoints: mood, affinity, headpat, relationship history,
and Rio response generation.

These endpoints expose the Living AI emotional engine to the frontend,
enabling real-time mood display, headpat interactions, relationship
history viewing, and dynamic response generation.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_emotional_engine
from services.emotional_engine import EmotionalEngine
from services.rio_response_service import (
    GeneratedResponse,
    ResponseContext,
    generate_response,
)
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
from utils.log import log_info, log_error

router = APIRouter(prefix="/emotional", tags=["emotional"])

VALID_CHARACTERS = {"rio"}


@router.get("/state", response_model=EmotionalStateResponse)
async def get_emotional_state(
    character_id: str = Query("rio", description="Character ID"),
    user: User = Depends(get_current_user),
    engine: EmotionalEngine = Depends(get_emotional_engine),
):
    """Get the current emotional state for a user-character pair."""
    if character_id not in VALID_CHARACTERS:
        raise ValidationError(f"Unknown character: {character_id}")

    def _query():
        state = engine.get_or_create_state(user.id, character_id)
        tier = engine.get_relationship_tier(state.affinity)

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

    return await concurrency_manager.run_in_thread(_query)


@router.post("/headpat", response_model=HeadpatResponse)
async def record_headpat(
    body: HeadpatRequest,
    user: User = Depends(get_current_user),
    engine: EmotionalEngine = Depends(get_emotional_engine),
):
    """Record a headpat interaction — boosts mood and affinity."""
    if body.character_id not in VALID_CHARACTERS:
        raise ValidationError(f"Unknown character: {body.character_id}")

    def _query():
        state, affinity_delta, mood_changed = engine.record_headpat(
            user.id, body.character_id,
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

    return await concurrency_manager.run_in_thread(_query)


@router.get("/history", response_model=RelationshipHistoryResponse)
async def get_relationship_history(
    character_id: str = Query("rio", description="Character ID"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    engine: EmotionalEngine = Depends(get_emotional_engine),
):
    """Get recent relationship events for a user-character pair."""
    if character_id not in VALID_CHARACTERS:
        raise ValidationError(f"Unknown character: {character_id}")

    def _query():
        events = engine.get_relationship_history(
            user.id, character_id, limit=limit,
        )

        state = engine.get_or_create_state(user.id, character_id)

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

    return await concurrency_manager.run_in_thread(_query)


@router.post("/generate-response", response_model=GeneratedResponse)
async def generate_rio_response(
    context: ResponseContext,
    user: User = Depends(get_current_user),
) -> GeneratedResponse:
    """Generate a dynamic, context-aware response from Rio using LLM.

    Analyzes emotional state, activity context, and situation type
    to generate personalized responses matching Rio's personality.
    """
    try:
        log_info(
            f"Generating Rio response for user {user.id}: "
            f"situation={context.situation_type}, tier={context.relationship_tier}, mood={context.mood}"
        )
        response = generate_response(context)
        log_info(f"Generated response with tone={response.tone}, length={len(response.message)} chars")
        return response
    except Exception as e:
        log_error(f"Failed to generate Rio response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response",
        )
