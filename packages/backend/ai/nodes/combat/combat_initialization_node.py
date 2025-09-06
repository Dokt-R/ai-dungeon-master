"""
Combat Initialization Node
"""

from typing import Dict

from fastapi import Depends

from packages.backend.components.game_state_manager import GameStateService
from packages.shared.models.langgraph_state_models import (
    CombatState,
    MinimalGameState,
)


async def initialize_combat_node(
    state: MinimalGameState, game_service: GameStateService = Depends()
) -> Dict[str, CombatState]:
    """Initializes the combat state, setting up participants and the environment."""

    """
    ! TO IMPLEMENT IN A NODE FOR STEP 1
    Establish Positions.
    The Game Master determines where all the characters and monsters are located.
    Given the adventurers’ marching order or their stated positions in the room
    or other location, the GM figures out where the adversaries are—how far away
    and in what direction.
    """

    # GET STATE
    game_state = state
    combat_state = CombatState(campaign_id=game_state["campaign_id"])

    # (OPTIONAL FOR LATER) GET PERSISTED COMBAT STATE

    # GET COMBAT PLAYERS
    for player_key in game_state.get("state_players", []):
        participant = await game_service.character_to_combat_participant(
            player_key, "player"
        )
        if participant:
            combat_state.participants[participant.participant_key] = participant
            combat_state.active_participants.append(participant.participant_key)

    # GET NPCS
    for npc_key in game_state.get("state_npcs", []):
        participant = await game_service.character_to_combat_participant(npc_key, "npc")
        if participant:
            combat_state.participants[participant.participant_key] = participant
            combat_state.active_participants.append(participant.participant_key)

    # GET ENEMIES
    for enemy_key in game_state.get("state_enemies", []):
        participant = await game_service.character_to_combat_participant(
            enemy_key, "enemy"
        )
        if participant:
            combat_state.participants[participant.participant_key] = participant
            combat_state.active_participants.append(participant.participant_key)

    # Set the first active participant if any exist
    if combat_state.active_participants:
        combat_state.active_participant_id = combat_state.active_participants[0]

    exit_early_flag = True
    if exit_early_flag:
        print("🧪 EXIT AT COMBAT INITIALIZATION NODE")
        print()
        print(f"   - Combat State: {combat_state}")
        print()

        # Update the state with combat results and exit_early flag
        updated_state = state.copy()
        updated_state["combat_state"] = combat_state
        updated_state["action_result"] = {}
        updated_state["exit_early"] = True
        updated_state["initiative_completed"] = True

        return updated_state

    print()
    print("Routing To ---> initative_node")
    print()
    return {"combat_state": combat_state}
