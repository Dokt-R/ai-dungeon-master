import functools
import logging

logger = logging.getLogger(__name__)


class CustomException(Exception):
    """Base class for custom exceptions."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details


class ValidationError(CustomException):
    """Exception raised for validation errors."""

    def __init__(
        self, message: str, error_code: str = "VALIDATION_ERROR", details: dict = None
    ):
        super().__init__(message, error_code, details)


class NotFoundError(CustomException):
    """Exception raised for not found errors."""

    def __init__(
        self, message: str, error_code: str = "NOT_FOUND", details: dict = None
    ):
        super().__init__(message, error_code, details)


class AIAPIError(CustomException):
    """Raised when an external AI API call fails."""

    def __init__(
        self, message: str, error_code: str = "AI_API_ERROR", details: dict = None
    ):
        super().__init__(message, error_code, details)


def discord_error_handler(
    fallback_message="An unexpected error occurred. Please contact an administrator.",
):
    """
    Decorator for Discord command methods to centralize error handling and user messaging.
    Usage:
        @discord_error_handler()
        async def command(self, interaction, ...):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction, *args, **kwargs):
            try:
                await func(self, interaction, *args, **kwargs)
            except (ValidationError, NotFoundError, AIAPIError) as exc:
                # Log custom exceptions with their structured data and stack trace
                logger.warning(
                    f"{type(exc).__name__} occurred: {exc.message} "
                    f"(Code: {exc.error_code}, Details: {exc.details})",
                    exc_info=True,
                )
                await _safe_send_message(interaction, exc.message, ephemeral=True)
            except Exception as e:
                # Log generic exceptions with full stack trace
                logger.error(
                    f"An unexpected error occurred in command {func.__name__}: {e}",
                    exc_info=True,
                )
                await _safe_send_message(interaction, fallback_message, ephemeral=True)

        return wrapper

    return decorator


async def _safe_send_message(interaction, message, ephemeral=True):
    """
    Safely send a message to the interaction, handling already-responded errors.
    Tries to send a new message, or a followup if a response already exists.
    """
    try:
        # The preferred way to respond, especially for the first response
        await interaction.response.send_message(message, ephemeral=ephemeral)
    except Exception:
        try:
            # If the initial response fails, it might be because we already responded.
            # In this case, we use a followup message.
            await interaction.followup.send(message, ephemeral=ephemeral)
        except Exception as e:
            # If both attempts fail, log the error for debugging.
            logger.error(
                f"Failed to send error message to Discord interaction for command. "
                f"Interaction responded: {interaction.response.is_done()}. Error: {e}"
            )
