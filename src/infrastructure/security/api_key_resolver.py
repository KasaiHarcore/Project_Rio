"""
API Key Resolution with Fallback

Resolves API keys from user settings (decrypted) with fallback to environment variables.
Priority: User settings > Environment variables
"""

import os
from typing import Optional

from infrastructure.security.encryption import decrypt_api_key
from utils.log import log_debug, log_warning


class ApiKeyResolver:
    """
    Resolves API keys with priority: user settings → environment variables.

    Usage:
        resolver = ApiKeyResolver(user_settings)
        openai_key = resolver.get_openai_key()
    """

    def __init__(self, user_settings: Optional[object] = None):
        """
        Initialize resolver with user settings.

        Args:
            user_settings: UserSettings model instance with encrypted API keys
        """
        self.user_settings = user_settings

    def get_openai_key(self) -> Optional[str]:
        """
        Get OpenAI API key with fallback.

        Returns:
            API key string or None if not configured anywhere
        """
        if self.user_settings and self.user_settings.encrypted_openai_key:
            decrypted = decrypt_api_key(self.user_settings.encrypted_openai_key)
            if decrypted:
                log_debug("Using OpenAI API key from user settings")
                return decrypted
            log_warning("Failed to decrypt user's OpenAI key, falling back to env var")

        env_key = os.getenv("OPENAI_API_KEY")
        if env_key:
            log_debug("Using OpenAI API key from environment variable")
            return env_key

        log_warning("OpenAI API key not configured in user settings or environment")
        return None

    def get_openrouter_key(self) -> Optional[str]:
        """
        Get OpenRouter API key with fallback.

        Returns:
            API key string or None if not configured anywhere
        """
        if self.user_settings and self.user_settings.encrypted_openrouter_key:
            decrypted = decrypt_api_key(self.user_settings.encrypted_openrouter_key)
            if decrypted:
                log_debug("Using OpenRouter API key from user settings")
                return decrypted
            log_warning("Failed to decrypt user's OpenRouter key, falling back to env var")

        env_key = os.getenv("OPENROUTER_API_KEY")
        if env_key:
            log_debug("Using OpenRouter API key from environment variable")
            return env_key

        log_warning("OpenRouter API key not configured in user settings or environment")
        return None

    def get_tavily_key(self) -> Optional[str]:
        """
        Get Tavily API key with fallback.

        Returns:
            API key string or None if not configured anywhere
        """
        if self.user_settings and self.user_settings.encrypted_tavily_key:
            decrypted = decrypt_api_key(self.user_settings.encrypted_tavily_key)
            if decrypted:
                log_debug("Using Tavily API key from user settings")
                return decrypted
            log_warning("Failed to decrypt user's Tavily key, falling back to env var")

        env_key = os.getenv("TAVILY_API_KEY")
        if env_key:
            log_debug("Using Tavily API key from environment variable")
            return env_key

        log_warning("Tavily API key not configured in user settings or environment")
        return None

    def get_cohere_key(self) -> Optional[str]:
        """
        Get Cohere API key with fallback.

        Returns:
            API key string or None if not configured anywhere
        """
        if self.user_settings and self.user_settings.encrypted_cohere_key:
            decrypted = decrypt_api_key(self.user_settings.encrypted_cohere_key)
            if decrypted:
                log_debug("Using Cohere API key from user settings")
                return decrypted
            log_warning("Failed to decrypt user's Cohere key, falling back to env var")

        env_key = os.getenv("COHERE_API_KEY")
        if env_key:
            log_debug("Using Cohere API key from environment variable")
            return env_key

        log_warning("Cohere API key not configured in user settings or environment")
        return None

    def get_langsmith_key(self) -> Optional[str]:
        """Get LangSmith API key with fallback."""
        if self.user_settings and self.user_settings.encrypted_langsmith_key:
            decrypted = decrypt_api_key(self.user_settings.encrypted_langsmith_key)
            if decrypted:
                log_debug("Using LangSmith API key from user settings")
                return decrypted
            log_warning("Failed to decrypt user's LangSmith key, falling back to env var")

        env_key = os.getenv("LANGSMITH_API_KEY")
        if env_key:
            log_debug("Using LangSmith API key from environment variable")
            return env_key

        return None

    def has_openai_key(self) -> bool:
        """Check if OpenAI key is available (without decrypting)."""
        return bool(
            (self.user_settings and self.user_settings.encrypted_openai_key)
            or os.getenv("OPENAI_API_KEY")
        )

    def has_openrouter_key(self) -> bool:
        """Check if OpenRouter key is available (without decrypting)."""
        return bool(
            (self.user_settings and self.user_settings.encrypted_openrouter_key)
            or os.getenv("OPENROUTER_API_KEY")
        )

    def has_tavily_key(self) -> bool:
        """Check if Tavily key is available (without decrypting)."""
        return bool(
            (self.user_settings and self.user_settings.encrypted_tavily_key)
            or os.getenv("TAVILY_API_KEY")
        )

    def has_cohere_key(self) -> bool:
        """Check if Cohere key is available (without decrypting)."""
        return bool(
            (self.user_settings and self.user_settings.encrypted_cohere_key)
            or os.getenv("COHERE_API_KEY")
        )


def get_api_key_for_provider(provider: str, user_settings: Optional[object] = None) -> Optional[str]:
    """
    Convenience function to get API key for a provider.

    Args:
        provider: Provider name ('openai', 'openrouter', 'tavily', 'cohere')
        user_settings: Optional UserSettings model instance

    Returns:
        API key string or None
    """
    resolver = ApiKeyResolver(user_settings)
    provider_lower = provider.lower()

    if provider_lower == "openai":
        return resolver.get_openai_key()
    elif provider_lower == "openrouter":
        return resolver.get_openrouter_key()
    elif provider_lower == "tavily":
        return resolver.get_tavily_key()
    elif provider_lower == "cohere":
        return resolver.get_cohere_key()
    else:
        log_warning(f"Unknown provider: {provider}")
        return None
