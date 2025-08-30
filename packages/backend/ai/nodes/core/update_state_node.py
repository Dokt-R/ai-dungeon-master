"""
Update State Node for Action Resolution

This module handles updating the game state based on action results,
managing NPC HP changes, item acquisitions, and other state transitions.
"""

import time
from typing import Any, Dict

from packages.backend.ai.state.action_resolution_state import ActionResolutionState
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


def _display_action(message: str) -> None:
    """Display action message to screen."""
    print(message)


async def update_state_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Update the game state based on action results."""
    try:
        action_result = state.get("action_result", {})
        game_state = state["game_state"]

        if action_result.get("type") == "attack" and action_result.get("success"):
            # Update defender HP
            target_name = action_result.get("target_name")
            npcs = game_state.get("npcs", [])

            for npc in npcs.values():
                if npc.get("name") == target_name:
                    npc["hp"] = action_result["new_hp"]
                    npc["is_alive"] = action_result["defender_alive"]
                    break

            _display_action(f"📊 State Updated: {target_name} HP now {action_result['new_hp']}")

        return {"game_state": game_state}

    except Exception as e:
        error_msg = f"State update failed: {str(e)}"
        logger.error("state_update_failed", error=str(e))
        return {"error": error_msg}