"""
Authentication service for user login, registration, and password management.

Integrates with SQL database for user management.
"""

from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from backend.db.models.user import User, UserRole
from backend.db.repositories.user_repo import UserRepository
from backend.db.repositories.audit_log_repo import AuditLogRepository
from backend.security.auth import verify_password
from backend.schemas.user import UserCreate, UserUpdate, UserInDB
from backend.schemas.audit_log import AuditLogCreate
from backend.utils.log import log_info, log_error, log_success, log_warning


class AuthService:
    """Service for handling user authentication and account management."""
    
    @staticmethod
    def login(
        session: Session,
        username: str,
        password: str
    ) -> Tuple[bool, Optional[UserInDB], Optional[str]]:
        """Authenticate user with username and password."""
        try:
            user_repo = UserRepository(session)
            audit_repo = AuditLogRepository(session)
            
            # Try to find user by username or email
            user = user_repo.get_by_username(username)
            if not user:
                user = user_repo.get_by_email(username)
            
            if not user:
                log_warning(f"Login failed: User not found - {username}")
                audit_repo.create(AuditLogCreate(
                    action="login_failed",
                    details={"username": username, "reason": "user_not_found"}
                ))
                return False, None, "Invalid username or password"
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                log_warning(f"Login failed: Invalid password - {username}")
                audit_repo.create(AuditLogCreate(
                    user_id=user.id,
                    action="login_failed",
                    details={"reason": "invalid_password"}
                ))
                return False, None, "Invalid username or password"
            
            # Success - create audit log
            log_success(f"User logged in: {user.username}")
            audit_repo.create(AuditLogCreate(
                user_id=user.id,
                action="login_success",
                details={"username": user.username, "role": user.role.value}
            ))
            
            # Convert to schema
            user_data = UserInDB.model_validate(user)
            return True, user_data, None
            
        except Exception as e:
            log_error(f"Login error: {str(e)}")
            return False, None, f"Login error: {str(e)}"
    
    @staticmethod
    def register(
        session: Session,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER
    ) -> Tuple[bool, Optional[UserInDB], Optional[str]]:
        """Register a new user account."""
        try:
            user_repo = UserRepository(session)
            audit_repo = AuditLogRepository(session)
            
            # Check if username exists
            if user_repo.get_by_username(username):
                log_warning(f"Registration failed: Username already exists - {username}")
                return False, None, "Username already exists"
            
            # Check if email exists
            if user_repo.get_by_email(email):
                log_warning(f"Registration failed: Email already exists - {email}")
                return False, None, "Email already exists"
            
            # Validate password strength
            if len(password) < 8:
                return False, None, "Password must be at least 8 characters"
            
            # Create user
            user_create = UserCreate(
                username=username,
                email=email,
                password=password,
                role=role
            )
            
            user = user_repo.create(user_create)
            
            # Create audit log
            log_success(f"New user registered: {username}")
            audit_repo.create(AuditLogCreate(
                user_id=user.id,
                action="user_registered",
                details={"username": username, "email": email, "role": role.value}
            ))
            
            user_data = UserInDB.model_validate(user)
            return True, user_data, None
            
        except Exception as e:
            log_error(f"Registration error: {str(e)}")
            return False, None, f"Registration error: {str(e)}"
    
    @staticmethod
    def reset_password(
        session: Session,
        username_or_email: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """Reset user password (simplified for local use)."""
        try:
            user_repo = UserRepository(session)
            audit_repo = AuditLogRepository(session)
            
            # Find user
            user = user_repo.get_by_username(username_or_email)
            if not user:
                user = user_repo.get_by_email(username_or_email)
            
            if not user:
                log_warning(f"Password reset failed: User not found - {username_or_email}")
                return False, "User not found"
            
            # Validate new password
            if len(new_password) < 8:
                return False, "Password must be at least 8 characters"
            
            # Update password
            user_update = UserUpdate(password=new_password)
            user_repo.update(user.id, user_update)
            
            # Create audit log
            log_success(f"Password reset for user: {user.username}")
            audit_repo.create(AuditLogCreate(
                user_id=user.id,
                action="password_reset",
                details={"username": user.username}
            ))
            
            return True, None
            
        except Exception as e:
            log_error(f"Password reset error: {str(e)}")
            return False, f"Password reset error: {str(e)}"
    
    @staticmethod
    def logout(
        session: Session,
        user_id: UUID
    ) -> None:
        """Log user logout event."""
        try:
            audit_repo = AuditLogRepository(session)
            audit_repo.create(AuditLogCreate(
                user_id=user_id,
                action="logout",
                details={}
            ))
            log_info(f"User logged out: {user_id}")
        except Exception as e:
            log_error(f"Logout logging error: {str(e)}")
