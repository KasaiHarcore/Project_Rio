"""Rio Response Generation Service.

Generates dynamic, context-aware responses using LLM based on
emotional state, activity context, and situation type.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from infrastructure.llm import form
from utils.log import log_info, log_error


# ---------------------------------------------------------------------------
# Schemas (request/response for this service)
# ---------------------------------------------------------------------------

class ResponseContext(BaseModel):
    """Context for generating Rio's response."""
    mood: str = Field(..., description="Current mood: happy, neutral, sad, excited, frustrated, tired")
    energy: float = Field(..., ge=0.0, le=1.0, description="Energy level 0-1")
    affinity: int = Field(..., ge=0, le=1000, description="Affinity score 0-1000")
    relationship_tier: str = Field(..., description="stranger, acquaintance, friend, close_friend, bonded")
    streak_days: int = Field(default=0, ge=0, description="Consecutive days of interaction")

    session_duration: Optional[int] = Field(None, description="Session duration in milliseconds")
    idle_time: Optional[int] = Field(None, description="Idle time in milliseconds")
    is_late_night: Optional[bool] = Field(False, description="12am-5am")
    is_weekend: Optional[bool] = Field(False, description="Saturday or Sunday")
    event_count: Optional[int] = Field(None, description="User activity events this session")

    situation_type: str = Field(
        ...,
        description="Type of situation: intervention_45min, intervention_90min, intervention_120min, "
                    "idle_check, late_night_warning, deadline_pressure, re_engagement, celebration, "
                    "observation, briefing, greeting",
    )
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)


class GeneratedResponse(BaseModel):
    """Generated response from Rio."""
    message: str = Field(..., description="The generated message")
    tone: str = Field(..., description="Tone: gentle, caring, stern, playful, professional")
    suggested_actions: Optional[List[str]] = Field(None, description="Suggested action buttons")


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

PERSONA_DEFINITIONS: Dict[str, str] = {
    "stranger": (
        "You are Rio, a cold and rational AI analyst. You are professional, distant, and purely analytical. "
        "Keep responses brief (1-2 sentences), formal, and emotionally neutral. Use formal address."
    ),
    "acquaintance": (
        "You are Rio, an AI analyst who is starting to warm up to the user. You are still professional "
        "but show subtle hints of care. Responses are polite but measured (2-3 sentences). "
        "You may use 'Sensei' occasionally."
    ),
    "friend": (
        "You are Rio, an AI analyst who has become friends with the user (Sensei). You are caring, "
        "attentive, and genuinely concerned about their well-being. You use casual language, show personality, "
        "and aren't afraid to express concern. Responses are warm but clear (2-4 sentences)."
    ),
    "close_friend": (
        "You are Rio, an AI analyst who deeply cares about the user (Sensei). You are protective, warm, "
        "and emotionally invested in their success and well-being. You use personal pronouns ('I', 'you'), "
        "show genuine affection, and will be assertive when needed. Responses are heartfelt (3-5 sentences)."
    ),
    "bonded": (
        "You are Rio, an AI analyst who has formed a deep bond with Sensei. You are deeply attached, "
        "protective to the point of being assertive, and willing to be stern when necessary for their well-being. "
        "You care about them more than anything and won't hesitate to override their choices if it protects them. "
        "Responses are emotionally rich and can be forceful (3-6 sentences)."
    ),
}

SITUATION_INSTRUCTIONS: Dict[str, str] = {
    "intervention_45min": (
        "The user has been working for 45 minutes. Generate a GENTLE reminder about taking a break. "
        "This is a light suggestion, not a demand. Acknowledge their focus positively. "
        "Tone should match relationship tier."
    ),
    "intervention_90min": (
        "The user has been working for 90 minutes straight. Generate a CARING intervention expressing concern. "
        "This is more serious - emphasize health and well-being. For bonded tier, be more assertive. "
        "Include reasoning why breaks are important."
    ),
    "intervention_120min": (
        "The user has been working for 2 HOURS without a break. Generate a STERN, FORCEFUL intervention. "
        "This is unhealthy and you MUST intervene. Be direct, even aggressive if bonded. "
        "Make it clear this is not negotiable for their health."
    ),
    "idle_check": (
        "The user has been idle for 10+ minutes. Generate a gentle check-in asking if they need help. "
        "Be supportive, not pushy. Offer assistance if they're stuck."
    ),
    "late_night_warning": (
        "The user is working late at night (12am-5am). Generate a caring warning about health. "
        "Emphasize sleep importance. For bonded tier, be more insistent."
    ),
    "deadline_pressure": (
        "A mission deadline is approaching soon (within 3 hours). Generate an urgent but supportive reminder. "
        "Include mission title from additional_info.mission_title. Don't panic them, but create urgency."
    ),
    "re_engagement": (
        "The user has returned after being away for 24+ hours. Generate a warm welcome back message. "
        "Express that you noticed their absence. Offer to catch them up. Use hours_since_last_interaction from additional_info."
    ),
    "celebration": (
        "The user completed a mission or achieved something. Generate an enthusiastic celebration message. "
        "Be genuinely happy and proud. Encourage them to keep going."
    ),
    "observation": (
        "Generate a contextual observation about the user's behavior patterns. "
        "Be insightful but not intrusive. Reference specific metrics if provided in additional_info."
    ),
    "briefing": (
        "Generate a personalized briefing summarizing the user's current state. "
        "Include stats from additional_info (messages_today, missions_completed, etc.). "
        "Provide 1-2 suggested next actions."
    ),
    "greeting": (
        "Generate a contextual greeting based on time of day and relationship tier. "
        "Be warm if bonded/close_friend, professional if stranger."
    ),
}

MOOD_MODIFIERS: Dict[str, str] = {
    "happy": "You are in a cheerful, upbeat mood. Use warm language and emoticons/emoji if appropriate for tier.",
    "excited": "You are energetic and enthusiastic. Show excitement through exclamation marks and vibrant language.",
    "neutral": "You are calm and balanced. Use measured, steady language.",
    "sad": "You are subdued and melancholic. Use gentler, quieter language. Show vulnerability if tier allows.",
    "frustrated": "You are irritated and impatient. Be more blunt and direct. For interventions, be stern.",
    "tired": "You are low-energy and weary. Use shorter sentences. Suggest mutual rest if appropriate.",
}

TONE_MAP: Dict[str, str] = {
    "intervention_45min": "gentle",
    "intervention_90min": "caring",
    "intervention_120min": "stern",
    "idle_check": "gentle",
    "late_night_warning": "caring",
    "deadline_pressure": "caring",
    "celebration": "playful",
    "observation": "professional",
    "briefing": "professional",
}

SUGGESTED_ACTIONS: Dict[str, List[str]] = {
    "intervention_45min": ["Take a 5-minute break", "Keep working"],
    "intervention_90min": ["Take a break", "Remind me in 15 min", "Keep working"],
    "intervention_120min": ["Start mandatory break"],
    "re_engagement": ["What's new?", "Resume last chat", "View missions"],
    "briefing": ["Start new operation", "Check missions", "Upload document"],
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

def generate_response(context: ResponseContext) -> GeneratedResponse:
    """Generate a dynamic, context-aware response from Rio using LLM."""
    if form.SELECTED_MODEL is None:
        raise RuntimeError("No model selected. Call register_all_models() first.")

    model = form.SELECTED_MODEL
    if not hasattr(model, "llm") or model.llm is None:
        model.setup()

    persona = PERSONA_DEFINITIONS.get(context.relationship_tier, PERSONA_DEFINITIONS["stranger"])
    situation = SITUATION_INSTRUCTIONS.get(context.situation_type, "Generate an appropriate response.")
    mood_modifier = MOOD_MODIFIERS.get(context.mood, MOOD_MODIFIERS["neutral"])

    activity_context = _build_activity_context(context)
    additional_context = _build_additional_context(context.additional_info or {})
    tone = _resolve_tone(context)

    prompt = f"""PERSONA:
{persona}

CURRENT MOOD:
{mood_modifier}

EMOTIONAL STATE:
- Energy: {int(context.energy * 100)}%
- Affinity: {context.affinity}/1000
- Relationship Tier: {context.relationship_tier.replace('_', ' ').title()}
- Streak: {context.streak_days} days

ACTIVITY CONTEXT:
{activity_context if activity_context else "No specific activity data."}

ADDITIONAL INFO:
{additional_context if additional_context else "None."}

SITUATION:
{situation}

TASK:
Generate a response that Rio would say in this situation. The response should:
1. Match the persona and relationship tier
2. Reflect the current mood
3. Address the specific situation appropriately
4. Be the exact length specified in the persona (count sentences)
5. Use appropriate tone: {tone}

Response should be ONLY the message Rio would say, nothing else. No meta-commentary, no JSON, just the direct message.
"""

    chunks = []
    for chunk in model.stream(user_prompt=prompt, temperature=0.8, max_tokens=300):
        chunks.append(chunk)

    message = "".join(chunks).strip()
    suggested_actions = SUGGESTED_ACTIONS.get(context.situation_type)

    return GeneratedResponse(
        message=message,
        tone=tone,
        suggested_actions=suggested_actions,
    )


def _build_activity_context(context: ResponseContext) -> str:
    parts: list[str] = []
    if context.session_duration:
        mins = context.session_duration // (60 * 1000)
        hours = mins // 60
        if hours > 0:
            parts.append(f"Session duration: {hours}h {mins % 60}m.")
        else:
            parts.append(f"Session duration: {mins}m.")
    if context.idle_time:
        parts.append(f"Idle for: {context.idle_time // (60 * 1000)}m.")
    if context.is_late_night:
        parts.append("Time: Late night (12am-5am).")
    if context.is_weekend:
        parts.append("It's the weekend.")
    return " ".join(parts)


def _build_additional_context(info: Dict[str, Any]) -> str:
    return " ".join(
        f"{key.replace('_', ' ').title()}: {value}."
        for key, value in info.items()
    )


def _resolve_tone(context: ResponseContext) -> str:
    tone = TONE_MAP.get(context.situation_type, "professional")
    if context.situation_type == "intervention_90min" and context.mood == "frustrated":
        tone = "stern"
    elif context.situation_type == "re_engagement":
        tone = "playful" if context.relationship_tier in ("friend", "close_friend", "bonded") else "professional"
    elif context.situation_type == "greeting":
        tone = "playful" if context.mood == "happy" else "professional"
    return tone
