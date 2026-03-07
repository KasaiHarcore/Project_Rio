"""Authentication endpoints: login, register, me, refresh, reset-password, logout.

Security measures:
- Rate limiting on public endpoints (login, register) via in-memory sliding window
- Password reset requires authentication (user must be logged in)
- Logout revokes tokens server-side via Redis blacklist
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_db
from services.auth_service import AuthService
from core.exceptions import AuthenticationError, DuplicateError, ValidationError
from models.user import User
from schemas.user import UserInDB
from infrastructure.security.auth import (
    TokenPair,
    create_token_pair,
    refresh_access_token,
    revoke_token,
)


router = APIRouter(prefix="/auth", tags=["auth"])


# ── Rate limiter (in-memory sliding window) ─────────────────────────────────

_rate_lock = Lock()
_rate_buckets: dict[str, list[float]] = defaultdict(list)

# Limits: max requests per window (seconds)
_RATE_AUTH_MAX = 10
_RATE_AUTH_WINDOW = 60  # 10 requests per 60s per IP


def _check_rate_limit(request: Request, action: str = "auth") -> None:
    """Raise 429 if the client exceeds the rate limit."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"{action}:{client_ip}"
    now = time.monotonic()

    with _rate_lock:
        bucket = _rate_buckets[key]
        # Purge entries outside the window
        cutoff = now - _RATE_AUTH_WINDOW
        _rate_buckets[key] = bucket = [t for t in bucket if t > cutoff]

        if len(bucket) >= _RATE_AUTH_MAX:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
        bucket.append(now)


# ── Request / Response schemas ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="Password")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")


class LogoutRequest(BaseModel):
    """Optional: client can send current tokens so they get revoked."""
    access_token: str | None = None
    refresh_token: str | None = None


class AuthResponse(BaseModel):
    success: bool = True
    user: UserInDB
    tokens: TokenPair


class MeResponse(BaseModel):
    success: bool = True
    user: UserInDB


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate and return JWT token pair."""
    _check_rate_limit(request, "login")

    success, user_data, tokens, error = AuthService.login(db, body.username, body.password)

    if not success:
        raise AuthenticationError(error or "Authentication failed")

    return AuthResponse(user=user_data, tokens=tokens)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Create a new user account and return JWT tokens."""
    _check_rate_limit(request, "register")

    success, user_data, error = AuthService.register(
        db, body.username, body.email, body.password
    )

    if not success:
        raise DuplicateError(error or "Registration failed")

    # Generate tokens for the newly registered user
    tokens = create_token_pair(str(user_data.id), user_data.role.value)
    return AuthResponse(user=user_data, tokens=tokens)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    user_data = UserInDB.model_validate(user)
    return MeResponse(user=user_data)


@router.post("/refresh")
def refresh(body: RefreshRequest, request: Request):
    """Exchange a refresh token for a new access token."""
    _check_rate_limit(request, "refresh")

    new_access_token = refresh_access_token(body.refresh_token)

    if new_access_token is None:
        raise AuthenticationError("Invalid or expired refresh token")

    return {
        "success": True,
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reset the authenticated user's password.

    Requires a valid access token — the user resets their **own** password.
    """
    success, error = AuthService.reset_password(
        db, user.username, body.new_password
    )

    if not success:
        raise ValidationError(error or "Password reset failed")

    # Invalidate cached user data
    try:
        from infrastructure.cache import cache_service
        cache_service.invalidate_user(str(user.id))
    except Exception:
        pass

    return {"success": True, "message": "Password reset successfully"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: LogoutRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Log out: revoke tokens server-side and record the event."""
    # Revoke tokens via Redis blacklist so they can't be reused
    if body:
        if body.access_token:
            revoke_token(body.access_token)
        if body.refresh_token:
            revoke_token(body.refresh_token)

    AuthService.logout(db, user.id)
    return None

