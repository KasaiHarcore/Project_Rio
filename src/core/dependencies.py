"""FastAPI dependency injection chain.

Provides the complete DI graph:
    get_db → get_*_repository → get_*_service

Also provides authentication dependencies:
    get_current_user_token → get_current_user → require_admin
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.exceptions import AuthorizationError

from infrastructure.database.session import get_db
from infrastructure.security.auth import decode_token, TokenData
from models.user import User, UserRole
from utils.log import log_warning

# ── Repositories ──────────────────────────────────────────────────────────

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

# ── Services ──────────────────────────────────────────────────────────────

from services.auth_service import AuthService
from services.mission_service import MissionService
from services.note_service import NoteService
from services.artifact_service import ArtifactService
from services.collection_service import CollectionService
from services.emotional_engine import EmotionalEngine
from services.settings_service import SettingsService
from services.xp_service import XPService


# ═══════════════════════════════════════════════════════════════════════════
# Authentication dependencies
# ═══════════════════════════════════════════════════════════════════════════

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> TokenData:
    """Extract and validate the JWT from the Authorization header."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_data.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type – access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


async def get_current_user(
    token_data: TokenData = Depends(get_current_user_token),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the full User ORM object from the validated JWT."""
    try:
        user_id = UUID(token_data.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    # L2 cache: try Redis first
    from infrastructure.cache import cache_service
    cached = cache_service.get_cached_user(str(user_id))
    if cached:
        user = db.get(User, user_id)
        if user is not None:
            return user

    # Cache miss → Postgres
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        log_warning(f"Token valid but user not found: {token_data.user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Backfill cache
    try:
        cache_service.set_cached_user(str(user_id), {
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


# ═══════════════════════════════════════════════════════════════════════════
# Repository factories
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# Service factories
# ═══════════════════════════════════════════════════════════════════════════

def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> AuthService:
    return AuthService(user_repo, audit_repo)


def get_mission_service(
    mission_repo: MissionRepository = Depends(get_mission_repository),
) -> MissionService:
    return MissionService(mission_repo)


def get_note_service(
    note_repo: NoteRepository = Depends(get_note_repository),
) -> NoteService:
    return NoteService(note_repo)


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
) -> XPService:
    return XPService(profile_repo)
