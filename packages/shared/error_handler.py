import logging
from fastapi import HTTPException


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CustomException(Exception):
    """Base class for custom exceptions."""

    pass


class NotFoundError(CustomException):
    """Exception raised for not found errors."""

    pass


class ValidationError(CustomException):
    """Exception raised for validation errors."""

    pass


def handle_error(error, context="fastapi"):
    """Centralized error handling function.
    context: "fastapi" (default) or "discord"
    """
    logging.error(f"An error occurred: {error}")
    if context == "fastapi":
        if isinstance(error, ValidationError):
            raise HTTPException(status_code=400, detail=str(error))
        if isinstance(error, NotFoundError):
            raise HTTPException(status_code=404, detail=str(error))
        # For all other errors, return 500
        raise HTTPException(status_code=500, detail=str(error))
    # For discord context, just log and do not raise


"""
Centralized Error Handler

Usage:
- In FastAPI endpoints, call handle_error(error, context="fastapi") in except blocks.
  - ValidationError -> HTTP 400
  - NotFoundError   -> HTTP 404
  - Other Exception -> HTTP 500
- In Discord command handlers, call handle_error(error, context="discord").
  - Only logs the error; does not raise.
  - Always send a user-facing message after calling handle_error.

Do NOT use handle_error in low-level service or database code; propagate exceptions up to the API or command handler layer.
"""

import functools


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
            except ValidationError as ve:
                try:
                    handle_error(ve, context="discord")
                except Exception:
                    pass
                await _safe_send_message(interaction, str(ve), ephemeral=True)
            except NotFoundError as ne:
                try:
                    handle_error(ne, context="discord")
                except Exception:
                    pass
                await _safe_send_message(interaction, str(ne), ephemeral=True)
            except Exception as e:
                try:
                    handle_error(e, context="discord")
                except Exception:
                    pass
                await _safe_send_message(interaction, fallback_message, ephemeral=True)

        return wrapper

    return decorator


async def _safe_send_message(interaction, message, ephemeral=True):
    """
    Safely send a message to the interaction, handling already-responded errors.
    Always attempts response.send_message first for test compatibility.
    """
    try:
        await interaction.response.send_message(message, ephemeral=ephemeral)
        return
    except Exception:
        # If response.send_message fails, try followup.send if available
        try:
            if hasattr(interaction, "followup") and hasattr(
                interaction.followup, "send"
            ):
                await interaction.followup.send(message, ephemeral=ephemeral)
                return
        except Exception:
            pass
    # If both fail, raise for test visibility
    raise RuntimeError("Failed to send error message to Discord interaction.")


def fastapi_error_handler(func):
    """
    Decorator for FastAPI endpoint functions to centralize error handling.
    Usage:
        @fastapi_error_handler
        def endpoint(...):
            ...
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValidationError, NotFoundError) as e:
            handle_error(e, context="fastapi")
        except Exception as e:
            handle_error(e, context="fastapi")

    return wrapper
