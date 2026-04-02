"""Dashboard stats endpoint: aggregated metrics for the main dashboard."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_dashboard_service, get_cache_service
from infrastructure.cache.service import CacheService
from models.user import User
from services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])



class ThreadStat(BaseModel):
    id: str
    title: Optional[str]
    status: str
    progress: int  # 0-100 heuristic
    updated_at: str
    message_count: int


class DashboardStats(BaseModel):
    total_threads: int
    active_threads: int
    total_messages: int
    total_documents: int
    ready_documents: int
    messages_today: int
    messages_by_day: List[int]  # last 7 days
    recent_threads: List[ThreadStat]
    onboarding_completed: bool
    # XP / Level
    level: int
    total_xp: int
    xp_in_level: int
    xp_for_next: int



@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    user: User = Depends(get_current_user),
    svc: DashboardService = Depends(get_dashboard_service),
    cache: CacheService = Depends(get_cache_service),
):
    """Aggregate dashboard metrics for the authenticated user.

    Uses Redis L2 cache (60s TTL) to avoid ~20 DB round-trips per call.
    """
    uid_str = str(user.id)

    # L2 cache: try Redis first
    cached = cache.get_cached_dashboard(uid_str)
    if cached:
        return DashboardStats(**cached)

    def _query():
        result = svc.get_stats(user.id)
        stats = DashboardStats(**result)

        # Backfill Redis cache
        try:
            cache.set_cached_dashboard(uid_str, stats.model_dump())
        except Exception:
            pass

        return stats

    return await concurrency_manager.run_in_thread(_query)



class BriefingMission(BaseModel):
    """Simplified mission for briefing."""
    id: str
    title: str
    deadline: Optional[str]
    progress: int


class BriefingThread(BaseModel):
    """Simplified thread for briefing."""
    id: str
    title: Optional[str]
    updated_at: str


class EmotionalStateData(BaseModel):
    """Emotional state snapshot."""
    mood: str
    energy: float
    affinity: int
    relationship_tier: str
    streak_days: int
    interaction_count: int


class SessionStats(BaseModel):
    """Session activity stats."""
    sessions_this_week: int
    total_messages_today: int
    missions_completed_today: int
    streak_days: int


class SuggestedAction(BaseModel):
    """Call-to-action suggestion."""
    label: str
    action: str  # e.g. "resume_chat", "start_mission", "upload_doc"
    target: Optional[str] = None  # thread_id, mission_id, etc.


class DashboardBriefing(BaseModel):
    """Personalized Rio briefing for dashboard."""
    briefing_text: str
    urgent_missions: List[BriefingMission]
    last_chats: List[BriefingThread]
    emotional_state: EmotionalStateData
    session_stats: SessionStats
    suggested_actions: List[SuggestedAction]



@router.get("/briefing", response_model=DashboardBriefing)
async def get_dashboard_briefing(
    user: User = Depends(get_current_user),
    svc: DashboardService = Depends(get_dashboard_service),
):
    """Generate personalized Rio briefing with context-aware message.

    Returns missions, threads, emotional state, and suggested actions.
    Briefing text adapts based on user activity patterns.
    """
    def _query():
        return svc.get_briefing(user.id)

    result = await concurrency_manager.run_in_thread(_query)
    return DashboardBriefing(**result)
