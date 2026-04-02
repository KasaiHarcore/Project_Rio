"""
Rio Response Generation API
Generates dynamic, context-aware responses using LLM
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from infrastructure.llm import form
from core.dependencies import get_current_user
from models.user import User
from utils.log import log_info, log_error
router = APIRouter(prefix="/emotional", tags=["emotional"])




class ResponseContext(BaseModel):
    """Context for generating Rio's response"""
    # Emotional state
    mood: str = Field(..., description="Current mood: happy, neutral, sad, excited, frustrated, tired")
    energy: float = Field(..., ge=0.0, le=1.0, description="Energy level 0-1")
    affinity: int = Field(..., ge=0, le=1000, description="Affinity score 0-1000")
    relationship_tier: str = Field(..., description="stranger, acquaintance, friend, close_friend, bonded")
    streak_days: int = Field(default=0, ge=0, description="Consecutive days of interaction")

    # Activity context
    session_duration: Optional[int] = Field(None, description="Session duration in milliseconds")
    idle_time: Optional[int] = Field(None, description="Idle time in milliseconds")
    is_late_night: Optional[bool] = Field(False, description="12am-5am")
    is_weekend: Optional[bool] = Field(False, description="Saturday or Sunday")
    event_count: Optional[int] = Field(None, description="User activity events this session")

    # Situation type
    situation_type: str = Field(
        ...,
        description="Type of situation: intervention_45min, intervention_90min, intervention_120min, "
                    "idle_check, late_night_warning, deadline_pressure, re_engagement, celebration, "
                    "observation, briefing, greeting"
    )

    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)


class GeneratedResponse(BaseModel):
    """Generated response from Rio"""
    message: str = Field(..., description="The generated message")
    tone: str = Field(..., description="Tone: gentle, caring, stern, playful, professional")
    suggested_actions: Optional[List[str]] = Field(None, description="Suggested action buttons")




PERSONA_DEFINITIONS = {
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




SITUATION_INSTRUCTIONS = {
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




MOOD_MODIFIERS = {
    "happy": "You are in a cheerful, upbeat mood. Use warm language and emoticons/emoji if appropriate for tier.",
    "excited": "You are energetic and enthusiastic. Show excitement through exclamation marks and vibrant language.",
    "neutral": "You are calm and balanced. Use measured, steady language.",
    "sad": "You are subdued and melancholic. Use gentler, quieter language. Show vulnerability if tier allows.",
    "frustrated": "You are irritated and impatient. Be more blunt and direct. For interventions, be stern.",
    "tired": "You are low-energy and weary. Use shorter sentences. Suggest mutual rest if appropriate.",
}




def generate_response_with_llm(context: ResponseContext) -> GeneratedResponse:
    """Generate response using LLM with rich context"""

    if form.SELECTED_MODEL is None:
        raise RuntimeError("No model selected. Call register_all_models() first.")

    model = form.SELECTED_MODEL

    if not hasattr(model, 'llm') or model.llm is None:
        model.setup()

    persona = PERSONA_DEFINITIONS.get(context.relationship_tier, PERSONA_DEFINITIONS["stranger"])
    situation = SITUATION_INSTRUCTIONS.get(context.situation_type, "Generate an appropriate response.")
    mood_modifier = MOOD_MODIFIERS.get(context.mood, MOOD_MODIFIERS["neutral"])

    activity_context = ""
    if context.session_duration:
        mins = context.session_duration // (60 * 1000)
        hours = mins // 60
        if hours > 0:
            activity_context += f"Session duration: {hours}h {mins % 60}m. "
        else:
            activity_context += f"Session duration: {mins}m. "

    if context.idle_time:
        idle_mins = context.idle_time // (60 * 1000)
        activity_context += f"Idle for: {idle_mins}m. "

    if context.is_late_night:
        activity_context += "Time: Late night (12am-5am). "

    if context.is_weekend:
        activity_context += "It's the weekend. "

    additional_context = ""
    if context.additional_info:
        for key, value in context.additional_info.items():
            additional_context += f"{key.replace('_', ' ').title()}: {value}. "

    # Determine tone based on situation and mood
    tone_map = {
        "intervention_45min": "gentle",
        "intervention_90min": "caring" if context.mood != "frustrated" else "stern",
        "intervention_120min": "stern",
        "idle_check": "gentle",
        "late_night_warning": "caring",
        "deadline_pressure": "caring",
        "re_engagement": "playful" if context.relationship_tier in ["friend", "close_friend", "bonded"] else "professional",
        "celebration": "playful",
        "observation": "professional",
        "briefing": "professional",
        "greeting": "playful" if context.mood == "happy" else "professional",
    }
    tone = tone_map.get(context.situation_type, "professional")

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

    # Generate suggested actions based on situation
    suggested_actions = None
    if context.situation_type == "intervention_45min":
        suggested_actions = ["Take a 5-minute break", "Keep working"]
    elif context.situation_type == "intervention_90min":
        suggested_actions = ["Take a break", "Remind me in 15 min", "Keep working"]
    elif context.situation_type == "intervention_120min":
        suggested_actions = ["Start mandatory break"]
    elif context.situation_type == "re_engagement":
        suggested_actions = ["What's new?", "Resume last chat", "View missions"]
    elif context.situation_type == "briefing":
        suggested_actions = ["Start new operation", "Check missions", "Upload document"]

    return GeneratedResponse(
        message=message,
        tone=tone,
        suggested_actions=suggested_actions,
    )




@router.post("/generate-response", response_model=GeneratedResponse)
async def generate_rio_response(
    context: ResponseContext,
    user: User = Depends(get_current_user),
) -> GeneratedResponse:
    """
    Generate a dynamic, context-aware response from Rio using LLM.

    This endpoint analyzes the emotional state, activity context, and situation type
    to generate personalized responses that match Rio's personality and relationship tier.
    """
    try:
        log_info(
            f"Generating Rio response for user {user.id}: "
            f"situation={context.situation_type}, tier={context.relationship_tier}, mood={context.mood}"
        )

        response = generate_response_with_llm(context)

        log_info(f"Generated response with tone={response.tone}, length={len(response.message)} chars")

        return response

    except Exception as e:
        log_error(f"Failed to generate Rio response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response",
        )
