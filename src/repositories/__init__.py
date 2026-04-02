"""Repository layer — data access abstraction for all domain models."""

from repositories.base import BaseRepository
from repositories.user_repository import UserRepository
from repositories.thread_repository import ThreadRepository
from repositories.message_repository import MessageRepository
from repositories.mission_repository import MissionRepository
from repositories.note_repository import NoteRepository
from repositories.artifact_repository import ArtifactRepository
from repositories.collection_repository import CollectionRepository
from repositories.emotional_state_repository import EmotionalStateRepository
from repositories.settings_repository import SettingsRepository
from repositories.audit_log_repository import AuditLogRepository
from repositories.document_repository import DocumentRepository
from repositories.user_profile_repository import UserProfileRepository
from repositories.dashboard_repository import DashboardRepository
from repositories.note_link_repository import NoteLinkRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ThreadRepository",
    "MessageRepository",
    "MissionRepository",
    "NoteRepository",
    "ArtifactRepository",
    "CollectionRepository",
    "EmotionalStateRepository",
    "SettingsRepository",
    "AuditLogRepository",
    "DocumentRepository",
    "UserProfileRepository",
    "DashboardRepository",
    "NoteLinkRepository",
]
