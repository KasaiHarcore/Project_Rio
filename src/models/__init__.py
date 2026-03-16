"""SQLAlchemy ORM Models for Application Entities."""

from models.user import User, UserRole, AuthProvider
from models.thread import Thread, ThreadStatus
from models.message import Message, MessageRole
from models.user_profile import UserProfile
from models.user_settings import UserSettings
from models.audit_log import AuditLog
from models.document import Document, DocumentStatus
from models.mission import Mission, MissionStatus, MissionPriority, MissionSource
from models.note import Note, NoteSource
from models.note_collection import NoteCollection
from models.emotional_state import EmotionalState, Mood
from models.relationship_event import RelationshipEvent, RelationshipEventType
from models.artifact import Artifact
from models.note_link import NoteLink, NoteLinkTargetType

from sqlalchemy.orm import configure_mappers
configure_mappers()

__all__ = [
    "User",
    "UserRole",
    "AuthProvider",
    "Thread",
    "ThreadStatus",
    "Message",
    "MessageRole",
    "UserProfile",
    "UserSettings",
    "AuditLog",
    "Document",
    "DocumentStatus",
    "Mission",
    "MissionStatus",
    "MissionPriority",
    "MissionSource",
    "Note",
    "NoteSource",
    "NoteCollection",
    "EmotionalState",
    "Mood",
    "RelationshipEvent",
    "RelationshipEventType",
    "Artifact",
    "NoteLink",
    "NoteLinkTargetType",
]
