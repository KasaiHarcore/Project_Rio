"""JWT configuration and settings."""

import os
import secrets
from typing import Optional

# JWT Algorithm
JWT_ALGORITHM = "HS256"

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Secret key for signing tokens
# In production, set JWT_SECRET_KEY environment variable
_default_secret = secrets.token_urlsafe(32)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", _default_secret)

# Token type identifier
TOKEN_TYPE = "bearer"


def get_secret_key() -> str:
    """Get the JWT secret key, generating if needed."""
    return JWT_SECRET_KEY
