"""
Combat Subgraph

This module defines the combat subgraph for handling all combat-related logic,
including turn management, action resolution, and state updates.
"""

from langgraph.graph import END, StateGraph

from packages.backend.ai.nodes.combat import (
    death_save_node,
    end_turn_node,
    initialize_combat_node,
    narrate_combat_event_node,
    process_turn_node,
    resolve_combat_action_node,
    roll_initiative_node,
    surprise_check_node,
)
from packages.backend.ai.state import ActionResolutionState


def should_continue_combat(state: ActionResolutionState) -> str:
    """Determines if the combat should continue to the next turn or end."""
    if state.get("combat_over") or state.get("game_over"):
        return "end_combat"
    return "process_turn"


def get_combat_subgraph():
    """Builds and returns the combat subgraph."""
    workflow = StateGraph(ActionResolutionState)

    # Define nodes for the combat subgraph
    """
    ! TO IMPLEMENT IN A NODE FOR STEP 1
    Establish Positions.
    The Game Master determines where all the characters and monsters are located.
    Given the adventurers’ marching order or their stated positions in the room
    or other location, the GM figures out where the adversaries are—how far away
    and in what direction.
    """
    workflow.add_node("initialize_combat", initialize_combat_node)
    workflow.add_node("surprise_check", surprise_check_node)
    workflow.add_node("roll_initiative", roll_initiative_node)
    workflow.add_node("process_turn", process_turn_node)
    workflow.add_node("resolve_combat_action", resolve_combat_action_node)
    workflow.add_node("death_save", death_save_node)
    workflow.add_node("end_turn", end_turn_node)
    workflow.add_node("narrate_combat_event", narrate_combat_event_node)
    workflow.add_node(
        "end_combat", lambda state: {"combat_over": True}
    )  # Simple node to mark the end

    # Define the flow of combat
    workflow.set_entry_point("initialize_combat")
    workflow.add_edge("initialize_combat", "surprise_check")
    workflow.add_edge("surprise_check", "roll_initiative")
    workflow.add_edge("roll_initiative", "process_turn")
    workflow.add_edge("process_turn", "resolve_combat_action")  # Resolve action first
    workflow.add_edge(
        "resolve_combat_action", "death_save"
    )  # Add death save after action resolution
    workflow.add_edge(
        "death_save", "narrate_combat_event"
    )  # Narrate after action and death saves
    workflow.add_edge("narrate_combat_event", "end_turn")  # Then proceed to end turn

    # Conditional logic to loop or end combat
    workflow.add_conditional_edges(
        "end_turn",
        should_continue_combat,
        {
            "process_turn": "process_turn",  # Loop back for next turn
            "end_combat": "narrate_combat_event",  # Narrate before ending combat
        },
    )
    workflow.add_edge("narrate_combat_event", END)  # End after narrative

    return workflow.compile()
