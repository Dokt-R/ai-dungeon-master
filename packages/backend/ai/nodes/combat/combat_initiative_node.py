"""
Combat Initiative Node
"""
from typing import Any, Dict

from packages.backend.ai.state import ActionResolutionState
from packages.backend.ai.state.base_state import Character
from packages.backend.ai.tools import DiceRoller


async def roll_initiative_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Rolls initiative for all participants and establishes turn order."""
    combat_state = state.get("combat_state")
    game_state = state.get("game_state")

    if not combat_state or not game_state:
        return {"error": "Combat state or Game state not found for initiative roll."}

    dice_roller = DiceRoller()
    participants = combat_state["participants"]
    characters: Dict[str, Character] = game_state["characters"]
    
    initiative_rolls = []
    for participant_id, participant_data in participants.items():
        character = characters.get(participant_id)
        if not character:
            print(f"Warning: Character {participant_id} not found in game_state for initiative.")
            dexterity_modifier = 0  # Fallback to 0 if character not found
        else:
            dexterity_modifier = character.dexterity_mod
        
        initiative_roll_result = dice_roller.roll_initiative(dexterity_modifier)
        participant_data["initiative_score"] = initiative_roll_result.total
        initiative_rolls.append((participant_id, initiative_roll_result.total))
        print(f"---{participant_id} rolled {initiative_roll_result.total} for initiative (Dex Mod: {dexterity_modifier})---")

    # Sort participants by initiative roll, descending
    initiative_rolls.sort(key=lambda x: x[1], reverse=True)
    combat_state["initiative_queue"] = [participant_id for participant_id, roll in initiative_rolls]
    
    if combat_state["initiative_queue"]:
        combat_state["active_turn_participant_id"] = combat_state["initiative_queue"][0]
    else:
        combat_state["active_turn_participant_id"] = None # No participants, no active turn

    return {"combat_state": combat_state}