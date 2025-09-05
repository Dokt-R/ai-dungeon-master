"""
Combat Initiative Node
"""
from typing import Any, Dict

from fastapi import Depends

from packages.backend.ai.state.base_state import Character
from packages.backend.ai.tools import DiceRoller

# from packages.backend.ai.state import ActionResolutionState
from packages.backend.components.game_state_manager import GameStateService
from packages.shared.models.langgraph_state_models import (
    CombatState,
    MinimalGameState,
)


async def roll_initiative_node(
            state: MinimalGameState, game_service: GameStateService = Depends()
) -> Dict[str, CombatState]:
    """Rolls initiative for all participants and establishes turn order."""
    combat_state = state.get("combat_state")

    if not combat_state:
        return {"error": "Combat state not found for initiative roll."}

    dice_roller = DiceRoller()
    participants = combat_state.participants




    initiative_order = []
    for participant_key, combat_participant in participants.items():
        """
        #! Need to add condition for identical creatures
        For a group of identical creatures, the GM makes a single roll,
        so each member of the group has the same Initiative.
        """
        """
        ! Surprise.
        If a combatant is surprised by combat 
        starting, that combatant has Disadvantage on their 
        Initiative roll. For example, if an ambusher starts 
        combat while hidden from a foe who is unaware 
        that combat is starting, that foe is surprised.
        """

        roll = dice_roller.roll_initiative(combat_participant.initiative_modifier)
        initiative_order.append({"participant_key": participant_key,
                                 "initiative": roll.total})
        combat_participant.initiative_roll = roll.total

    # Sort participants by initiative roll, descending
    sorted_participants = sorted(participants.items(), key=lambda item: item[1].initiative_roll, reverse=True)
    sorted_initiative_order = sorted(initiative_order, key=lambda x: x["initiative"], reverse=True)
    combat_state.participants = sorted_participants
    combat_state.initiative_order = sorted_initiative_order

    # Change the active participant to the highest initiative
    combat_state.active_participant_id = sorted_participants[0][0]

    """
    ! Can add random or not random resolution for ties here
    If a tie occurs, the GM decides the order 
    among tied monsters, and the players decide the 
    order among tied characters. The GM decides the 
    order if the tie is between a monster and a player 
    character.
    """
    
    if not combat_state.active_participant_id:
        combat_state.active_participant_id = [1]
    
    # TEST MODE: Exit early after initiative roll if test flag is set
    if state.get("test_exit_after_initiative"):
        print("🧪 TEST MODE: Exiting combat early after initiative roll")
        print("🎲 Combat State after Initiative:")
        print(f"   - Active Turn: {combat_state.get('active_turn_participant_id', 'None')}")
        print(f"   - Initiative Queue: {combat_state.get('initiative_queue', [])}")
        for participant_id in combat_state.get('initiative_queue', []):
            participant_data = combat_state.get('participants', {}).get(participant_id, {})
            print(f"   - {participant_id}: Initiative {participant_data.get('initiative_score', 'N/A')}")
        print("⚠️  Setting exit_early=True to prevent normal combat progression")

        # Update the state with combat results and exit_early flag
        updated_state = state.copy()
        updated_state["combat_state"] = combat_state
        updated_state["exit_early"] = True
        updated_state["initiative_completed"] = True

        return updated_state
    
    # Final State Values
    combat_state.combat_phase = "initiative"
    combat_state.needs_initiative_reroll = False
    combat_state.initiative_complete = True

    for attr, value in vars(combat_state).items():
        print(f"{attr} = {value}")

    return {"combat_state": combat_state}
