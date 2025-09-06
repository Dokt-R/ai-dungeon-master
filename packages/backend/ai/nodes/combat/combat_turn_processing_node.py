"""
Combat Turn Processing Node
"""

from typing import Any, Dict

from packages.backend.ai.state import ActionResolutionState


async def process_turn_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Manages the flow of a single combat turn."""
    combat_state = state["combat_state"]
    if not combat_state:
        return {}

    active_participant_id = combat_state["active_turn_participant_id"]
    participant = combat_state["participants"][active_participant_id]

    # Skip turn if surprised
    if participant["is_surprised"]:
        print(f"---{active_participant_id} is surprised and cannot act!---")
        participant["is_surprised"] = False  # Surprise only lasts one round
        return {"combat_state": combat_state}

    print(f"---It is now {active_participant_id}'s turn.---")

    # In a real implementation, this is where you would prompt the player for an action
    # or trigger the AI for an NPC's action. For now, we'll just print.

    return {}
