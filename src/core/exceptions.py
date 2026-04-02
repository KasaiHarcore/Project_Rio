"""Custom Exception Types for Consistent Error Handling.

This module defines a hierarchy of application-specific exceptions
that provide:
- Consistent error codes for API responses
- Structured error details for debugging
- Clear separation of error categories

Exception Hierarchy:
    AppException (base)
    ├── DatabaseError
    ├── NotFoundError
    ├── DuplicateError
    ├── ValidationError
    ├── AuthenticationError
    ├── AuthorizationError
    └── ConfigurationError
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception.
    
    All custom exceptions inherit from this class to ensure
    consistent error handling across the application.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code for API responses
            details: Additional context for debugging
        """
        self.message = message
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class DatabaseError(AppException):
    """Database operation error.
    
    Raised when database operations fail (connection, query, transaction).
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class NotFoundError(AppException):
    """Resource not found error.
    
    Raised when a requested resource does not exist.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="NOT_FOUND", details=details)


class DuplicateError(AppException):
    """Duplicate resource error.
    
    Raised when attempting to create a resource that already exists.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="DUPLICATE", details=details)


class ValidationError(AppException):
    """Input validation error.
    
    Raised when input data fails validation rules.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class AuthenticationError(AppException):
    """Authentication error.
    
    Raised when authentication fails (invalid credentials, expired token).
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", details=details)


class AuthorizationError(AppException):
    """Authorization error.
    
    Raised when user lacks permission for an action.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", details=details)


class ConfigurationError(AppException):
    """Configuration error.
    
    Raised when application configuration is invalid or missing.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


class WorkflowError(AppException):
    """Workflow execution error.
    
    Raised when workflow execution fails.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="WORKFLOW_ERROR", details=details)


class ExternalServiceError(AppException):
    """External service error.
    
    Raised when an external service (API, third-party) fails.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR", details=details)


class RateLimitError(AppException):
    """Rate limit exceeded error.
    
    Raised when a client exceeds the configured request rate limit.
    """

    def __init__(self, message: str = "Too many requests. Please try again later.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", details=details)


class OAuthError(AppException):
    """OAuth authentication error.
    
    Raised when an OAuth2 flow fails (invalid code, provider error, account linking).
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code="OAUTH_ERROR", details=details)

