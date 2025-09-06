from packages.backend.ai.state import ActionResolutionState
from packages.shared.error_handler import _get_player_message
from packages.shared.errors import ErrorCode
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


def error_handler_node(state: ActionResolutionState) -> dict:
    """
    Handles errors in the action resolution graph using the centralized error system.
    """
    error_info = state.get("error")
    if not error_info:
        return {}

    correlation_id = state.get("correlation_id")
    error_code = error_info.get("error_code", ErrorCode.UNKNOWN)
    details = error_info.get("details", {})

    logger.error(
        "action_resolution_error",
        error_code=error_code,
        details=details,
        correlation_id=correlation_id,
        state=state,
    )

    # Generate a player-facing narrative using the centralized system
    narrative = _get_player_message(error_code, **details)

    # We clear the error after handling it and set the narrative
    return {"error": None, "narrative_response": narrative}
