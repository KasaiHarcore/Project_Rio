"""OAuth2 provider implementations (Google + GitHub).

Uses httpx (async HTTP client) to exchange authorization codes
for user information from Google and GitHub.

Usage:
    from infrastructure.security.oauth import get_oauth_provider

    provider = get_oauth_provider("google")
    url = provider.get_authorization_url(state="random-state-string")
    user_info = await provider.exchange_code(code="auth-code-from-callback")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field

from models.user import AuthProvider
from core.settings import get_oauth_config
from utils.log import log_info, log_error, log_debug, log_warning



class OAuthUserInfo(BaseModel):
    """Normalized user info returned by any OAuth2 provider."""

    provider: AuthProvider
    oauth_id: str = Field(..., description="Provider-specific user ID")
    email: str = Field(..., description="Email address from provider")
    name: str = Field(..., description="Display name from provider")
    avatar_url: Optional[str] = Field(None, description="Profile picture URL")



class OAuthProvider(ABC):
    """Base class for OAuth2 providers."""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Build the URL to redirect users to the provider's consent page."""
        ...

    @abstractmethod
    async def exchange_code(self, code: str) -> OAuthUserInfo:
        """Exchange an authorization code for user info.

        Raises:
            OAuthError: If the exchange or user-info fetch fails.
        """
        ...



class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth2 provider using Authorization Code flow."""

    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self) -> None:
        config = get_oauth_config()
        self._client_id = config.google_client_id or ""
        self._client_secret = config.google_client_secret or ""
        self._redirect_uri = f"{config.redirect_base_url}/auth/callback/google"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthUserInfo:
        from core.exceptions import OAuthError

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Exchange code for tokens
            token_resp = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                log_error(f"Google token exchange failed: {token_resp.text}")
                raise OAuthError(
                    "Failed to authenticate with Google",
                    details={"status": token_resp.status_code},
                )

            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                raise OAuthError("Google did not return an access token")

            config = get_oauth_config()
            if config.google_oidc_enabled:
                raw_id_token = tokens.get("id_token")
                if raw_id_token:
                    try:
                        from infrastructure.security.oidc import (
                            OIDCDiscovery,
                            validate_id_token,
                        )

                        jwks = await OIDCDiscovery.get_jwks(
                            cache_ttl=config.oidc_jwks_cache_ttl,
                        )
                        claims = validate_id_token(
                            id_token=raw_id_token,
                            client_id=self._client_id,
                            jwks=jwks,
                        )
                        if claims:
                            log_info(f"[OAuth] Google user (OIDC): {claims.get('email')}")
                            return OAuthUserInfo(
                                provider=AuthProvider.GOOGLE,
                                oauth_id=str(claims["sub"]),
                                email=claims["email"],
                                name=claims.get("name", claims.get("email", "Google User")),
                                avatar_url=claims.get("picture"),
                            )
                        log_debug("OIDC ID token validation failed, falling back to /userinfo")
                    except Exception as oidc_err:
                        log_warning(f"OIDC ID token parsing failed, falling back to /userinfo: {oidc_err}")

            userinfo_resp = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                log_error(f"Google userinfo failed: {userinfo_resp.text}")
                raise OAuthError("Failed to fetch Google user info")

            data = userinfo_resp.json()
            log_info(f"[OAuth] Google user: {data.get('email')}")

            return OAuthUserInfo(
                provider=AuthProvider.GOOGLE,
                oauth_id=str(data["id"]),
                email=data["email"],
                name=data.get("name", data.get("email", "Google User")),
                avatar_url=data.get("picture"),
            )



class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth2 provider using Authorization Code flow."""

    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USERINFO_URL = "https://api.github.com/user"
    EMAILS_URL = "https://api.github.com/user/emails"

    def __init__(self) -> None:
        config = get_oauth_config()
        self._client_id = config.github_client_id or ""
        self._client_secret = config.github_client_secret or ""
        self._redirect_uri = f"{config.redirect_base_url}/auth/callback/github"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": "user:email read:user",
            "state": state,
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthUserInfo:
        from core.exceptions import OAuthError

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Exchange code for access token
            token_resp = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            if token_resp.status_code != 200:
                log_error(f"GitHub token exchange failed: {token_resp.text}")
                raise OAuthError(
                    "Failed to authenticate with GitHub",
                    details={"status": token_resp.status_code},
                )

            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                error_desc = tokens.get("error_description", "Unknown error")
                raise OAuthError(f"GitHub auth failed: {error_desc}")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            }

            # Fetch user profile
            user_resp = await client.get(self.USERINFO_URL, headers=headers)
            if user_resp.status_code != 200:
                log_error(f"GitHub user fetch failed: {user_resp.text}")
                raise OAuthError("Failed to fetch GitHub user info")

            user_data = user_resp.json()

            # Fetch primary email (may not be in user profile)
            email = user_data.get("email")
            if not email:
                emails_resp = await client.get(self.EMAILS_URL, headers=headers)
                if emails_resp.status_code == 200:
                    for entry in emails_resp.json():
                        if entry.get("primary") and entry.get("verified"):
                            email = entry["email"]
                            break
            if not email:
                raise OAuthError("Could not retrieve email from GitHub")

            log_info(f"[OAuth] GitHub user: {email}")

            return OAuthUserInfo(
                provider=AuthProvider.GITHUB,
                oauth_id=str(user_data["id"]),
                email=email,
                name=user_data.get("name") or user_data.get("login", "GitHub User"),
                avatar_url=user_data.get("avatar_url"),
            )



_PROVIDERS: dict[str, type[OAuthProvider]] = {
    "google": GoogleOAuthProvider,
    "github": GitHubOAuthProvider,
}


def get_oauth_provider(provider_name: str) -> OAuthProvider:
    """Get an OAuth provider instance by name.

    Args:
        provider_name: 'google' or 'github'

    Raises:
        ValueError: If the provider name is unknown.
    """
    cls = _PROVIDERS.get(provider_name.lower())
    if cls is None:
        raise ValueError(f"Unknown OAuth provider: {provider_name}. Supported: {list(_PROVIDERS)}")
    return cls()
