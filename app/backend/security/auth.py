"""Authentication helpers, password hashing, and JWT token utilities.

Uses:
- passlib for password hashing (Argon2/bcrypt)
- PyJWT for token creation and verification
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.security.jwt_config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    TOKEN_TYPE,
)
from backend.utils.log import log_debug, log_error, log_warning


# Password hashing context using Argon2 (preferred) with bcrypt fallback
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Decoded JWT token data."""
    user_id: str
    role: str
    exp: datetime
    iat: datetime
    token_type: str = "access"


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = TOKEN_TYPE
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


# =============================================================================
# Password Functions (using passlib)
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        log_error(f"Error verifying password: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password for storing using Argon2.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


# =============================================================================
# JWT Token Functions (using PyJWT)
# =============================================================================

def create_access_token(
    user_id: str | UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.
    
    Args:
        user_id: User's unique identifier
        role: User's role (e.g., 'user', 'admin')
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    log_debug(f"Created access token for user {user_id}, expires at {expire}")
    return token


def create_refresh_token(
    user_id: str | UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token.
    
    Args:
        user_id: User's unique identifier
        role: User's role
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    log_debug(f"Created refresh token for user {user_id}, expires at {expire}")
    return token


def create_token_pair(user_id: str | UUID, role: str) -> TokenPair:
    """Create both access and refresh tokens.
    
    Args:
        user_id: User's unique identifier
        role: User's role
        
    Returns:
        TokenPair with access_token and refresh_token
    """
    return TokenPair(
        access_token=create_access_token(user_id, role),
        refresh_token=create_refresh_token(user_id, role),
    )


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        log_warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        log_warning(f"Invalid token: {e}")
        return None


def decode_token(token: str) -> Optional[TokenData]:
    """Decode a JWT token into TokenData.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData if valid, None if invalid
    """
    payload = verify_token(token)
    if not payload:
        return None
    
    try:
        return TokenData(
            user_id=payload["sub"],
            role=payload["role"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            token_type=payload.get("type", "access"),
        )
    except (KeyError, ValueError) as e:
        log_error(f"Error decoding token data: {e}")
        return None


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """Create a new access token from a valid refresh token.
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        New access token if refresh token is valid, None otherwise
    """
    payload = verify_token(refresh_token)
    if not payload:
        return None
    
    if payload.get("type") != "refresh":
        log_warning("Attempted to refresh with non-refresh token")
        return None
    
    user_id = payload.get("sub")
    role = payload.get("role")
    
    if not user_id or not role:
        log_error("Refresh token missing required claims")
        return None
    
    return create_access_token(user_id, role)


def is_token_expired(token: str) -> bool:
    """Check if a token is expired without raising exceptions.
    
    Args:
        token: JWT token string
        
    Returns:
        True if expired or invalid, False if still valid
    """
    return verify_token(token) is None

