"""OIDC discovery and ID token validation (Google).

Fetches the OpenID Connect discovery document, caches JWKS keys in Redis,
and validates ID tokens using RS256 verification — eliminating the extra
``/userinfo`` API call when the ID token is present.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from utils.log import log_debug, log_error, log_info, log_warning


# Google OIDC issuer URLs (both forms are valid per the spec)
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


class OIDCDiscovery:
    """Fetch and cache OIDC JWKS for a given issuer."""

    @classmethod
    async def get_jwks(
        cls,
        issuer_url: str = GOOGLE_DISCOVERY_URL,
        cache_ttl: int = 3600,
    ) -> List[Dict[str, Any]]:
        """Fetch JWKS keys, using Redis cache when available.

        Args:
            issuer_url: The OpenID Connect discovery document URL.
            cache_ttl: Redis cache TTL in seconds.

        Returns:
            List of JWK key dicts.
        """
        # Try Redis cache first
        cache_key = "jwks:google"
        try:
            from infrastructure.cache.redis_cache import redis_tool

            cached = redis_tool.cache_get_json(namespace="oidc", key=cache_key)
            if cached and isinstance(cached, list):
                log_debug("OIDC JWKS cache hit")
                return cached
        except Exception as e:
            log_debug(f"OIDC JWKS cache miss or error: {e}")

        # Fetch discovery document
        async with httpx.AsyncClient(timeout=10.0) as client:
            discovery_resp = await client.get(issuer_url)
            discovery_resp.raise_for_status()
            discovery = discovery_resp.json()

            jwks_uri = discovery.get("jwks_uri")
            if not jwks_uri:
                log_error("OIDC discovery document missing jwks_uri")
                return []

            jwks_resp = await client.get(jwks_uri)
            jwks_resp.raise_for_status()
            jwks_data = jwks_resp.json()

        keys: List[Dict[str, Any]] = jwks_data.get("keys", [])

        # Cache in Redis
        try:
            from infrastructure.cache.redis_cache import redis_tool

            redis_tool.cache_set_json(
                namespace="oidc",
                key=cache_key,
                value=keys,
                ttl_seconds=cache_ttl,
            )
            log_debug(f"Cached {len(keys)} OIDC JWKS keys (TTL={cache_ttl}s)")
        except Exception as e:
            log_warning(f"Failed to cache OIDC JWKS: {e}")

        return keys


def validate_id_token(
    id_token: str,
    client_id: str,
    jwks: List[Dict[str, Any]],
    issuer: str = "https://accounts.google.com",
) -> Optional[Dict[str, Any]]:
    """Validate and decode a Google OIDC ID token.

    Args:
        id_token: The raw JWT ID token string.
        client_id: Expected ``aud`` claim (OAuth client ID).
        jwks: List of JWK key dicts from the OIDC provider.
        issuer: Expected ``iss`` claim.

    Returns:
        Decoded claims dict on success, ``None`` on any failure.
    """
    try:
        # Decode header to find the key ID
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")
        if not kid:
            log_warning("ID token missing kid header")
            return None

        # Find matching key in JWKS
        matching_key = None
        for key in jwks:
            if key.get("kid") == kid:
                matching_key = key
                break

        if not matching_key:
            log_warning(f"No matching JWK found for kid={kid}")
            return None

        # Convert JWK to RSA public key
        public_key = RSAAlgorithm.from_jwk(matching_key)

        # Verify and decode — accept both Google issuer formats
        claims = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=list(GOOGLE_ISSUERS) if issuer in GOOGLE_ISSUERS else issuer,
        )

        log_info(f"[OIDC] ID token validated for sub={claims.get('sub')}")
        return claims

    except jwt.ExpiredSignatureError:
        log_warning("OIDC ID token has expired")
        return None
    except jwt.InvalidTokenError as e:
        log_warning(f"OIDC ID token validation failed: {e}")
        return None
    except Exception as e:
        log_error(f"Unexpected error validating OIDC ID token: {e}")
        return None
