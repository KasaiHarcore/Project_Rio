"""OAuth2 endpoints: Google and GitHub login/callback.

Provides:
    GET  /auth/oauth/{provider}           → redirect to consent page
    GET  /auth/oauth/{provider}/callback  → exchange code, return JWT
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from core.dependencies import get_auth_service
from core.exceptions import OAuthError, ValidationError, ExternalServiceError
from core.settings import get_oauth_config
from models.user import AuthProvider
from schemas.user import UserInDB, OAuthLoginResponse, TokenPairSchema
from services.auth_service import AuthService
from infrastructure.security.auth import create_token_pair, ACCESS_TOKEN_EXPIRE_MINUTES
from infrastructure.security.oauth import get_oauth_provider, OAuthUserInfo
from utils.log import log_error

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])



@router.get("/{provider}")
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
