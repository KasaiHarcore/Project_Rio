"""Authentication helpers, password hashing, and JWT token utilities.

Uses:
- passlib for password hashing (Argon2/bcrypt)
- PyJWT for token creation and verification
- Redis for token blacklisting (real logout / revocation)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from infrastructure.security.jwt_config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    TOKEN_TYPE,
)
from utils.log import log_debug, log_error, log_warning


# Password hashing context using Argon2 (preferred) with bcrypt fallback
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# Redis-based token blacklist (lazy import to avoid circular deps)
_BLACKLIST_PREFIX = "token:blacklist"


def _blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a token's jti to the Redis blacklist with matching TTL."""
    try:
        from infrastructure.cache.redis_cache import redis_tool

        redis_tool.cache_set_json(
            namespace=_BLACKLIST_PREFIX,
            key=jti,
            value=True,
            ttl_seconds=ttl_seconds,
        )
    except Exception as exc:
        # If Redis is down we degrade gracefully — the token will simply
        # remain valid until its natural expiration.
        log_warning(f"Could not blacklist token (Redis unavailable): {exc}")


def _is_blacklisted(jti: str) -> bool:
    """Check if a jti has been revoked."""
    try:
        from infrastructure.cache.redis_cache import redis_tool

        return redis_tool.cache_get_json(namespace=_BLACKLIST_PREFIX, key=jti) is not None
    except Exception:
        return False


# Pydantic models

class TokenData(BaseModel):
    """Decoded JWT token data."""
    user_id: str
    role: str
    exp: datetime
    iat: datetime
    jti: str = ""
    token_type: str = "access"


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = TOKEN_TYPE
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


# Password Functions (using passlib)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        log_error(f"Error verifying password: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password for storing using Argon2."""
    return pwd_context.hash(password)


# JWT Token Functions (using PyJWT)

def create_access_token(
    user_id: str | UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token with a unique jti claim."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
        "type": "access",
        "jti": uuid4().hex,
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    log_debug("Access token created")
    return token


def create_refresh_token(
    user_id: str | UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token with a unique jti claim."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
        "type": "refresh",
        "jti": uuid4().hex,
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    log_debug("Refresh token created")
    return token


def create_token_pair(user_id: str | UUID, role: str) -> TokenPair:
    """Create both access and refresh tokens."""
    return TokenPair(
        access_token=create_access_token(user_id, role),
        refresh_token=create_refresh_token(user_id, role),
    )


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token.
    
    Returns None if the token is expired, invalid, or blacklisted.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        log_warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        log_warning(f"Invalid token: {e}")
        return None

    # Check blacklist
    jti = payload.get("jti", "")
    if jti and _is_blacklisted(jti):
        log_warning("Token has been revoked")
        return None

    return payload


def decode_token(token: str) -> Optional[TokenData]:
    """Decode a JWT token into TokenData."""
    payload = verify_token(token)
    if not payload:
        return None
    
    try:
        return TokenData(
            user_id=payload["sub"],
            role=payload["role"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            jti=payload.get("jti", ""),
            token_type=payload.get("type", "access"),
        )
    except (KeyError, ValueError) as e:
        log_error(f"Error decoding token data: {e}")
        return None


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """
    Create a new access token from a valid refresh token.
    
    The old refresh token remains valid until expiry (single-use rotation
    can be added later by blacklisting the consumed refresh token).
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


def revoke_token(token: str) -> bool:
    """
    Blacklist a token so it can no longer be used.
    
    Calculates remaining TTL from the token's `exp` claim and stores
    the jti in Redis for that duration.
    
    Returns True if successfully blacklisted.
    """
    try:
        # Decode WITHOUT blacklist check — we want to revoke even if it's
        # already in the list (idempotent).
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return True  # already expired, nothing to revoke
    except jwt.InvalidTokenError:
        return False

    jti = payload.get("jti")
    if not jti:
        return False

    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    remaining = int((exp - datetime.now(timezone.utc)).total_seconds())
    if remaining <= 0:
        return True

    _blacklist_token(jti, remaining)
    return True
