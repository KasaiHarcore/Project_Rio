"""Authentication helpers and token validation utilities."""

from passlib.context import CryptContext
from typing import Optional
from datetime import datetime, timedelta
from backend.utils.log import log_debug, log_error

# Password hashing context using Argon2 (preferred) with bcrypt fallback
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        log_error(f"Error verifying password: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password for storing using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)
