"""Emotional Engine -- Tracks character mood, energy, affinity, and relationship.

The emotional engine is the core of the "Living AI" system. It maintains
a state machine for each character-user pair, updating mood and affinity
based on interaction patterns, sentiment, time of day, and special events.

Relationship Tiers (by affinity score):
    0-100:   stranger     -- formal, reserved
    100-300: acquaintance -- friendly, professional
    300-600: friend       -- casual, warm
    600-800: close_friend -- intimate, playful
    800-1000: bonded      -- deeply personal, protective

Mood State Machine:
    happy + positive -> happy (+3 affinity)
    neutral + positive -> happy (+2)
    neutral + negative -> sad (-2)
    sad + positive -> neutral (+3, recovery bonus)
    any + long_absence -> sad (-5)
    any + headpat -> happy (+5)
    energy < 0.2 -> mood shifts toward tired
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from models.emotional_state import EmotionalState, Mood
from models.relationship_event import RelationshipEvent, RelationshipEventType
from repositories.emotional_state_repository import EmotionalStateRepository
from utils.log import log_info, log_debug



MAX_MOOD_HISTORY = 20
MAX_AFFINITY = 1000
MIN_AFFINITY = 0
LONG_ABSENCE_HOURS = 48
ENERGY_DECAY_RATE = 0.02       # per hour without interaction
ENERGY_RECOVERY_RATE = 0.15    # per interaction

RELATIONSHIP_TIERS = {
    "stranger":     (0, 100),
    "acquaintance": (100, 300),
    "friend":       (300, 600),
    "close_friend": (600, 800),
    "bonded":       (800, 1000),
}

MOOD_TRANSITIONS: Dict[Tuple[str, str], Tuple[Mood, int]] = {
    ("happy", "positive"):      (Mood.HAPPY, 3),
    ("neutral", "positive"):    (Mood.HAPPY, 2),
    ("sad", "positive"):        (Mood.NEUTRAL, 3),  # recovery bonus
    ("excited", "positive"):    (Mood.EXCITED, 2),
    ("frustrated", "positive"): (Mood.NEUTRAL, 4),   # relief bonus
    ("tired", "positive"):      (Mood.NEUTRAL, 2),

    ("happy", "negative"):      (Mood.NEUTRAL, -1),
    ("neutral", "negative"):    (Mood.SAD, -2),
    ("sad", "negative"):        (Mood.SAD, -3),
    ("excited", "negative"):    (Mood.NEUTRAL, -2),
    ("frustrated", "negative"): (Mood.FRUSTRATED, -3),
    ("tired", "negative"):      (Mood.SAD, -2),

    ("happy", "neutral"):       (Mood.HAPPY, 1),
    ("neutral", "neutral"):     (Mood.NEUTRAL, 1),
    ("sad", "neutral"):         (Mood.SAD, 0),
    ("excited", "neutral"):     (Mood.NEUTRAL, 1),
    ("frustrated", "neutral"):  (Mood.NEUTRAL, 1),
    ("tired", "neutral"):       (Mood.TIRED, 0),

    ("happy", "grateful"):      (Mood.EXCITED, 5),
    ("neutral", "grateful"):    (Mood.HAPPY, 4),
    ("sad", "grateful"):        (Mood.HAPPY, 5),
    ("frustrated", "grateful"): (Mood.HAPPY, 5),
    ("tired", "grateful"):      (Mood.HAPPY, 3),
    ("excited", "grateful"):    (Mood.EXCITED, 4),
}

# Time-of-day mood modifiers
TIME_MOOD_MODIFIERS = {
    "early_morning": (0, 6),    # 12am-6am: tired
    "morning":       (6, 12),   # 6am-12pm: energetic
    "afternoon":     (12, 17),  # 12pm-5pm: neutral
    "evening":       (17, 21),  # 5pm-9pm: relaxed
    "night":         (21, 24),  # 9pm-12am: winding down
}


class EmotionalEngine:
    """Manages character emotional state for a user-character pair."""

    def __init__(self, emotional_repo: EmotionalStateRepository) -> None:
        self._repo = emotional_repo


    def get_or_create_state(
        self,
        user_id: uuid.UUID,
        character_id: str,
    ) -> EmotionalState:
        """Load or initialize emotional state from DB."""
        state = self._repo.get_or_create(user_id, character_id)
        return state


    def update_mood(
        self,
        user_id: uuid.UUID,
        character_id: str,
        sentiment: str,
        context: str = "",
    ) -> Tuple[EmotionalState, bool]:
        """Apply mood state machine transition based on sentiment.

        Returns:
            (updated_state, mood_changed)
        """
        state = self.get_or_create_state(user_id, character_id)
        old_mood = state.mood

        # Look up transition
        key = (old_mood.value, sentiment)
        if key in MOOD_TRANSITIONS:
            new_mood, affinity_delta = MOOD_TRANSITIONS[key]
        else:
            new_mood = old_mood
            affinity_delta = 0

        # Apply energy-based override
        if state.energy < 0.2 and new_mood != Mood.TIRED:
            new_mood = Mood.TIRED

        mood_changed = new_mood != old_mood
        state.mood = new_mood

        state.affinity = max(MIN_AFFINITY, min(MAX_AFFINITY, state.affinity + affinity_delta))

        # Log mood transition
        if mood_changed:
            transition = {
                "mood_from": old_mood.value,
                "mood_to": new_mood.value,
                "trigger": sentiment,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            history = list(state.mood_history or [])
            history.append(transition)
            state.mood_history = history[-MAX_MOOD_HISTORY:]

        # Log relationship event
        if affinity_delta != 0:
            event_type = (
                RelationshipEventType.POSITIVE_INTERACTION
                if affinity_delta > 0
                else RelationshipEventType.NEGATIVE_INTERACTION
            )
            event = RelationshipEvent(
                user_id=user_id,
                character_id=character_id,
                event_type=event_type,
                affinity_delta=affinity_delta,
                mood_before=old_mood.value,
                mood_after=new_mood.value,
                context=context[:500] if context else None,
            )
            self._repo.create_relationship_event(event)

        self._repo.flush()
        return state, mood_changed


    def update_affinity(
        self,
        user_id: uuid.UUID,
        character_id: str,
        delta: int,
        event_type: RelationshipEventType,
        context: str = "",
    ) -> EmotionalState:
        """Directly adjust affinity and log the event."""
        state = self.get_or_create_state(user_id, character_id)
        old_mood = state.mood.value

        state.affinity = max(MIN_AFFINITY, min(MAX_AFFINITY, state.affinity + delta))

        event = RelationshipEvent(
            user_id=user_id,
            character_id=character_id,
            event_type=event_type,
            affinity_delta=delta,
            mood_before=old_mood,
            mood_after=state.mood.value,
            context=context[:500] if context else None,
        )
        self._repo.create_relationship_event(event)
        self._repo.flush()
        return state


    def decay_energy(
        self,
        user_id: uuid.UUID,
        character_id: str,
    ) -> EmotionalState:
        """Reduce energy based on time since last interaction."""
        state = self.get_or_create_state(user_id, character_id)

        if state.last_interaction_at:
            hours_since = (
                datetime.now(timezone.utc) - state.last_interaction_at
            ).total_seconds() / 3600
            decay = min(hours_since * ENERGY_DECAY_RATE, 1.0)
            state.energy = max(0.0, state.energy - decay)
        self._repo.flush()
        return state

    def restore_energy(
        self,
        user_id: uuid.UUID,
        character_id: str,
    ) -> EmotionalState:
        """Restore some energy on interaction."""
        state = self.get_or_create_state(user_id, character_id)
        state.energy = min(1.0, state.energy + ENERGY_RECOVERY_RATE)
        self._repo.flush()
        return state


    def get_relationship_tier(self, affinity: int) -> str:
        """Map affinity score to a named tier."""
        for tier_name, (low, high) in RELATIONSHIP_TIERS.items():
            if low <= affinity < high:
                return tier_name
        return "bonded" if affinity >= 800 else "stranger"


    def get_time_of_day(self) -> str:
        """Get current time-of-day period."""
        hour = datetime.now().hour
        if hour < 6:
            return "early_morning"
        elif hour < 12:
            return "morning"
        elif hour < 17:
            return "afternoon"
        elif hour < 21:
            return "evening"
        else:
            return "night"

    def get_time_energy_modifier(self) -> float:
        """Energy modifier based on time of day (simulates character's day cycle)."""
        time_period = self.get_time_of_day()
        modifiers = {
            "early_morning": -0.2,
            "morning": 0.1,
            "afternoon": 0.0,
            "evening": -0.05,
            "night": -0.15,
        }
        return modifiers.get(time_period, 0.0)


    def record_headpat(
        self,
        user_id: uuid.UUID,
        character_id: str,
    ) -> Tuple[EmotionalState, int, bool]:
        """Record a headpat interaction.

        Returns:
            (updated_state, affinity_delta, mood_changed)
        """
        state = self.get_or_create_state(user_id, character_id)
        old_mood = state.mood

        affinity_delta = 5
        state.mood = Mood.HAPPY
        state.affinity = min(MAX_AFFINITY, state.affinity + affinity_delta)
        state.energy = min(1.0, state.energy + 0.05)

        mood_changed = old_mood != Mood.HAPPY

        if mood_changed:
            transition = {
                "mood_from": old_mood.value,
                "mood_to": Mood.HAPPY.value,
                "trigger": "headpat",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            history = list(state.mood_history or [])
            history.append(transition)
            state.mood_history = history[-MAX_MOOD_HISTORY:]

        event = RelationshipEvent(
            user_id=user_id,
            character_id=character_id,
            event_type=RelationshipEventType.HEADPAT,
            affinity_delta=affinity_delta,
            mood_before=old_mood.value,
            mood_after=Mood.HAPPY.value,
            context="User gave a headpat",
        )
        self._repo.create_relationship_event(event)
        self._repo.flush()

        return state, affinity_delta, mood_changed


    def check_absence(
        self,
        user_id: uuid.UUID,
        character_id: str,
    ) -> Tuple[EmotionalState, bool]:
        """Check for long absence and apply mood/affinity penalty.

        Returns:
            (state, was_absent)
        """
        state = self.get_or_create_state(user_id, character_id)

        if not state.last_interaction_at:
            return state, False

        hours_since = (
            datetime.now(timezone.utc) - state.last_interaction_at
        ).total_seconds() / 3600

        if hours_since >= LONG_ABSENCE_HOURS:
            old_mood = state.mood
            state.mood = Mood.SAD
            state.affinity = max(MIN_AFFINITY, state.affinity - 5)
            state.streak_days = 0

            event = RelationshipEvent(
                user_id=user_id,
                character_id=character_id,
                event_type=RelationshipEventType.LONG_ABSENCE,
                affinity_delta=-5,
                mood_before=old_mood.value,
                mood_after=Mood.SAD.value,
                context=f"No interaction for {int(hours_since)} hours",
            )
            self._repo.create_relationship_event(event)
            self._repo.flush()
            return state, True

        return state, False


    def update_streak(
        self,
        user_id: uuid.UUID,
        character_id: str,
    ) -> EmotionalState:
        """Update interaction streak (called once per day on first interaction)."""
        state = self.get_or_create_state(user_id, character_id)

        now = datetime.now(timezone.utc)
        if state.last_interaction_at:
            days_since = (now - state.last_interaction_at).days
            if days_since == 1:
                state.streak_days += 1
                # Streak milestone bonus
                if state.streak_days % 7 == 0:
                    milestone_bonus = min(10, state.streak_days // 7 * 2)
                    state.affinity = min(MAX_AFFINITY, state.affinity + milestone_bonus)
                    event = RelationshipEvent(
                        user_id=user_id,
                        character_id=character_id,
                        event_type=RelationshipEventType.STREAK_MILESTONE,
                        affinity_delta=milestone_bonus,
                        mood_before=state.mood.value,
                        mood_after=state.mood.value,
                        context=f"Streak milestone: {state.streak_days} days!",
                    )
                    self._repo.create_relationship_event(event)
            elif days_since > 1:
                state.streak_days = 1  # reset, start new streak
            # days_since == 0: same day, no change
        else:
            state.streak_days = 1  # first ever interaction

        self._repo.flush()
        return state


    def record_interaction(
        self,
        user_id: uuid.UUID,
        character_id: str,
        sentiment: str = "neutral",
        task_success: Optional[bool] = None,
        context: str = "",
    ) -> Tuple[EmotionalState, bool]:
        """Main entry point called after each conversation turn.

        Handles: absence check, streak update, mood transition, energy
        restoration, interaction counting.

        Optimized: fetches state once and passes it through all sub-operations
        to avoid repeated DB lookups.

        Returns:
            (updated_state, mood_changed)
        """
        state = self.get_or_create_state(user_id, character_id)

        # --- absence check (inline) ---
        if state.last_interaction_at:
            hours_since = (
                datetime.now(timezone.utc) - state.last_interaction_at
            ).total_seconds() / 3600
            if hours_since >= LONG_ABSENCE_HOURS:
                old_mood = state.mood
                state.mood = Mood.SAD
                state.affinity = max(MIN_AFFINITY, state.affinity - 5)
                state.streak_days = 0
                self._repo.create_relationship_event(RelationshipEvent(
                    user_id=user_id, character_id=character_id,
                    event_type=RelationshipEventType.LONG_ABSENCE,
                    affinity_delta=-5,
                    mood_before=old_mood.value, mood_after=Mood.SAD.value,
                    context=f"No interaction for {int(hours_since)} hours",
                ))

        # --- streak update (inline) ---
        now = datetime.now(timezone.utc)
        if state.last_interaction_at:
            days_since = (now - state.last_interaction_at).days
            if days_since == 1:
                state.streak_days += 1
                if state.streak_days % 7 == 0:
                    milestone_bonus = min(10, state.streak_days // 7 * 2)
                    state.affinity = min(MAX_AFFINITY, state.affinity + milestone_bonus)
                    self._repo.create_relationship_event(RelationshipEvent(
                        user_id=user_id, character_id=character_id,
                        event_type=RelationshipEventType.STREAK_MILESTONE,
                        affinity_delta=milestone_bonus,
                        mood_before=state.mood.value, mood_after=state.mood.value,
                        context=f"Streak milestone: {state.streak_days} days!",
                    ))
            elif days_since > 1:
                state.streak_days = 1
        else:
            state.streak_days = 1

        # --- energy restore (inline) ---
        state.energy = min(1.0, state.energy + ENERGY_RECOVERY_RATE)

        # --- mood transition ---
        if task_success is True:
            sentiment = "grateful" if sentiment == "positive" else "positive"
        elif task_success is False:
            sentiment = "negative" if sentiment == "neutral" else sentiment

        old_mood = state.mood
        key = (old_mood.value, sentiment)
        if key in MOOD_TRANSITIONS:
            new_mood, affinity_delta = MOOD_TRANSITIONS[key]
        else:
            new_mood, affinity_delta = old_mood, 0

        if state.energy < 0.2 and new_mood != Mood.TIRED:
            new_mood = Mood.TIRED

        mood_changed = new_mood != old_mood
        state.mood = new_mood
        state.affinity = max(MIN_AFFINITY, min(MAX_AFFINITY, state.affinity + affinity_delta))

        if mood_changed:
            history = list(state.mood_history or [])
            history.append({
                "mood_from": old_mood.value, "mood_to": new_mood.value,
                "trigger": sentiment, "timestamp": now.isoformat(),
            })
            state.mood_history = history[-MAX_MOOD_HISTORY:]

        if affinity_delta != 0:
            evt_type = (
                RelationshipEventType.POSITIVE_INTERACTION
                if affinity_delta > 0
                else RelationshipEventType.NEGATIVE_INTERACTION
            )
            self._repo.create_relationship_event(RelationshipEvent(
                user_id=user_id, character_id=character_id,
                event_type=evt_type, affinity_delta=affinity_delta,
                mood_before=old_mood.value, mood_after=new_mood.value,
                context=context[:500] if context else None,
            ))

        # --- finalize ---
        state.interaction_count += 1
        state.last_interaction_at = now

        self._repo.flush()
        log_debug(
            f"[Emotion] user={user_id} char={character_id} "
            f"mood={state.mood.value} energy={state.energy:.2f} "
            f"affinity={state.affinity} streak={state.streak_days}"
        )
        return state, mood_changed


    def compute_emotional_context(
        self,
        user_id: uuid.UUID,
        character_id: str,
    ) -> Dict[str, str]:
        """Compute full emotional context dict for prompt injection.

        Returns a dict with keys matching persona prompt placeholders.
        """
        state = self.get_or_create_state(user_id, character_id)

        # Apply energy decay (non-destructive read)
        tier = self.get_relationship_tier(state.affinity)
        time_period = self.get_time_of_day()

        # Build emotional behavior notes
        mood_behaviors = {
            Mood.HAPPY: "You feel cheerful and engaged. Your responses are warm and enthusiastic.",
            Mood.NEUTRAL: "You feel calm and balanced. Your responses are steady and professional.",
            Mood.SAD: "You feel a bit down. Your responses are softer, with a hint of melancholy.",
            Mood.EXCITED: "You feel excited and energetic! Your responses are lively and animated.",
            Mood.FRUSTRATED: "You feel slightly frustrated. Your responses are more terse and direct.",
            Mood.TIRED: "You feel tired and low on energy. Your responses are shorter and more subdued.",
        }

        tier_behaviors = {
            "stranger": "You are polite but reserved. Keep responses professional and formal.",
            "acquaintance": "You are friendly and helpful. A bit more warmth in your tone.",
            "friend": "You are casual and warm. Use their name, share small jokes occasionally.",
            "close_friend": "You are intimate and playful. Tease gently, show genuine care.",
            "bonded": "You are deeply connected. Show strong emotions, be protective and loving.",
        }

        time_behaviors = {
            "early_morning": "It's very early -- you're sleepy and speak softly.",
            "morning": "Good morning energy -- you're fresh and ready to help.",
            "afternoon": "Steady afternoon pace -- balanced and focused.",
            "evening": "Evening wind-down -- relaxed and reflective.",
            "night": "Late night -- quieter, more contemplative tone.",
        }

        energy_note = ""
        if state.energy < 0.2:
            energy_note = " You are running low on energy and feel drowsy."
        elif state.energy < 0.5:
            energy_note = " You are somewhat tired but managing."

        streak_note = ""
        if state.streak_days >= 7:
            streak_note = f" (You've been talking for {state.streak_days} days in a row -- you're happy about this bond!)"

        return {
            "current_mood": state.mood.value,
            "energy_level": f"{state.energy:.0%}",
            "affinity_score": str(state.affinity),
            "relationship_tier": tier,
            "interaction_count": str(state.interaction_count),
            "streak_days": str(state.streak_days),
            "emotional_behavior_notes": (
                f"{mood_behaviors.get(state.mood, '')}\n"
                f"{tier_behaviors.get(tier, '')}\n"
                f"{time_behaviors.get(time_period, '')}"
                f"{energy_note}{streak_note}"
            ),
            "time_period": time_period,
        }


    def get_relationship_history(
        self,
        user_id: uuid.UUID,
        character_id: str,
        limit: int = 20,
    ) -> List[RelationshipEvent]:
        """Retrieve recent relationship events."""
        return self._repo.list_relationship_events(
            user_id=user_id,
            character_id=character_id,
            limit=limit,
        )


    def analyze_sentiment(self, message: str) -> str:
        """Classify user message sentiment using the active LLM.

        Uses a lightweight LLM call to accurately detect sentiment
        including nuanced cases like sarcasm, mixed feelings, and
        implicit frustration.

        Returns: 'positive', 'negative', 'neutral', or 'grateful'
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        from infrastructure.llm import form

        if not message or not message.strip():
            return "neutral"

        system_prompt = (
            "You are a sentiment classifier. Analyze the user's message and respond "
            "with EXACTLY one word -- the sentiment category.\n\n"
            "Categories:\n"
            "- grateful: User is thankful, appreciative, impressed, or praising\n"
            "- positive: User is happy, satisfied, encouraging, or agreeable\n"
            "- negative: User is frustrated, angry, disappointed, critical, or complaining\n"
            "- neutral: Factual question, instruction, or no clear emotional signal\n\n"
            "Consider tone, context, and subtext. Sarcasm should be classified by "
            "the actual underlying emotion, not the surface words.\n\n"
            "Respond with ONE word only: grateful, positive, negative, or neutral."
        )

        try:
            llm = form.SELECTED_MODEL.llm
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=message[:500]),  # cap input length
            ])
            result = str(response.content).strip().lower()

            valid = {"grateful", "positive", "negative", "neutral"}
            if result in valid:
                return result

            # LLM returned something unexpected -- try to parse it
            for v in valid:
                if v in result:
                    return v

            log_debug(f"[Emotion] Unexpected sentiment result: {result!r}, defaulting to neutral")
            return "neutral"

        except Exception as e:
            log_debug(f"[Emotion] Sentiment LLM call failed: {e}, defaulting to neutral")
            return "neutral"
