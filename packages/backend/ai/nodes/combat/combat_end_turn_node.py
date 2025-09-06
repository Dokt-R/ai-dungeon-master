"""
Combat End of Turn Node
"""

from typing import Any, Dict

from packages.backend.ai.state import ActionResolutionState


async def end_turn_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Handles end-of-turn effects and checks for combat conclusion."""
    combat_state = state["combat_state"]
    if not combat_state:
        return {}

    # Process recurring effects for all participants
    for participant_id, participant in combat_state["participants"].items():
        effects_to_remove = []
        for effect in participant["active_effects"]:
            if effect["type"] == "poison":
                # Apply poison damage (example)
                poison_damage = 1  # Placeholder
                participant["current_health"] -= poison_damage
                print(f"---{participant_id} takes {poison_damage} poison damage!---")

            effect["duration"] -= 1
            if effect["duration"] <= 0:
                effects_to_remove.append(effect)

        for effect in effects_to_remove:
            participant["active_effects"].remove(effect)
            print(f"---{participant_id}'s {effect['type']} effect ends.---")

    # Check for victory/defeat conditions
    player_alive = any(
        p["type"] == "player" and "dead" not in p["status_conditions"]
        for p in combat_state["participants"].values()
    )
    enemies_alive = any(
        p["type"] == "enemy" and "dead" not in p["status_conditions"]
        for p in combat_state["participants"].values()
    )

    if not player_alive:
        print("---PLAYER DEFEATED! GAME OVER.---")
        return {"game_over": True}

    if not enemies_alive:
        print("---ALL ENEMIES DEFEATED! COMBAT ENDS.---")
        return {"combat_over": True}

    # Move to the next participant in the initiative queue
    current_index = combat_state["initiative_queue"].index(
        combat_state["active_turn_participant_id"]
    )
    next_index = (current_index + 1) % len(combat_state["initiative_queue"])

    # If we've completed a full round, increment the round number
    if next_index == 0:
        combat_state["current_round"] += 1
        print(f"---STARTING ROUND {combat_state['current_round']}---")

    combat_state["active_turn_participant_id"] = combat_state["initiative_queue"][
        next_index
    ]

    return {"combat_state": combat_state}
