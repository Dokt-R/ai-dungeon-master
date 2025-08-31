"""
Combat Initiative Node
"""
from typing import Any, Dict

from packages.backend.ai.state import ActionResolutionState
from packages.backend.ai.tools import DiceRoller


async def roll_initiative_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Rolls initiative for all participants and establishes turn order."""
    combat_state = state["combat_state"]
    if not combat_state:
        return {}

    dice_roller = DiceRoller()
    participants = combat_state["participants"]
    
    initiative_rolls = []
    for participant_id, participant in participants.items():
        # In a real scenario, you'd get the dexterity modifier from the character sheet
        # For now, we'll use a placeholder modifier.
        dexterity_modifier = 0
        initiative_roll_result = dice_roller.roll_initiative(dexterity_modifier)
        participant["initiative_score"] = initiative_roll_result.total
        initiative_rolls.append((participant_id, initiative_roll_result.total))
        print(f"---{participant_id} rolled {initiative_roll_result.total} for initiative---")

    # Sort participants by initiative roll, descending
    initiative_rolls.sort(key=lambda x: x[1], reverse=True)
    combat_state["initiative_queue"] = [participant_id for participant_id, roll in initiative_rolls]
    combat_state["active_turn_participant_id"] = combat_state["initiative_queue"][0]

    return {"combat_state": combat_state}