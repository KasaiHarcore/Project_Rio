"""OAuth2 endpoints: Google and GitHub login/callback.

Provides:
    GET  /auth/oauth/{provider}           → redirect to consent page
    GET  /auth/oauth/{provider}/callback  → exchange code, return JWT
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.dependencies import get_db
from core.exceptions import OAuthError
from core.settings import get_oauth_config
from models.user import User, UserRole, AuthProvider
from schemas.user import UserInDB, OAuthLoginResponse, TokenPairSchema
from infrastructure.security.auth import create_token_pair, ACCESS_TOKEN_EXPIRE_MINUTES
from infrastructure.security.oauth import get_oauth_provider, OAuthUserInfo
from utils.log import log_info, log_error, log_warning

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


# ── Redirect to provider ───────────────────────────────────────────────────

@router.get("/{provider}")
async def oauth_redirect(provider: str):
    """Redirect the user to the OAuth provider's consent page.

    Supported providers: ``google``, ``github``.
    """
    config = get_oauth_config()

    if provider == "google" and not config.google_enabled:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Google OAuth is not configured")
    if provider == "github" and not config.github_enabled:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "GitHub OAuth is not configured")

    try:
        oauth = get_oauth_provider(provider)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown provider: {provider}")

    state = secrets.token_urlsafe(32)
    url = oauth.get_authorization_url(state=state)
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


# ── Callback ───────────────────────────────────────────────────────────────

class OAuthCallbackResponse(BaseModel):
    """Response returned by the callback endpoint."""
    success: bool = True
    user: UserInDB
    tokens: TokenPairSchema
    is_new_user: bool = False


@router.get("/{provider}/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="Authorization code from provider"),
    state: Optional[str] = Query(None, description="CSRF state token"),
    db: Session = Depends(get_db),
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
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown provider: {provider}")

    # Exchange code for user info from the provider
    try:
        user_info: OAuthUserInfo = await oauth.exchange_code(code)
    except OAuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    except Exception as exc:
        log_error(f"OAuth exchange error: {exc}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "OAuth provider error")

    # Resolve user
    is_new_user = False
    auth_provider_enum = AuthProvider(user_info.provider.value)

    # Check if user exists by oauth_id + provider
    user = (
        db.query(User)
        .filter(User.oauth_id == user_info.oauth_id, User.auth_provider == auth_provider_enum)
        .first()
    )

    if not user:
        # Check by email (account linking)
        user = db.query(User).filter(User.email == user_info.email).first()
        if user:
            # Link existing local account to this OAuth provider
            log_info(f"[OAuth] Linking {user_info.email} to {provider}")
            user.auth_provider = auth_provider_enum
            user.oauth_id = user_info.oauth_id
            if user_info.avatar_url and not user.avatar_url:
                user.avatar_url = user_info.avatar_url
            db.commit()
            db.refresh(user)
        else:
            # Create new user
            log_info(f"[OAuth] Creating new user: {user_info.email} via {provider}")
            username = _generate_username(db, user_info.name, user_info.email)
            user = User(
                username=username,
                email=user_info.email,
                hashed_password=None,  # OAuth users have no password
                role=UserRole.USER,
                auth_provider=auth_provider_enum,
                oauth_id=user_info.oauth_id,
                avatar_url=user_info.avatar_url,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            is_new_user = True

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


# ── Helpers ─────────────────────────────────────────────────────────────────

def _generate_username(db: Session, name: str, email: str) -> str:
    """Generate a unique username from the OAuth display name or email."""
    base = name.lower().replace(" ", "_")[:50] if name else email.split("@")[0]
    # Remove non-alphanumeric characters except underscore
    base = "".join(c for c in base if c.isalnum() or c == "_")
    if not base:
        base = "user"

    username = base
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base}_{counter}"
        counter += 1

    return username
