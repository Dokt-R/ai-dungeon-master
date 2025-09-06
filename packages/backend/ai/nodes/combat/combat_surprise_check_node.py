"""
Combat Surprise Check Node
"""

from typing import Any, Dict

from packages.backend.ai.state import ActionResolutionState
from packages.backend.ai.tools import DiceRoller


async def surprise_check_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Performs a surprise check for all participants."""
    """
    ! Surprise.
    If a combatant is surprised by combat 
    starting, that combatant has Disadvantage on their 
    Initiative roll. For example, if an ambusher starts 
    combat while hidden from a foe who is unaware 
    that combat is starting, that foe is surprised.
    """
    return {}

    combat_state = state["combat_state"]
    if not combat_state:
        return {}

    dice_roller = DiceRoller()
    participants = combat_state["participants"]

    # Example: Simple surprise logic. This can be expanded with more complex rules.
    # For now, let's assume a fixed DC or compare against a group check.
    stealth_dc = 12

    for participant_id, participant in participants.items():
        # In a real scenario, you'd get the Wisdom (Perception) modifier from the character sheet
        # For now, we'll use a placeholder modifier.
        perception_modifier = 0
        perception_check = dice_roller.roll_skill_check(perception_modifier)

        if perception_check.total < stealth_dc:
            participant["is_surprised"] = True
            print(
                f"---{participant['id']} IS SURPRISED (Perception: {perception_check.total} vs DC: {stealth_dc})---"
            )
        else:
            participant["is_surprised"] = False
            print(
                f"---{participant['id']} IS NOT SURPRISED (Perception: {perception_check.total} vs DC: {stealth_dc})---"
            )

    return {"combat_state": combat_state}
