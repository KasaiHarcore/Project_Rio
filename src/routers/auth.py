"""Authentication, OAuth, and JWKS endpoints.

Auth provides:
    POST /auth/login          - authenticate and return JWT token pair
    POST /auth/register       - create a new user account
    GET  /auth/me             - return current user profile
    POST /auth/refresh        - exchange refresh token for new access token
    POST /auth/reset-password - reset authenticated user's password
    POST /auth/logout         - revoke tokens and log out

OAuth provides:
    GET  /auth/oauth/{provider}           - redirect to consent page
    GET  /auth/oauth/{provider}/callback  - exchange code, return JWT

JWKS provides:
    GET  /.well-known/jwks.json - public key distribution

Security measures:
- Rate limiting on public endpoints (login, register) via Redis sliding window
- Password reset requires authentication (user must be logged in)
- Logout revokes tokens server-side via Redis blacklist
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_auth_service, get_cache_service
from core.exceptions import (
    AuthenticationError,
    DuplicateError,
    ExternalServiceError,
    OAuthError,
    ValidationError,
)
from core.settings import get_oauth_config
from infrastructure.cache.helpers import best_effort
from infrastructure.cache.service import CacheService
from infrastructure.security.auth import (
    TokenPair,
    create_token_pair,
    refresh_access_token,
    revoke_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from infrastructure.security.jwt_config import JWT_ALGORITHM, JWT_VERIFY_KEY
from infrastructure.security.oauth import get_oauth_provider, OAuthUserInfo
from infrastructure.security.rate_limiter import RedisRateLimiter
from models.user import AuthProvider, User
from schemas.user import UserInDB, OAuthLoginResponse, TokenPairSchema
from services.auth_service import AuthService
from utils.log import log_error


# ---------------------------------------------------------------------------
# Auth router
# ---------------------------------------------------------------------------

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

    Requires a valid access token -- the user resets their **own** password.
    """
    success, error = await concurrency_manager.run_in_thread(
        svc.reset_password, user.username, body.new_password
    )

    if not success:
        raise ValidationError(error or "Password reset failed")

    # Invalidate cached user data
    best_effort(cache.invalidate_user, str(user.id))

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


# ---------------------------------------------------------------------------
# OAuth router  (was oauth.py)
# ---------------------------------------------------------------------------

oauth_router = APIRouter(prefix="/auth/oauth", tags=["auth"])


class OAuthCallbackResponse(BaseModel):
    """Response returned by the callback endpoint."""
    success: bool = True
    user: UserInDB
    tokens: TokenPairSchema
    is_new_user: bool = False


@oauth_router.get("/{provider}")
async def oauth_redirect(provider: str):
    """Redirect the user to the OAuth provider's consent page.

    Supported providers: ``google``, ``github``.
    """
    config = get_oauth_config()

    if provider == "google" and not config.google_enabled:
        raise ValidationError("Google OAuth is not configured")
    if provider == "github" and not config.github_enabled:
        raise ValidationError("GitHub OAuth is not configured")

    try:
        oauth = get_oauth_provider(provider)
    except ValueError:
        raise ValidationError(f"Unknown provider: {provider}")

    state = secrets.token_urlsafe(32)
    url = oauth.get_authorization_url(state=state)
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@oauth_router.get("/{provider}/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="Authorization code from provider"),
    state: Optional[str] = Query(None, description="CSRF state token"),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """Exchange the authorization code for user info and return JWT tokens.

    If the email is already registered:
    - If same provider: log in as that user
    - If different provider (e.g. local): link accounts by updating auth_provider

    If the email is new: create a new user account.
    """
    try:
        oauth = get_oauth_provider(provider)
    except ValueError:
        raise ValidationError(f"Unknown provider: {provider}")

    # Exchange code for user info from the provider
    try:
        user_info: OAuthUserInfo = await oauth.exchange_code(code)
    except OAuthError:
        raise
    except Exception as exc:
        log_error(f"OAuth exchange error: {exc}")
        raise ExternalServiceError("OAuth provider error")

    # Resolve user via AuthService
    auth_provider_enum = AuthProvider(user_info.provider.value)
    user, is_new_user = auth_svc.get_or_create_oauth_user(
        oauth_id=user_info.oauth_id,
        provider=auth_provider_enum,
        email=user_info.email,
        name=user_info.name,
        avatar_url=user_info.avatar_url,
    )

    # Generate JWT tokens
    token_pair = create_token_pair(str(user.id), user.role.value)

    user_data = UserInDB.model_validate(user)
    return OAuthCallbackResponse(
        user=user_data,
        tokens=TokenPairSchema(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
        is_new_user=is_new_user,
    )


# ---------------------------------------------------------------------------
# JWKS router  (was jwks.py)
# ---------------------------------------------------------------------------

jwks_router = APIRouter(tags=["jwks"])


def _int_to_base64url(n: int) -> str:
    """Encode an arbitrary-size integer as Base64url (no padding)."""
    byte_length = (n.bit_length() + 7) // 8
    raw = n.to_bytes(byte_length, byteorder="big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _build_jwk() -> Dict[str, Any]:
    """Build a JWK dict from the current RSA public key."""
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    pub_numbers = JWT_VERIFY_KEY.public_numbers()

    # kid = SHA-256 of the DER-encoded public key
    der_bytes = JWT_VERIFY_KEY.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    kid = hashlib.sha256(der_bytes).hexdigest()

    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _int_to_base64url(pub_numbers.n),
        "e": _int_to_base64url(pub_numbers.e),
    }


_CACHED_JWKS: Dict[str, List[Dict[str, Any]]] | None = None


@jwks_router.get("/.well-known/jwks.json")
async def jwks_endpoint() -> Dict[str, List[Dict[str, Any]]]:
    """Return the JSON Web Key Set for public key verification."""
    global _CACHED_JWKS
    if _CACHED_JWKS is None:
        if JWT_ALGORITHM == "RS256":
            _CACHED_JWKS = {"keys": [_build_jwk()]}
        else:
            _CACHED_JWKS = {"keys": []}
    return _CACHED_JWKS
