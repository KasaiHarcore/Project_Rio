"""Authentication endpoints: login, register, me, refresh, reset-password, logout.

Security measures:
- Rate limiting on public endpoints (login, register) via Redis sliding window
- Password reset requires authentication (user must be logged in)
- Logout revokes tokens server-side via Redis blacklist
"""

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, EmailStr, Field

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_auth_service, get_cache_service
from infrastructure.cache.service import CacheService
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
from infrastructure.security.rate_limiter import RedisRateLimiter


router = APIRouter(prefix="/auth", tags=["auth"])



_rate_limiter = RedisRateLimiter(max_requests=10, window_seconds=60)



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



@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    """Authenticate and return JWT token pair."""
    _rate_limiter.check(request, "login")

    success, user_data, tokens, error = await concurrency_manager.run_in_thread(
        svc.login, body.username, body.password
    )

    if not success:
        raise AuthenticationError(error or "Authentication failed")

    return AuthResponse(user=user_data, tokens=tokens)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    """Create a new user account and return JWT tokens."""
    _rate_limiter.check(request, "register")

    success, user_data, error = await concurrency_manager.run_in_thread(
        svc.register, body.username, body.email, body.password
    )

    if not success:
        raise DuplicateError(error or "Registration failed")

    # Generate tokens for the newly registered user
    tokens = create_token_pair(str(user_data.id), user_data.role.value)
    return AuthResponse(user=user_data, tokens=tokens)


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    user_data = UserInDB.model_validate(user)
    return MeResponse(user=user_data)


@router.post("/refresh")
async def refresh(body: RefreshRequest, request: Request):
    """Exchange a refresh token for a new access token."""
    _rate_limiter.check(request, "refresh")

    new_access_token = await concurrency_manager.run_in_thread(
        refresh_access_token, body.refresh_token
    )

    if new_access_token is None:
        raise AuthenticationError("Invalid or expired refresh token")

    return {
        "success": True,
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
    cache: CacheService = Depends(get_cache_service),
):
    """Reset the authenticated user's password.

    Requires a valid access token — the user resets their **own** password.
    """
    success, error = await concurrency_manager.run_in_thread(
        svc.reset_password, user.username, body.new_password
    )

    if not success:
        raise ValidationError(error or "Password reset failed")

    # Invalidate cached user data
    try:
        cache.invalidate_user(str(user.id))
    except Exception:
        pass

    return {"success": True, "message": "Password reset successfully"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest | None = None,
    user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
):
    """Log out: revoke tokens server-side and record the event."""
    # Revoke tokens via Redis blacklist so they can't be reused
    if body:
        if body.access_token:
            await concurrency_manager.run_in_thread(revoke_token, body.access_token)
        if body.refresh_token:
            await concurrency_manager.run_in_thread(revoke_token, body.refresh_token)

    await concurrency_manager.run_in_thread(svc.logout, user.id)
    return None
