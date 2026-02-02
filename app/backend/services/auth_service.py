"""
Authentication service for user login, registration, and password management.

Integrates with SQL database for user management.
"""

from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.db.models.user import User, UserRole
from backend.db.models.audit_log import AuditLog
from backend.security.auth import (
    verify_password,
    get_password_hash,
    create_token_pair,
    TokenPair,
)
from backend.schemas.user import UserCreate, UserInDB
from backend.schemas.audit_log import AuditLogCreate
from backend.utils.log import log_info, log_error, log_success, log_warning



class AuthService:
    """Service for handling user authentication and account management."""
    
    @staticmethod
    def login(
        session: Session,
        username: str,
        password: str
    ) -> Tuple[bool, Optional[UserInDB], Optional[TokenPair], Optional[str]]:
        """Authenticate user with username and password.
        
        Returns:
            Tuple of (success, user_data, tokens, error_message)
        """
        try:
            # Try to find user by username or email
            user = session.query(User).filter(User.username == username).first()
            if not user:
                user = session.query(User).filter(User.email == username).first()
            
            if not user:
                log_warning(f"Login failed: User not found - {username}")
                session.add(AuditLog(
                    action="login_failed",
                    details={"username": username, "reason": "user_not_found"}
                ))
                session.commit()
                return False, None, None, "Invalid username or password"
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                log_warning(f"Login failed: Invalid password - {username}")
                session.add(AuditLog(
                    user_id=user.id,
                    action="login_failed",
                    details={"reason": "invalid_password"}
                ))
                session.commit()
                return False, None, None, "Invalid username or password"
            
            # Create JWT tokens
            tokens = create_token_pair(str(user.id), user.role.value)
            
            # Success - create audit log
            log_success(f"User logged in: {user.username}")
            session.add(AuditLog(
                user_id=user.id,
                action="login_success",
                details={"username": user.username, "role": user.role.value}
            ))
            session.commit()
            
            # Convert to schema
            user_data = UserInDB.model_validate(user)
            return True, user_data, tokens, None
            
        except Exception as e:
            log_error(f"Login error: {str(e)}")
            return False, None, None, f"Login error: {str(e)}"
    
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
            # Check if username exists
            if session.query(User).filter(User.username == username).first():
                log_warning(f"Registration failed: Username already exists - {username}")
                return False, None, "Username already exists"
            
            # Check if email exists
            if session.query(User).filter(User.email == email).first():
                log_warning(f"Registration failed: Email already exists - {email}")
                return False, None, "Email already exists"
            
            # Validate password strength
            if len(password) < 8:
                return False, None, "Password must be at least 8 characters"
            
            # Create user
            hashed_password = get_password_hash(password)
            user = User(
                email=email,
                username=username,
                hashed_password=hashed_password,
                role=role
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Create audit log
            log_success(f"New user registered: {username}")
            session.add(AuditLog(
                user_id=user.id,
                action="user_registered",
                details={"username": username, "email": email, "role": role.value}
            ))
            session.commit()
            
            user_data = UserInDB.model_validate(user)
            return True, user_data, None
            
        except Exception as e:
            session.rollback()
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
            # Find user
            user = session.query(User).filter(User.username == username_or_email).first()
            if not user:
                user = session.query(User).filter(User.email == username_or_email).first()
            
            if not user:
                log_warning(f"Password reset failed: User not found - {username_or_email}")
                return False, "User not found"
            
            # Validate new password
            if len(new_password) < 8:
                return False, "Password must be at least 8 characters"
            
            # Update password
            user.hashed_password = get_password_hash(new_password)
            session.add(user)
            
            # Create audit log
            log_success(f"Password reset for user: {user.username}")
            session.add(AuditLog(
                user_id=user.id,
                action="password_reset",
                details={"username": user.username}
            ))
            session.commit()
            
            return True, None
            
        except Exception as e:
            session.rollback()
            log_error(f"Password reset error: {str(e)}")
            return False, f"Password reset error: {str(e)}"
    
    @staticmethod
    def logout(
        session: Session,
        user_id: UUID
    ) -> None:
        """Log user logout event."""
        try:
            session.add(AuditLog(
                user_id=user_id,
                action="logout",
                details={}
            ))
            session.commit()
            log_info(f"User logged out: {user_id}")
        except Exception as e:
            log_error(f"Logout logging error: {str(e)}")
