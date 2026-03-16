"""FastAPI dependency injection chain.

Provides the complete DI graph:
    get_db → get_*_repository → get_*_service

Also provides authentication dependencies:
    get_current_user_token → get_current_user → require_admin
"""

from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.exceptions import AuthenticationError, AuthorizationError

from infrastructure.database.session import get_db
from infrastructure.security.auth import decode_token, TokenData
from models.user import User, UserRole
from utils.log import log_warning

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

from infrastructure.cache.service import CacheService
from services.auth_service import AuthService
from services.mission_service import MissionService
from services.note_service import NoteService
from services.artifact_service import ArtifactService
from services.collection_service import CollectionService
from services.emotional_engine import EmotionalEngine
from services.settings_service import SettingsService
from services.xp_service import XPService
from services.chat_service import ChatService
from services.dashboard_service import DashboardService
from services.document_service import DocumentService
from services.note_link_service import NoteLinkService

def get_cache_service() -> CacheService:
    """Provide the CacheService singleton via DI."""
    from infrastructure.cache import cache_service
    return cache_service

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> TokenData:
    """Extract and validate the JWT from the Authorization header."""
    if credentials is None:
        raise AuthenticationError("Missing authentication token")

    token_data = decode_token(credentials.credentials)
    if token_data is None:
        raise AuthenticationError("Invalid or expired token")

    if token_data.token_type != "access":
        raise AuthenticationError("Invalid token type – access token required")

    return token_data


async def get_current_user(
    token_data: TokenData = Depends(get_current_user_token),
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
) -> User:
    """Resolve the full User ORM object from the validated JWT."""
    try:
        user_id = UUID(token_data.user_id)
    except ValueError:
        raise AuthenticationError("Invalid user ID in token")

    # L2 cache: try Redis first
    cached = cache.get_cached_user(str(user_id))
    if cached:
        user = db.get(User, user_id)
        if user is not None:
            return user

    # Cache miss → Postgres
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        log_warning(f"Token valid but user not found: {token_data.user_id}")
        raise AuthenticationError("User not found")

    # Backfill cache
    try:
        cache.set_cached_user(str(user_id), {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        })
    except Exception:
        pass

    return user


def require_roles(*allowed: UserRole):
    """Dependency factory: enforces that the user has one of the allowed roles.

    Usage:
        @router.get("/admin-only")
        async def endpoint(user: User = Depends(require_roles(UserRole.ADMIN))):
            ...

        @router.post("/power-users")
        async def endpoint(user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MODERATOR))):
            ...
    """
    async def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise AuthorizationError(
                f"Requires role: {', '.join(r.value for r in allowed)}"
            )
        return user
    return _guard


# Convenience alias
require_admin = require_roles(UserRole.ADMIN)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_thread_repository(db: Session = Depends(get_db)) -> ThreadRepository:
    return ThreadRepository(db)


def get_message_repository(db: Session = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db)


def get_mission_repository(db: Session = Depends(get_db)) -> MissionRepository:
    return MissionRepository(db)


def get_note_repository(db: Session = Depends(get_db)) -> NoteRepository:
    return NoteRepository(db)


def get_artifact_repository(db: Session = Depends(get_db)) -> ArtifactRepository:
    return ArtifactRepository(db)


def get_collection_repository(db: Session = Depends(get_db)) -> CollectionRepository:
    return CollectionRepository(db)


def get_emotional_state_repository(db: Session = Depends(get_db)) -> EmotionalStateRepository:
    return EmotionalStateRepository(db)


def get_settings_repository(db: Session = Depends(get_db)) -> SettingsRepository:
    return SettingsRepository(db)


def get_audit_log_repository(db: Session = Depends(get_db)) -> AuditLogRepository:
    return AuditLogRepository(db)


def get_document_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_user_profile_repository(db: Session = Depends(get_db)) -> UserProfileRepository:
    return UserProfileRepository(db)


def get_dashboard_repository(db: Session = Depends(get_db)) -> DashboardRepository:
    return DashboardRepository(db)


def get_note_link_repository(db: Session = Depends(get_db)) -> NoteLinkRepository:
    return NoteLinkRepository(db)

def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> AuthService:
    return AuthService(user_repo, audit_repo)


def get_mission_service(
    mission_repo: MissionRepository = Depends(get_mission_repository),
    cache: CacheService = Depends(get_cache_service),
) -> MissionService:
    return MissionService(mission_repo, cache_service=cache)


def get_note_service(
    note_repo: NoteRepository = Depends(get_note_repository),
    link_repo: NoteLinkRepository = Depends(get_note_link_repository),
) -> NoteService:
    link_service = NoteLinkService(link_repo, note_repo)
    return NoteService(note_repo, note_link_service=link_service)


def get_artifact_service(
    artifact_repo: ArtifactRepository = Depends(get_artifact_repository),
) -> ArtifactService:
    return ArtifactService(artifact_repo)


def get_collection_service(
    collection_repo: CollectionRepository = Depends(get_collection_repository),
) -> CollectionService:
    return CollectionService(collection_repo)


def get_emotional_engine(
    emotional_repo: EmotionalStateRepository = Depends(get_emotional_state_repository),
) -> EmotionalEngine:
    return EmotionalEngine(emotional_repo)


def get_settings_service(
    settings_repo: SettingsRepository = Depends(get_settings_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    profile_repo: UserProfileRepository = Depends(get_user_profile_repository),
) -> SettingsService:
    return SettingsService(settings_repo, user_repo, profile_repo)


def get_xp_service(
    profile_repo: UserProfileRepository = Depends(get_user_profile_repository),
    cache: CacheService = Depends(get_cache_service),
) -> XPService:
    return XPService(profile_repo, cache_service=cache)


def get_dashboard_service(
    dashboard_repo: DashboardRepository = Depends(get_dashboard_repository),
    emotional_engine: EmotionalEngine = Depends(get_emotional_engine),
) -> DashboardService:
    return DashboardService(dashboard_repo, emotional_engine)


def get_note_link_service(
    link_repo: NoteLinkRepository = Depends(get_note_link_repository),
    note_repo: NoteRepository = Depends(get_note_repository),
) -> NoteLinkService:
    return NoteLinkService(link_repo, note_repo)


def get_document_service(
    document_repo: DocumentRepository = Depends(get_document_repository),
) -> DocumentService:
    return DocumentService(document_repo)


def get_chat_service(
    xp: XPService = Depends(get_xp_service),
    settings: SettingsService = Depends(get_settings_service),
    cache: CacheService = Depends(get_cache_service),
) -> ChatService:
    from services.chat_history_service import chat_history_service
    return ChatService(chat_history_service, xp, settings, cache)
