"""Custom exception types for consistent error handling."""
from typing import Any, Optional


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize exception.
        
        Args:
            message: Error message
            error_code: Optional error code
            details: Optional additional details
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(AppException):
    """Database operation error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, error_code="NOT_FOUND", details=details)


class DuplicateError(AppException):
    """Duplicate resource error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, error_code="DUPLICATE", details=details)


class ValidationError(AppException):
    """Input validation error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class AuthenticationError(AppException):
    """Authentication error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", details=details)


class AuthorizationError(AppException):
    """Authorization error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", details=details)


class ConfigurationError(AppException):
    """Configuration error."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)
