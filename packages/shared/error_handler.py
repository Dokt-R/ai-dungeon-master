import functools
import logging

from packages.shared.errors import ERRORS, PLAYER_ERRORS
from packages.shared.exceptions import (
    AIAPIError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def _get_player_message(code: str, **kwargs) -> str:
    """
    Returns a player-facing message based on error code and optional formatting args.
    Falls back to the internal error message if no mapping exists.
    """
    player_err_def = PLAYER_ERRORS.get(code)
    if player_err_def:
        return player_err_def.message.format(**kwargs)
    # Fallback — use internal message
    return ERRORS[code].message.format(**kwargs)


# Example usage
# try:
#     ...
# except GameException as e:
#     player_msg = get_player_message(e.code, **e.details)
#     await discord_channel.send(player_msg)


def discord_error_handler(
    fallback_message="An unexpected error occurred. Please contact an administrator.",
):
    """
    Decorator for Discord command methods to centralize error handling and user messaging.
    Sends player-facing messages to the user, logs internal details for debugging.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction, *args, **kwargs):
            try:
                await func(self, interaction, *args, **kwargs)
            except (
                ValidationError,
                NotFoundError,
                AIAPIError,
                PermissionDeniedError,
            ) as exc:
                # Log custom exceptions with their structured data and stack trace
                logger.warning(
                    f"{type(exc).__name__} occurred: {exc.message} "
                    f"(Code: {exc.error_code}, Details: {exc.details})",
                    exc_info=True,
                )
                player_message = _get_player_message(exc.error_code, **exc.details)
                await _safe_send_message(interaction, player_message, ephemeral=True)
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
