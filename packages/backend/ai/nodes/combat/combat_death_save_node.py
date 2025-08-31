"""
Combat Death Save Node
"""
from typing import Any, Dict

from packages.backend.ai.state import ActionResolutionState
from packages.backend.ai.tools import DiceRoller


async def death_save_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Handles death saving throws for unconscious participants."""
    combat_state = state["combat_state"]
    if not combat_state:
        return {}

    dice_roller = DiceRoller()
    
    for participant_id, participant in combat_state["participants"].items():
        if "unconscious" in participant["status_conditions"] and "dead" not in participant["status_conditions"]:
            print(f"---{participant_id} is making a death saving throw!---")
            roll = dice_roller.roll_dice_notation("1d20").total

            if roll >= 10:
                participant["death_save_successes"] += 1
                print(f"---{participant_id} rolled a {roll} (Success)! Total successes: {participant['death_save_successes']}---")
            else:
                participant["death_save_failures"] += 1
                print(f"---{participant_id} rolled a {roll} (Failure)! Total failures: {participant['death_save_failures']}---")

            if participant["death_save_successes"] >= 3:
                participant["status_conditions"].remove("unconscious")
                participant["status_conditions"].add("stable")
                participant["current_health"] = 1 # Stabilized at 1 HP
                print(f"---{participant_id} is stable and regains 1 HP!---")
            elif participant["death_save_failures"] >= 3:
                participant["status_conditions"].remove("unconscious")
                participant["status_conditions"].add("dead")
                print(f"---{participant_id} has failed three death saves and is DEAD!---")
        
    return {"combat_state": combat_state}