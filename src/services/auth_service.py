"""Authentication service for user login, registration, and password management.

Uses UserRepository and AuditLogRepository for data access.
No direct session.query() calls — all DB access goes through repositories.
"""

from typing import Optional, Tuple
from uuid import UUID

from models.user import User, UserRole, AuthProvider
from infrastructure.security.auth import (
    verify_password,
    get_password_hash,
    create_token_pair,
    TokenPair,
)
from schemas.user import UserInDB
from repositories.user_repository import UserRepository
from repositories.audit_log_repository import AuditLogRepository
from utils.log import log_info, log_error, log_success, log_warning


class AuthService:
    """Service for handling user authentication and account management."""

    def __init__(self, user_repo: UserRepository, audit_repo: AuditLogRepository):
        self.user_repo = user_repo
        self.audit_repo = audit_repo

    def login(
        self,
        username: str,
        password: str,
    ) -> Tuple[bool, Optional[UserInDB], Optional[TokenPair], Optional[str]]:
        """Authenticate user with username and password.

        Returns:
            Tuple of (success, user_data, tokens, error_message)
        """
        try:
            user = self.user_repo.find_by_username_or_email(username)

            if not user:
                log_warning(f"Login failed: User not found - {username}")
                self.audit_repo.create(
                    user_id=None,
                    action="login_failed",
                    details={"username": username, "reason": "user_not_found"},
                )
                return False, None, None, "Invalid username or password"

            if user.hashed_password is None:
                log_warning(f"Login failed: OAuth-only account has no password - {username}")
                self.audit_repo.create(
                    user_id=user.id,
                    action="login_failed",
                    details={"reason": "oauth_only_account"},
                )
                return False, None, None, "This account uses OAuth login. Please sign in with your OAuth provider."

            if not verify_password(password, user.hashed_password):
                log_warning(f"Login failed: Invalid password - {username}")
                self.audit_repo.create(
                    user_id=user.id,
                    action="login_failed",
                    details={"reason": "invalid_password"},
                )
                return False, None, None, "Invalid username or password"

            tokens = create_token_pair(str(user.id), user.role.value)

            log_success(f"User logged in: {user.username}")
            self.audit_repo.create(
                user_id=user.id,
                action="login_success",
                details={"username": user.username, "role": user.role.value},
            )

            user_data = UserInDB.model_validate(user)
            return True, user_data, tokens, None

        except Exception as e:
            log_error(f"Login error: {str(e)}")
            return False, None, None, "An internal error occurred. Please try again."

    def register(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
    ) -> Tuple[bool, Optional[UserInDB], Optional[str]]:
        """Register a new user account."""
        try:
            if self.user_repo.username_exists(username):
                log_warning(f"Registration failed: Username already exists - {username}")
                return False, None, "Username already exists"

            if self.user_repo.email_exists(email):
                log_warning(f"Registration failed: Email already exists - {email}")
                return False, None, "Email already exists"

            if len(password) < 8:
                return False, None, "Password must be at least 8 characters"

            hashed_password = get_password_hash(password)
            user = User(
                email=email,
                username=username,
                hashed_password=hashed_password,
                role=role,
            )
            user = self.user_repo.create(user)

            log_success(f"New user registered: {username}")
            self.audit_repo.create(
                user_id=user.id,
                action="user_registered",
                details={"username": username, "email": email, "role": role.value},
            )

            user_data = UserInDB.model_validate(user)
            return True, user_data, None

        except Exception as e:
            log_error(f"Registration error: {str(e)}")
            return False, None, "An internal error occurred. Please try again."

    def reset_password(
        self,
        username_or_email: str,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """Reset user password (simplified for local use)."""
        try:
            user = self.user_repo.find_by_username_or_email(username_or_email)

            if not user:
                log_warning(f"Password reset failed: User not found - {username_or_email}")
                return False, "User not found"

            if len(new_password) < 8:
                return False, "Password must be at least 8 characters"

            user.hashed_password = get_password_hash(new_password)

            log_success(f"Password reset for user: {user.username}")
            self.audit_repo.create(
                user_id=user.id,
                action="password_reset",
                details={"username": user.username},
            )

            return True, None

        except Exception as e:
            log_error(f"Password reset error: {str(e)}")
            return False, "An internal error occurred. Please try again."

    def get_or_create_oauth_user(
        self,
        oauth_id: str,
        provider: AuthProvider,
        email: str,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Tuple[User, bool]:
        """Resolve or create a user from OAuth info.

        Returns:
            Tuple of (user, is_new_user)
        """
        # Check by oauth_id + provider
        user = self.user_repo.find_by_oauth(provider.value, oauth_id)
        if user:
            return user, False

        # Check by email (account linking)
        user = self.user_repo.find_by_email(email)
        if user:
            log_info(f"[OAuth] Linking {email} to {provider.value}")
            user.auth_provider = provider
            user.oauth_id = oauth_id
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            self.user_repo.flush()
            return user, False

        # Create new user
        log_info(f"[OAuth] Creating new user: {email} via {provider.value}")
        username = self._generate_unique_username(name, email)
        user = User(
            username=username,
            email=email,
            hashed_password=None,
            role=UserRole.USER,
            auth_provider=provider,
            oauth_id=oauth_id,
            avatar_url=avatar_url,
        )
        user = self.user_repo.create(user)

        self.audit_repo.create(
            user_id=user.id,
            action="oauth_registration",
            details={"email": email, "provider": provider.value},
        )

        return user, True

    def _generate_unique_username(self, name: Optional[str], email: str) -> str:
        """Generate a unique username from OAuth display name or email."""
        base = name.lower().replace(" ", "_")[:50] if name else email.split("@")[0]
        base = "".join(c for c in base if c.isalnum() or c == "_")
        if not base:
            base = "user"

        username = base
        counter = 1
        while self.user_repo.username_exists(username):
            username = f"{base}_{counter}"
            counter += 1

        return username

    def logout(self, user_id: UUID) -> None:
        """Log user logout event."""
        try:
            self.audit_repo.create(user_id=user_id, action="logout", details={})
            log_info(f"User logged out: {user_id}")
        except Exception as e:
            log_error(f"Logout logging error: {str(e)}")
