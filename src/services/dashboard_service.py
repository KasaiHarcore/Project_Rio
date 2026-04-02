"""Dashboard service — orchestrates stats and briefing for the dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID

from models.thread import ThreadStatus
from repositories.dashboard_repository import DashboardRepository
from services.emotional_engine import EmotionalEngine
from services.xp_service import level_progress


class DashboardService:
    """Orchestrates dashboard data retrieval."""

    def __init__(
        self,
        dashboard_repo: DashboardRepository,
        emotional_engine: EmotionalEngine,
    ) -> None:
        self._repo = dashboard_repo
        self._emotional = emotional_engine

    def get_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Aggregate dashboard metrics for the authenticated user."""
        thread_stats = self._repo.get_thread_stats(user_id)
        msg_stats = self._repo.get_message_stats(user_id)
        messages_by_day = self._repo.get_messages_by_day(user_id, days=7)
        doc_stats = self._repo.get_document_stats(user_id)

        # Recent threads with message count (no N+1)
        recent_rows = self._repo.get_recent_threads_with_msg_count(user_id, limit=6)
        recent_threads = []
        for thread, msg_count in recent_rows:
            if thread.status == ThreadStatus.ARCHIVED:
                progress = 100
            elif msg_count == 0:
                progress = 0
            else:
                progress = min(90, msg_count * 10)

            recent_threads.append({
                "id": str(thread.id),
                "title": thread.title,
                "status": thread.status.value if hasattr(thread.status, "value") else str(thread.status),
                "progress": progress,
                "updated_at": thread.updated_at.isoformat() if thread.updated_at else "",
                "message_count": msg_count,
            })

        # Onboarding + XP
        profile = self._repo.get_profile(user_id)
        onboarding_completed = bool(profile and profile.onboarding_completed)

        xp = profile.xp if profile else 0
        lp = level_progress(xp)

        return {
            "total_threads": thread_stats["total"],
            "active_threads": thread_stats["active"],
            "total_messages": msg_stats["total"],
            "total_documents": doc_stats["total"],
            "ready_documents": doc_stats["ready"],
            "messages_today": msg_stats["today"],
            "messages_by_day": messages_by_day,
            "recent_threads": recent_threads,
            "onboarding_completed": onboarding_completed,
            "level": lp["level"],
            "total_xp": lp["total_xp"],
            "xp_in_level": lp["xp_in_level"],
            "xp_for_next": lp["xp_for_next"],
        }

    def get_briefing(self, user_id: UUID, messages_today: Optional[int] = None) -> Dict[str, Any]:
        """Generate personalized briefing with context-aware message.

        Args:
            messages_today: Pre-fetched count to avoid redundant DB query.
                If None, will be queried from the repository.
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        # Urgent missions
        deadline_threshold = now + timedelta(hours=48)
        urgent_missions_rows = self._repo.get_urgent_missions(user_id, deadline_threshold)
        urgent_missions = [
            {
                "id": str(m.id),
                "title": m.title,
                "deadline": m.deadline.isoformat() if m.deadline else None,
                "progress": m.progress,
            }
            for m in urgent_missions_rows
        ]

        # Recent threads
        last_threads_rows = self._repo.get_active_threads(user_id, limit=3)
        last_chats = [
            {
                "id": str(t.id),
                "title": t.title,
                "updated_at": t.updated_at.isoformat() if t.updated_at else "",
            }
            for t in last_threads_rows
        ]

        # Emotional state
        emotional_state = self._emotional.get_or_create_state(user_id, "rio")
        relationship_tier = self._emotional.get_relationship_tier(emotional_state.affinity)

        emotional_data = {
            "mood": emotional_state.mood.value,
            "energy": emotional_state.energy,
            "affinity": emotional_state.affinity,
            "relationship_tier": relationship_tier,
            "streak_days": emotional_state.streak_days,
            "interaction_count": emotional_state.interaction_count,
        }

        # Session stats — reuse pre-fetched count if available
        if messages_today is None:
            messages_today = self._repo.get_message_stats(user_id)["today"]
        missions_completed_today = self._repo.get_missions_completed_since(user_id, today_start)
        sessions_this_week = self._repo.get_sessions_since(user_id, week_start)

        session_stats = {
            "sessions_this_week": sessions_this_week,
            "total_messages_today": messages_today,
            "missions_completed_today": missions_completed_today,
            "streak_days": emotional_state.streak_days,
        }

        # Briefing text
        briefing_text = self._generate_briefing_text(
            urgent_missions=urgent_missions,
            last_chats=last_chats,
            session_stats=session_stats,
            relationship_tier=relationship_tier,
            mood=emotional_state.mood.value,
        )

        suggested_actions = self._generate_suggested_actions(
            urgent_missions=urgent_missions,
            last_chats=last_chats,
            messages_today=messages_today,
        )

        return {
            "briefing_text": briefing_text,
            "urgent_missions": urgent_missions,
            "last_chats": last_chats,
            "emotional_state": emotional_data,
            "session_stats": session_stats,
            "suggested_actions": suggested_actions,
        }

    def _generate_briefing_text(
        self,
        urgent_missions: List[Dict],
        last_chats: List[Dict],
        session_stats: Dict,
        relationship_tier: str,
        mood: str,
    ) -> str:
        """Generate context-aware briefing message from Rio."""
        greetings = {
            "stranger": "Neural link established. Systems online.",
            "acquaintance": "Good to see you again.",
            "friend": "Hey there! Ready to tackle today?",
            "close_friend": "Sensei! I've been waiting for you~",
            "bonded": "Welcome back... I missed you.",
        }
        greeting = greetings.get(relationship_tier, "Hello.")

        tone_modifiers = {
            "happy": " I'm feeling great today!",
            "excited": " I'm super energized!",
            "sad": " ...I'm here if you need me.",
            "frustrated": " Let's get through this together.",
            "tired": " Running a bit low on energy...",
            "neutral": "",
        }
        tone = tone_modifiers.get(mood, "")

        if urgent_missions:
            count = len(urgent_missions)
            main_msg = f" You have {count} mission{'s' if count != 1 else ''} with upcoming deadlines."
        elif last_chats:
            main_msg = f" You left off on '{last_chats[0].get('title') or 'a conversation'}'."
        elif session_stats["missions_completed_today"] > 0:
            n = session_stats["missions_completed_today"]
            main_msg = f" Great progress today—{n} mission{'s' if n != 1 else ''} completed!"
        elif session_stats["streak_days"] >= 3:
            main_msg = f" {session_stats['streak_days']}-day streak active. Let's keep it going!"
        else:
            main_msg = " All systems nominal. What shall we work on today?"

        return f"{greeting}{tone}{main_msg}"

    def _generate_suggested_actions(
        self,
        urgent_missions: List[Dict],
        last_chats: List[Dict],
        messages_today: int,
    ) -> List[Dict]:
        """Generate context-aware action suggestions."""
        actions: List[Dict] = []

        if urgent_missions:
            actions.append({
                "label": f"Review {urgent_missions[0]['title'][:30]}...",
                "action": "open_mission",
                "target": urgent_missions[0]["id"],
            })

        if last_chats and messages_today == 0:
            actions.append({
                "label": "Resume Last Chat",
                "action": "resume_chat",
                "target": last_chats[0]["id"],
            })

        if messages_today > 0:
            actions.append({
                "label": "Start New Chat",
                "action": "new_chat",
                "target": None,
            })

        if len(actions) < 3:
            actions.append({
                "label": "Create Study Mission",
                "action": "new_mission",
                "target": None,
            })

        if len(actions) < 3:
            actions.append({
                "label": "Upload Document",
                "action": "upload_doc",
                "target": None,
            })

        return actions[:3]
