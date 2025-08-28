"""
Resolve Action Node for Action Resolution

This module provides action routing functionality to determine which
specific action handler (combat, exploration, social) should process
the parsed player intent.
"""

from typing import Any, Dict

from packages.backend.ai.state.action_resolution_state import ActionResolutionState
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


def _display_action(message: str) -> None:
    """Display action message to screen."""
    print(message)


async def resolve_action_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Route to the appropriate action handler."""
    try:
        parsed_intent = state.get("parsed_intent", {})
        action_type = parsed_intent.get("action_type", "unknown")

        _display_action(f"🎮 Routing to: {action_type}_node")

        # For now, all actions route to combat (simplified flow)
        # In a full implementation, this would have conditional routing
        return {}

    except Exception as e:
        error_msg = f"Action routing failed: {str(e)}"
        logger.error("action_routing_failed", error=str(e))
        return {"error": error_msg}