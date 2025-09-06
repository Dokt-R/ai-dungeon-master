"""
Update State Node for Action Resolution

This module handles updating the game state based on action results,
managing NPC HP changes, item acquisitions, and other state transitions.
"""

from typing import Any, Dict

from sqlmodel import Session, create_engine

from packages.backend.ai.state.action_resolution_state import ActionResolutionState
from packages.backend.components.game_state_manager import GameStateService
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


def _display_action(message: str) -> None:
    """Display action message to screen."""
    print(message)


async def update_state_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Update the game state based on action results."""
    # In a real application, the session would be managed by a dependency injection system
    # For this example, we'll create a new session.
    engine = create_engine(
        "sqlite:///./data/srd_database.sqlite"
    )  # Use your actual database URL
    with Session(engine) as session:
        game_state_service = GameStateService(session)
        try:
            action_result = state.get("action_result", {})
            game_state = state[
                "game_state"
            ]  # This is still the in-memory representation for now

            if action_result.get("type") == "attack" and action_result.get("success"):
                target_id = action_result.get("target_id")
                if target_id:
                    character = await game_state_service.get_character_by_id(target_id)
                    if character:
                        character.hp = action_result["new_hp"]
                        await game_state_service.update_character(character)
                        _display_action(
                            f"📊 State Updated: {character.name} HP now {character.hp}"
                        )
                        # Update the in-memory game_state for subsequent nodes in this graph run
                        if target_id == game_state["player"]["character_id"]:
                            game_state["player"]["hp"] = character.hp
                            game_state["player"]["is_alive"] = character.is_alive
                        elif str(target_id) in game_state["npcs"]:
                            game_state["npcs"][str(target_id)]["hp"] = character.hp
                            game_state["npcs"][str(target_id)]["is_alive"] = (
                                character.is_alive
                            )

            # TODO: Handle other state updates like item acquisition, conditions, etc.

            return {"game_state": game_state}

        except Exception as e:
            error_msg = f"State update failed: {str(e)}"
            logger.error("state_update_failed", error=str(e))
            return {"error": error_msg}
