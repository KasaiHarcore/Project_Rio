"""JWT configuration and settings."""

import os
import secrets

from utils.log import log_warning

# JWT Algorithm
JWT_ALGORITHM = "HS256"

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Secret key for signing tokens
_env_secret = os.getenv("JWT_SECRET_KEY")

if _env_secret:
    JWT_SECRET_KEY: str = _env_secret
else:
    JWT_SECRET_KEY = secrets.token_urlsafe(32)
    log_warning(
        "JWT_SECRET_KEY is NOT set – using a random ephemeral key. "
        "All tokens will be invalidated on restart. "
        "Set JWT_SECRET_KEY env var before deploying to production!"
    )

# Token type identifier
TOKEN_TYPE = "bearer"
