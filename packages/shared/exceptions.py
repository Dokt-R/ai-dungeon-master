from typing import Any, Dict, Optional

from packages.shared.errors import ERRORS, PLAYER_ERRORS, ErrorCode


class CustomException(Exception):
    """Base class for custom exceptions."""

    def __init__(self, error_code: ErrorCode, **kwargs):
        if error_code not in ERRORS:
            raise ValueError(f"Unknown error code: {error_code}")

        # Internal message for logging
        internal_error = ERRORS[error_code]
        message = internal_error.message.format(**kwargs)

        self.message = message

        super().__init__(message)

        # Player-facing message for Discord
        player_error = PLAYER_ERRORS.get(error_code)
        if player_error:
            self.player_message = player_error.message.format(**kwargs)
        else:
            self.player_message = self.message

        self.error_code: ErrorCode = internal_error.error_code
        self.status_code: int = internal_error.status_code
        self.details: Optional[Dict[str, Any]] = kwargs.get("details") or {}

# ===== Specific Subclasses =====

class ValidationError(CustomException):
    def __init__(self, error_code: ErrorCode = ErrorCode.VALIDATION_ERROR, **kwargs):
        super().__init__(error_code, **kwargs)


class NotFoundError(CustomException):
    def __init__(self, error_code: ErrorCode = ErrorCode.NOT_FOUND, **kwargs):
        super().__init__(error_code, **kwargs)


class AIAPIError(CustomException):
    def __init__(self, error_code: ErrorCode = ErrorCode.AI_API_ERROR, **kwargs):
        super().__init__(error_code, **kwargs)

class PermissionDeniedError(CustomException):
    def __init__(self, error_code: ErrorCode = ErrorCode.PERMISSION_DENIED_ERROR, **kwargs):
        super().__init__(error_code, **kwargs)
