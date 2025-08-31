"""
Combat Narrative Node
"""
from typing import Any, Dict

from packages.backend.ai.state import ActionResolutionState


async def narrate_combat_event_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Generates narrative responses for combat events."""
    combat_state = state["combat_state"]
    if not combat_state:
        return {}

    # This is a placeholder for more sophisticated narrative generation.
    # In a real implementation, an LLM would be used to craft dynamic descriptions
    # based on the combat_state, recent actions, and game_state.
    
    narrative_events = []

    # Example: Narrate turn start
    active_participant_id = combat_state["active_turn_participant_id"]
    if active_participant_id:
        narrative_events.append(f"It is {active_participant_id}'s turn.")

    # Example: Narrate combat end
    if state.get("combat_over"):
        narrative_events.append("The battle concludes!")
    elif state.get("game_over"):
        narrative_events.append("The battle ends in defeat...")

    # Combine narratives
    narrative_response = "\n".join(narrative_events)
    if narrative_response:
        print(f"---NARRATIVE: {narrative_response}---")

    return {"narrative_response": narrative_response}