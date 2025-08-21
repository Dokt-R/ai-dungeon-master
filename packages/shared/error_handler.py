from functools import wraps
from typing import Any, Callable

from packages.shared.correlation import correlation_id_context, get_correlation_id
from packages.shared.errors import ERRORS, PLAYER_ERRORS
from packages.shared.exceptions import (
    AIAPIError,
    CustomException,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from packages.shared.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def _get_player_message(code: str, **kwargs: Any) -> str:
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
    fallback_message: str = "An unexpected error occurred. Please contact an administrator.",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for Discord command methods to centralize error handling and user messaging.

    This decorator handles exceptions in Discord commands and sends appropriate messages
    to users while logging errors for developers.

    Args:
        fallback_message (str): Message sent to user for unexpected exceptions

    Example:
        @discord_error_handler(fallback_message="Sorry, something went wrong!")
        async def my_command(self, interaction):
            # Command implementation
            pass
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(
            self: Any, interaction: Any, *args: Any, **kwargs: Any
        ) -> Any:
            # Ensure a correlation id is present for the duration of this command
            current_cid = get_correlation_id()

            if current_cid:
                # Get bound logger with current context
                bound_logger = logger.bind()
                await _handle_command_execution(
                    bound_logger,
                    func,
                    self,
                    interaction,
                    args,
                    kwargs,
                    fallback_message,
                )
                return

            # No CID currently present -> create one for this command scope
            with correlation_id_context():
                bound_logger = logger.bind()
                await _handle_command_execution(
                    bound_logger,
                    func,
                    self,
                    interaction,
                    args,
                    kwargs,
                    fallback_message,
                )

        return wrapper

    return decorator


async def _handle_command_execution(
    bound_logger,
    func: Callable[..., Any],
    self: Any,
    interaction: Any,
    args: Any,
    kwargs: Any,
    fallback_message: str,
) -> Any:
    """Handle the execution of a Discord command with proper error handling and logging.

    This function contains the common error handling logic used by the discord_error_handler decorator.
    """
    try:
        return await func(self, interaction, *args, **kwargs)
    except (
        CustomException,
        ValidationError,
        NotFoundError,
        AIAPIError,
        PermissionDeniedError,
    ) as exc:
        # Log with structured context
        bound_logger.warning(
            "Custom exception occurred",
            exception_type=type(exc).__name__,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
            exc_info=True,
        )
        player_message = _get_player_message(exc.error_code, **exc.details)

        await _safe_send_message(interaction, player_message, ephemeral=True)
    except Exception as e:
        # Log generic exceptions with full stack trace
        bound_logger.error(
            "Unexpected error in command",
            command=func.__name__,
            error=str(e),
            exc_info=True,
        )
        await _safe_send_message(interaction, fallback_message, ephemeral=True)


async def _safe_send_message(
    interaction: Any, message: str, ephemeral: bool = True
) -> None:
    """Safely send a message to the interaction, handling already-responded errors.

    Always attempts response.send_message first for test compatibility.
    Logs warnings when falling back to followup.send and errors when both fail.

    Args:
        interaction: Discord interaction object
        message (str): Message to send
        ephemeral (bool): Whether message should be ephemeral
    """
    try:
        await interaction.response.send_message(message, ephemeral=ephemeral)
        return
    except Exception as e:
        logger.warning(
            f"Failed to send message via interaction.response.send_message: {e}"
        )
        # If response.send_message fails, try followup.send if available
        try:
            if hasattr(interaction, "followup") and hasattr(
                interaction.followup, "send"
            ):
                await interaction.followup.send(message, ephemeral=ephemeral)
                return
        except Exception as e:
            logger.warning(f"Failed to send message via interaction.followup.send: {e}")
            pass
    # If both fail, log error and raise for test visibility
    logger.error(
        "Failed to send message via both response.send_message and followup.send"
    )
    raise RuntimeError("Failed to send error message to Discord interaction.")
