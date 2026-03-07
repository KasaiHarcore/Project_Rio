"""Settings service for managing user settings and profile."""

from typing import Optional, Tuple, Dict
from uuid import UUID

from models.user_settings import UserSettings
from models.user_profile import UserProfile
from schemas.user import UserProfileUpdate
from schemas.user_settings import (
    UserSettingsBase,
    UserSettingsUpdate,
    UserSettingsInDB,
    UserSettingsAPIStatus,
)
from repositories.settings_repository import SettingsRepository
from repositories.user_repository import UserRepository
from repositories.user_profile_repository import UserProfileRepository
from infrastructure.security.encryption import encrypt_api_key, decrypt_api_key, mask_api_key
from utils.log import log_info, log_error, log_warning, log_debug


class SettingsService:
    """Service for managing user settings and profile."""

    def __init__(
        self,
        settings_repo: SettingsRepository,
        user_repo: UserRepository,
        profile_repo: UserProfileRepository,
    ) -> None:
        self._settings_repo = settings_repo
        self._user_repo = user_repo
        self._profile_repo = profile_repo

    def get_or_create_settings(self, user_id: UUID) -> UserSettings:
        """Get user settings, creating with defaults if not exists.

        Args:
            user_id: User UUID

        Returns:
            UserSettings instance
        """
        settings = self._settings_repo.get_or_create(user_id)
        log_info(f"Loaded/created settings for user {user_id}")
        return settings

    def update_settings(
        self,
        user_id: UUID,
        updates: UserSettingsUpdate,
    ) -> Tuple[bool, Optional[UserSettingsInDB], Optional[str]]:
        """Update user settings.

        Args:
            user_id: User UUID
            updates: Settings update payload

        Returns:
            Tuple of (success, settings_data, error_message)
        """
        try:
            settings = self._settings_repo.get_or_create(user_id)

            # Apply updates
            update_data = updates.model_dump(exclude_unset=True)

            # Handle API key encryption
            api_key_mapping = {
                "openai_api_key": "encrypted_openai_key",
                "openrouter_api_key": "encrypted_openrouter_key",
                "tavily_api_key": "encrypted_tavily_key",
                "cohere_api_key": "encrypted_cohere_key",
            }

            for plaintext_field, encrypted_field in api_key_mapping.items():
                if plaintext_field in update_data:
                    plaintext_key = update_data.pop(plaintext_field)
                    if plaintext_key:
                        encrypted = encrypt_api_key(plaintext_key)
                        if encrypted:
                            setattr(settings, encrypted_field, encrypted)
                            log_debug(f"Encrypted {plaintext_field} for user {user_id}")
                        else:
                            log_warning(f"Failed to encrypt {plaintext_field}, skipping")
                    else:
                        # Empty string or None - clear the key
                        setattr(settings, encrypted_field, None)
                        log_debug(f"Cleared {plaintext_field} for user {user_id}")

            # Apply remaining updates (non-API-key fields)
            for key, value in update_data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

            self._settings_repo.flush()

            settings_data = self._to_settings_response(settings)
            log_info(f"Updated settings for user {user_id}")
            return True, settings_data, None

        except Exception as e:
            error_msg = f"Failed to update settings: {str(e)}"
            log_error(error_msg)
            return False, None, error_msg

    def get_settings(self, user_id: UUID) -> UserSettingsInDB:
        """Get user settings (creates with defaults if not exists).

        Args:
            user_id: User UUID

        Returns:
            UserSettingsInDB instance with API key status (not actual keys)
        """
        settings = self._settings_repo.get_or_create(user_id)
        return self._to_settings_response(settings)

    def _to_settings_response(self, settings: UserSettings) -> UserSettingsInDB:
        """Convert UserSettings model to response schema with API key status.

        Args:
            settings: UserSettings model instance

        Returns:
            UserSettingsInDB with API key status (never actual keys)
        """
        # Decrypt keys for masking (but don't expose them)
        openai_key = decrypt_api_key(settings.encrypted_openai_key) if settings.encrypted_openai_key else None
        openrouter_key = decrypt_api_key(settings.encrypted_openrouter_key) if settings.encrypted_openrouter_key else None
        tavily_key = decrypt_api_key(settings.encrypted_tavily_key) if settings.encrypted_tavily_key else None
        cohere_key = decrypt_api_key(settings.encrypted_cohere_key) if settings.encrypted_cohere_key else None

        # Create API key status
        api_status = UserSettingsAPIStatus(
            openai_configured=openai_key is not None,
            openrouter_configured=openrouter_key is not None,
            tavily_configured=tavily_key is not None,
            cohere_configured=cohere_key is not None,
            openai_masked=mask_api_key(openai_key) if openai_key else None,
            openrouter_masked=mask_api_key(openrouter_key) if openrouter_key else None,
            tavily_masked=mask_api_key(tavily_key) if tavily_key else None,
            cohere_masked=mask_api_key(cohere_key) if cohere_key else None,
        )

        # Convert to dict and add API status
        settings_dict = {
            "id": settings.id,
            "user_id": settings.user_id,
            "created_at": settings.created_at,
            "updated_at": settings.updated_at,
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
            "top_p": settings.top_p,
            "frequency_penalty": settings.frequency_penalty,
            "presence_penalty": settings.presence_penalty,
            "system_prompt": settings.system_prompt,
            "model_name": settings.model_name,
            "max_iterations": settings.max_iterations,
            "top_k": settings.top_k,
            "enable_planner": settings.enable_planner,
            "enable_reflection": settings.enable_reflection,
            "mission_reminders": settings.mission_reminders,
            "chat_alerts": settings.chat_alerts,
            "system_updates": settings.system_updates,
            "weekly_summary": settings.weekly_summary,
            "error_alerts": settings.error_alerts,
            "sound_enabled": settings.sound_enabled,
            "email_notifications": settings.email_notifications,
            "api_keys": api_status,
        }

        return UserSettingsInDB(**settings_dict)

    def get_decrypted_api_keys(self, user_id: UUID) -> Dict[str, Optional[str]]:
        """Get decrypted API keys for internal use (e.g., LLM initialization).

        SECURITY: Only use this method internally. Never expose these keys in API responses.

        Args:
            user_id: User UUID

        Returns:
            Dict with decrypted API keys: {
                "openai": str | None,
                "openrouter": str | None,
                "tavily": str | None,
                "cohere": str | None
            }
        """
        settings = self._settings_repo.get_or_create(user_id)

        return {
            "openai": decrypt_api_key(settings.encrypted_openai_key) if settings.encrypted_openai_key else None,
            "openrouter": decrypt_api_key(settings.encrypted_openrouter_key) if settings.encrypted_openrouter_key else None,
            "tavily": decrypt_api_key(settings.encrypted_tavily_key) if settings.encrypted_tavily_key else None,
            "cohere": decrypt_api_key(settings.encrypted_cohere_key) if settings.encrypted_cohere_key else None,
        }

    def get_or_create_profile(self, user_id: UUID) -> UserProfile:
        """Get user profile, creating if not exists.

        Args:
            user_id: User UUID

        Returns:
            UserProfile instance
        """
        profile = self._profile_repo.get_or_create(user_id)
        return profile

    def update_profile(
        self,
        user_id: UUID,
        updates: UserProfileUpdate,
    ) -> Tuple[bool, Optional[str]]:
        """Update user profile.

        Args:
            user_id: User UUID
            updates: Profile update payload

        Returns:
            Tuple of (success, error_message)
        """
        try:
            profile = self._profile_repo.get_or_create(user_id)

            # Apply updates
            update_data = updates.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            self._profile_repo.flush()
            log_info(f"Updated profile for user {user_id}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to update profile: {str(e)}"
            log_error(error_msg)
            return False, error_msg

    def update_user_info(
        self,
        user_id: UUID,
        username: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Update basic user information (username, email).

        Args:
            user_id: User UUID
            username: New username (optional)
            email: New email (optional)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user = self._user_repo.find_by_id(user_id)
            if not user:
                return False, "User not found"

            if username:
                # Check if username is already taken
                if self._user_repo.username_exists(username, exclude_id=user_id):
                    return False, "Username already taken"
                user.username = username

            if email:
                # Check if email is already taken
                if self._user_repo.email_exists(email, exclude_id=user_id):
                    return False, "Email already taken"
                user.email = email

            self._user_repo.flush()
            log_info(f"Updated user info for user {user_id}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to update user info: {str(e)}"
            log_error(error_msg)
            return False, error_msg
