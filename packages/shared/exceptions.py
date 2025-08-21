from packages.shared.errors import ERRORS, PLAYER_ERRORS, ErrorCode


class CustomException(Exception):
    """Base class for custom exceptions."""

    def __init__(self, error_code: ErrorCode, *, details: dict | None = None, **kwargs):
        if error_code not in ERRORS:
            raise ValueError(f"Unknown error code: {error_code}")

        # Internal message for logging
        internal_error = ERRORS[error_code]

        self.details = details or {}
        self.details.update(kwargs)
        self.message = internal_error.message.format(**self.details)

        super().__init__(self.message)

        # Player-facing message for Discord
        player_error = PLAYER_ERRORS.get(error_code)
        if player_error:
            self.player_message = player_error.message.format(**self.details)
        else:
            self.player_message = self.message

        self.error_code: ErrorCode = internal_error.error_code
        self.status_code: int = internal_error.status_code

    def __str__(self):
        return f"{self.__class__.__name__}(error_code={self.error_code}, details={self.details})"
        

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
    def __init__(
        self, error_code: ErrorCode = ErrorCode.PERMISSION_DENIED_ERROR, **kwargs
    ):
        super().__init__(error_code, **kwargs)
