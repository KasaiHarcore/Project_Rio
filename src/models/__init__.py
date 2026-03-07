"""SQLAlchemy ORM Models for Application Entities.

Model Hierarchy:
    User
    ├── UserProfile (1:1)
    ├── Thread (1:N)
    │   └── Message (1:N)
    ├── EmotionalState (1:N, per character)
    │   └── RelationshipEvent (audit trail)
    ├── Mission (1:N)
    ├── Note (1:N, via Thread CASCADE)
    │   └── NoteCollection (N:1)
    ├── Document (1:N)
    └── AuditLog (1:N)
"""

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
]
