"""
Combat Initialization Node
"""
from typing import Any, Dict

from packages.backend.ai.state import (
    ActionResolutionState,
    CombatParticipant,
    CombatState,
)


async def initialize_combat_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Initializes the combat state, setting up participants and the environment."""
    game_state = state["game_state"]
    player = game_state["player"]
    npcs = game_state["npcs"]

    participants = {}
    
    # Add player to participants
    participants[player["name"]] = CombatParticipant(
        id=player["name"],
        type='player',
        current_health=player["hp"],
        max_health=player["max_hp"],
        percent_of_damage_taken_this_round=0.0,
        status_conditions=set(player["conditions"]),
        active_effects=[],
        initiative_score=0,
        cover_status='none',
        advantage_conditions=set(),
        is_surprised=False,
        death_save_successes=0,
        death_save_failures=0
    )

    # Add hostile NPCs to participants
    for npc_id, npc in npcs.items():
        if npc["is_hostile"]:
            participants[npc_id] = CombatParticipant(
                id=npc_id,
                type='enemy',
                current_health=npc["hp"],
                max_health=npc["max_hp"],
                percent_of_damage_taken_this_round=0.0,
                status_conditions=set(npc["conditions"]),
                active_effects=[],
                initiative_score=0,
                cover_status='none',
                advantage_conditions=set(),
                is_surprised=False,
                death_save_successes=0,
                death_save_failures=0
            )

    combat_state = CombatState(
        participants=participants,
        current_round=1,
        active_turn_participant_id="",
        combat_phase='initiative',
        initiative_queue=[],
        damage_queue=[],
        pending_effects=[],
        environmental_effects=[]
    )

    print("---COMBAT INITIALIZED---")
    return {"combat_state": combat_state}