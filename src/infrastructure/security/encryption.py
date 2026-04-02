"""
API Key Encryption Utility

Provides Fernet-based symmetric encryption for securely storing API keys in the database.
Uses AES-128 with HMAC authentication for strong security guarantees.
"""

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from utils.log import log_warning, log_error, log_info


class EncryptionService:
    """Service for encrypting and decrypting sensitive data like API keys."""

    def __init__(self):
        """Initialize encryption service with key from environment."""
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            log_warning(
                "ENCRYPTION_KEY not set in environment. API key encryption disabled. "
                "Generate key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
            self._cipher = None
        else:
            try:
                self._cipher = Fernet(encryption_key.encode())
            except Exception as e:
                log_error(f"Failed to initialize encryption cipher: {e}")
                self._cipher = None

    def encrypt_api_key(self, plaintext_key: Optional[str]) -> Optional[str]:
        """
        Encrypt an API key for secure storage.

        Args:
            plaintext_key: The API key to encrypt (e.g., "sk-...")

        Returns:
            Base64-encoded encrypted string, or None if encryption fails or key is None
        """
        if not plaintext_key:
            return None

        if not self._cipher:
            log_warning("Cannot encrypt API key: encryption not configured")
            return None

        try:
            encrypted_bytes = self._cipher.encrypt(plaintext_key.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            log_error(f"Failed to encrypt API key: {e}")
            return None

    def decrypt_api_key(self, encrypted_key: Optional[str]) -> Optional[str]:
        """
        Decrypt an API key for use.

        Args:
            encrypted_key: Base64-encoded encrypted string from database

        Returns:
            Decrypted API key string, or None if decryption fails or key is None
        """
        if not encrypted_key:
            return None

        if not self._cipher:
            log_warning("Cannot decrypt API key: encryption not configured")
            return None

        try:
            decrypted_bytes = self._cipher.decrypt(encrypted_key.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            log_error("Failed to decrypt API key: invalid token or wrong encryption key")
            return None
        except Exception as e:
            log_error(f"Failed to decrypt API key: {e}")
            return None

    def mask_api_key(self, plaintext_key: Optional[str]) -> str:
        """
        Mask an API key for display purposes (show first 3 + last 4 characters).

        Args:
            plaintext_key: The API key to mask

        Returns:
            Masked string like "sk-...xyz123" or "Not configured"
        """
        if not plaintext_key:
            return "Not configured"

        if len(plaintext_key) <= 7:
            # Too short to safely mask
            return "***"

        # Show first 3 and last 4 characters
        return f"{plaintext_key[:3]}...{plaintext_key[-4:]}"

    @property
    def is_configured(self) -> bool:
        """Check if encryption is properly configured."""
        return self._cipher is not None


# Global singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Convenience functions for backward compatibility
def encrypt_api_key(plaintext_key: Optional[str]) -> Optional[str]:
    """Encrypt an API key. See EncryptionService.encrypt_api_key()."""
    return get_encryption_service().encrypt_api_key(plaintext_key)


def decrypt_api_key(encrypted_key: Optional[str]) -> Optional[str]:
    """Decrypt an API key. See EncryptionService.decrypt_api_key()."""
    return get_encryption_service().decrypt_api_key(encrypted_key)


def mask_api_key(plaintext_key: Optional[str]) -> str:
    """Mask an API key for display. See EncryptionService.mask_api_key()."""
    return get_encryption_service().mask_api_key(plaintext_key)
