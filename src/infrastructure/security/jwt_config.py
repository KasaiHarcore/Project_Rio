"""JWT configuration and settings.

Supports both HS256 (symmetric) and RS256 (asymmetric) signing algorithms.
RS256 uses RSA key pairs for enhanced security in distributed environments.

Migration:
  1. Deploy with JWT_ALGORITHM=HS256 (default, no behavior change)
  2. Generate RSA key pair, set JWT_PRIVATE_KEY + JWT_PUBLIC_KEY env vars
  3. Switch JWT_ALGORITHM=RS256 with JWT_LEGACY_HS256_VERIFY=true
  4. After 7 days (max refresh TTL), set JWT_LEGACY_HS256_VERIFY=false
"""

import os
import secrets

from utils.log import log_warning, log_info

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Token type identifier
TOKEN_TYPE = "bearer"

# JWT Algorithm — "HS256" (symmetric) or "RS256" (asymmetric)
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256").upper()
if JWT_ALGORITHM not in ("HS256", "RS256"):
    raise ValueError(f"Unsupported JWT_ALGORITHM: {JWT_ALGORITHM}. Must be HS256 or RS256.")

# Accept old HS256 tokens during RS256 migration period
JWT_LEGACY_HS256_VERIFY: bool = os.getenv("JWT_LEGACY_HS256_VERIFY", "true").lower() == "true"


def _load_pem_key(env_value: str) -> bytes:
    """Load a PEM key from an inline string or file path."""
    stripped = env_value.strip()
    if stripped.startswith("-----"):
        return stripped.encode("utf-8")
    # Treat as file path
    path = os.path.expanduser(stripped)
    with open(path, "rb") as f:
        return f.read()


# ── HS256 secret (always loaded for legacy fallback) ─────────────────────

_env_secret = os.getenv("JWT_SECRET_KEY")

if _env_secret:
    JWT_SECRET_KEY: str = _env_secret
else:
    JWT_SECRET_KEY = secrets.token_urlsafe(32)
    log_warning(
        "JWT_SECRET_KEY is NOT set - using a random ephemeral key. "
        "All tokens will be invalidated on restart. "
        "Set JWT_SECRET_KEY env var before deploying to production!"
    )

# ── Algorithm-aware signing / verification keys ─────────────────────────

if JWT_ALGORITHM == "RS256":
    _private_key_env = os.getenv("JWT_PRIVATE_KEY")
    _public_key_env = os.getenv("JWT_PUBLIC_KEY")

    if _private_key_env and _public_key_env:
        from cryptography.hazmat.primitives.serialization import (
            load_pem_private_key,
            load_pem_public_key,
        )

        _private_pem = _load_pem_key(_private_key_env)
        _public_pem = _load_pem_key(_public_key_env)
        JWT_SIGNING_KEY = load_pem_private_key(_private_pem, password=None)
        JWT_VERIFY_KEY = load_pem_public_key(_public_pem)
        log_info("JWT RS256: loaded RSA key pair from environment")
    else:
        # Dev mode: generate ephemeral RSA 2048-bit key pair
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
            PublicFormat,
        )

        _ephemeral_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        JWT_SIGNING_KEY = _ephemeral_key
        JWT_VERIFY_KEY = _ephemeral_key.public_key()
        log_warning(
            "JWT RS256: JWT_PRIVATE_KEY / JWT_PUBLIC_KEY not set - "
            "using ephemeral RSA key pair. All tokens will be "
            "invalidated on restart. Set env vars for production!"
        )
else:
    # HS256 — symmetric key for both signing and verification
    JWT_SIGNING_KEY = JWT_SECRET_KEY  # type: ignore[assignment]
    JWT_VERIFY_KEY = JWT_SECRET_KEY  # type: ignore[assignment]
