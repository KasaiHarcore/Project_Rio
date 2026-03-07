"""Dashboard stats endpoint: aggregated metrics for the main dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_db
from models.document import Document, DocumentStatus
from models.message import Message, MessageRole
from models.thread import Thread, ThreadStatus
from models.user import User
from models.mission import Mission, MissionStatus
from services.emotional_engine import EmotionalEngine

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ── Response schemas ────────────────────────────────────────────────────────

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


# ── Endpoint ────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate dashboard metrics for the authenticated user.

    Uses Redis L2 cache (60s TTL) to avoid ~20 DB round-trips per call.
    """
    uid = user.id
    uid_str = str(uid)

    # L2 cache: try Redis first
    from infrastructure.cache import cache_service
    cached = cache_service.get_cached_dashboard(uid_str)
    if cached:
        return DashboardStats(**cached)

    now = datetime.now(timezone.utc)

    # Thread counts
    total_threads: int = (
        db.query(func.count(Thread.id))
        .filter(Thread.user_id == uid)
        .scalar() or 0
    )
    active_threads: int = (
        db.query(func.count(Thread.id))
        .filter(Thread.user_id == uid, Thread.status == ThreadStatus.ACTIVE)
        .scalar() or 0
    )

    # Message counts
    user_thread_ids = db.query(Thread.id).filter(Thread.user_id == uid).subquery()

    total_messages: int = (
        db.query(func.count(Message.id))
        .filter(Message.thread_id.in_(db.query(user_thread_ids)))
        .scalar() or 0
    )

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    messages_today: int = (
        db.query(func.count(Message.id))
        .filter(
            Message.thread_id.in_(db.query(user_thread_ids)),
            Message.created_at >= today_start,
        )
        .scalar() or 0
    )

    # Messages per day (last 7 days) for sparkline
    messages_by_day: List[int] = []
    for days_ago in range(6, -1, -1):
        day_start = (now - timedelta(days=days_ago)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        count: int = (
            db.query(func.count(Message.id))
            .filter(
                Message.thread_id.in_(db.query(user_thread_ids)),
                Message.created_at >= day_start,
                Message.created_at < day_end,
            )
            .scalar() or 0
        )
        messages_by_day.append(count)

    # Document counts
    total_documents: int = (
        db.query(func.count(Document.id))
        .filter(Document.user_id == uid)
        .scalar() or 0
    )
    ready_documents: int = (
        db.query(func.count(Document.id))
        .filter(Document.user_id == uid, Document.status == DocumentStatus.READY)
        .scalar() or 0
    )

    # Recent threads with message count (for mission list)
    threads = (
        db.query(Thread)
        .filter(Thread.user_id == uid)
        .order_by(Thread.updated_at.desc())
        .limit(6)
        .all()
    )

    recent_threads: List[ThreadStat] = []
    for t in threads:
        msg_count: int = (
            db.query(func.count(Message.id))
            .filter(Message.thread_id == t.id)
            .scalar() or 0
        )
        # Heuristic progress: ACTIVE with messages → partial, ARCHIVED → 100
        if t.status == ThreadStatus.ARCHIVED:
            progress = 100
        elif msg_count == 0:
            progress = 0
        else:
            progress = min(90, msg_count * 10)  # cap at 90 for active

        recent_threads.append(
            ThreadStat(
                id=str(t.id),
                title=t.title,
                status=t.status.value if hasattr(t.status, "value") else str(t.status),
                progress=progress,
                updated_at=t.updated_at.isoformat() if t.updated_at else "",
                message_count=msg_count,
            )
        )

    # Onboarding + XP check
    from models.user_profile import UserProfile
    from services.xp_service import level_progress, get_user_xp

    profile = db.query(UserProfile).filter(UserProfile.user_id == uid).first()
    onboarding_completed = bool(profile and profile.onboarding_completed)

    xp = get_user_xp(db, uid)
    lp = level_progress(xp)

    result = DashboardStats(
        total_threads=total_threads,
        active_threads=active_threads,
        total_messages=total_messages,
        total_documents=total_documents,
        ready_documents=ready_documents,
        messages_today=messages_today,
        messages_by_day=messages_by_day,
        recent_threads=recent_threads,
        onboarding_completed=onboarding_completed,
        level=lp["level"],
        total_xp=lp["total_xp"],
        xp_in_level=lp["xp_in_level"],
        xp_for_next=lp["xp_for_next"],
    )

    # Backfill Redis cache
    try:
        cache_service.set_cached_dashboard(uid_str, result.model_dump())
    except Exception:
        pass

    return result


# ── Briefing Response Schemas ──────────────────────────────────────────────

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


# ── Briefing Endpoint ──────────────────────────────────────────────────────

@router.get("/briefing", response_model=DashboardBriefing)
def get_dashboard_briefing(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate personalized Rio briefing with context-aware message.

    Returns missions, threads, emotional state, and suggested actions.
    Briefing text adapts based on user activity patterns.
    """
    uid = user.id
    now = datetime.now(timezone.utc)

    # ── Get urgent missions (deadline within 48 hours) ───────────────────
    deadline_threshold = now + timedelta(hours=48)
    urgent_missions_rows = (
        db.query(Mission)
        .filter(
            Mission.user_id == uid,
            Mission.status == MissionStatus.ACTIVE,
            Mission.deadline.isnot(None),
            Mission.deadline <= deadline_threshold,
            Mission.deadline >= now,  # Not overdue
        )
        .order_by(Mission.deadline.asc())
        .limit(5)
        .all()
    )

    urgent_missions = [
        BriefingMission(
            id=str(m.id),
            title=m.title,
            deadline=m.deadline.isoformat() if m.deadline else None,
            progress=m.progress,
        )
        for m in urgent_missions_rows
    ]

    # ── Get last 3 chat threads ─────────────────────────────────────────
    last_threads_rows = (
        db.query(Thread)
        .filter(Thread.user_id == uid, Thread.status == ThreadStatus.ACTIVE)
        .order_by(Thread.updated_at.desc())
        .limit(3)
        .all()
    )

    last_chats = [
        BriefingThread(
            id=str(t.id),
            title=t.title,
            updated_at=t.updated_at.isoformat() if t.updated_at else "",
        )
        for t in last_threads_rows
    ]

    # ── Get emotional state ─────────────────────────────────────────────
    emotional_state = EmotionalEngine.get_or_create_state(
        db=db,
        user_id=uid,
        character_id="rio",
    )

    relationship_tier = EmotionalEngine.get_relationship_tier(emotional_state.affinity)

    emotional_data = EmotionalStateData(
        mood=emotional_state.mood.value,
        energy=emotional_state.energy,
        affinity=emotional_state.affinity,
        relationship_tier=relationship_tier,
        streak_days=emotional_state.streak_days,
        interaction_count=emotional_state.interaction_count,
    )

    # ── Calculate session stats ─────────────────────────────────────────
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    # Messages today
    user_thread_ids = db.query(Thread.id).filter(Thread.user_id == uid).subquery()
    messages_today = (
        db.query(func.count(Message.id))
        .filter(
            Message.thread_id.in_(db.query(user_thread_ids)),
            Message.created_at >= today_start,
        )
        .scalar() or 0
    )

    # Missions completed today
    missions_completed_today = (
        db.query(func.count(Mission.id))
        .filter(
            Mission.user_id == uid,
            Mission.status == MissionStatus.COMPLETED,
            Mission.updated_at >= today_start,
        )
        .scalar() or 0
    )

    # Sessions this week (count days with messages)
    sessions_this_week = (
        db.query(func.count(func.distinct(func.date(Message.created_at))))
        .filter(
            Message.thread_id.in_(db.query(user_thread_ids)),
            Message.created_at >= week_start,
        )
        .scalar() or 0
    )

    session_stats = SessionStats(
        sessions_this_week=sessions_this_week,
        total_messages_today=messages_today,
        missions_completed_today=missions_completed_today,
        streak_days=emotional_state.streak_days,
    )

    # ── Generate briefing text ──────────────────────────────────────────
    briefing_text = _generate_briefing_text(
        urgent_missions=urgent_missions,
        last_chats=last_chats,
        session_stats=session_stats,
        relationship_tier=relationship_tier,
        mood=emotional_state.mood.value,
    )

    # ── Generate suggested actions ──────────────────────────────────────
    suggested_actions = _generate_suggested_actions(
        urgent_missions=urgent_missions,
        last_chats=last_chats,
        messages_today=messages_today,
    )

    return DashboardBriefing(
        briefing_text=briefing_text,
        urgent_missions=urgent_missions,
        last_chats=last_chats,
        emotional_state=emotional_data,
        session_stats=session_stats,
        suggested_actions=suggested_actions,
    )


# ── Helper Functions ────────────────────────────────────────────────────────

def _generate_briefing_text(
    urgent_missions: List[BriefingMission],
    last_chats: List[BriefingThread],
    session_stats: SessionStats,
    relationship_tier: str,
    mood: str,
) -> str:
    """Generate context-aware briefing message from Rio."""

    # Greeting based on relationship tier
    greetings = {
        "stranger": "Neural link established. Systems online.",
        "acquaintance": "Good to see you again.",
        "friend": "Hey there! Ready to tackle today?",
        "close_friend": "Sensei! I've been waiting for you~",
        "bonded": "Welcome back... I missed you.",
    }
    greeting = greetings.get(relationship_tier, "Hello.")

    # Mood-based tone adjustments
    tone_modifiers = {
        "happy": " I'm feeling great today!",
        "excited": " I'm super energized!",
        "sad": " ...I'm here if you need me.",
        "frustrated": " Let's get through this together.",
        "tired": " Running a bit low on energy...",
        "neutral": "",
    }
    tone = tone_modifiers.get(mood, "")

    # Context-based main message
    if urgent_missions:
        count = len(urgent_missions)
        main_msg = f" You have {count} mission{'s' if count != 1 else ''} with upcoming deadlines."
    elif last_chats:
        main_msg = f" You left off on '{last_chats[0].title or 'a conversation'}'."
    elif session_stats.missions_completed_today > 0:
        main_msg = f" Great progress today—{session_stats.missions_completed_today} mission{'s' if session_stats.missions_completed_today != 1 else ''} completed!"
    elif session_stats.streak_days >= 3:
        main_msg = f" {session_stats.streak_days}-day streak active. Let's keep it going!"
    else:
        main_msg = " All systems nominal. What shall we work on today?"

    return f"{greeting}{tone}{main_msg}"


def _generate_suggested_actions(
    urgent_missions: List[BriefingMission],
    last_chats: List[BriefingThread],
    messages_today: int,
) -> List[SuggestedAction]:
    """Generate context-aware action suggestions."""
    actions: List[SuggestedAction] = []

    # Priority 1: Urgent missions
    if urgent_missions:
        actions.append(SuggestedAction(
            label=f"Review {urgent_missions[0].title[:30]}...",
            action="open_mission",
            target=urgent_missions[0].id,
        ))

    # Priority 2: Resume last chat
    if last_chats and messages_today == 0:
        actions.append(SuggestedAction(
            label="Resume Last Chat",
            action="resume_chat",
            target=last_chats[0].id,
        ))

    # Priority 3: Start new chat if active today
    if messages_today > 0:
        actions.append(SuggestedAction(
            label="Start New Chat",
            action="new_chat",
        ))

    # Priority 4: Always offer mission creation
    if len(actions) < 3:
        actions.append(SuggestedAction(
            label="Create Study Mission",
            action="new_mission",
        ))

    # Priority 5: Upload knowledge
    if len(actions) < 3:
        actions.append(SuggestedAction(
            label="Upload Document",
            action="upload_doc",
        ))

    return actions[:3]  # Max 3 actions
