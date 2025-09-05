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
from packages.shared.models.langgraph_state_models import MinimalGameState


def combat_check_exit_early(state: MinimalGameState, next_node: str) -> str:
    """
    Helper function to check for exit_early in combat subgraph.
    If exit_early is set, returns END, otherwise returns the next_node.
    """
    if state.get("exit_early"):
        return END
    return next_node


def should_continue_combat(state: MinimalGameState) -> str:
    """Determines if the combat should continue to the next turn or end."""
    if state.get("exit_early"):
        return "end_combat"
    if state.get("combat_over") or state.get("game_over"):
        return "end_combat"
    return "process_turn"


def get_combat_subgraph():
    """Builds and returns the combat subgraph."""
    workflow = StateGraph(MinimalGameState)

    # Define nodes for the combat subgraph
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

    # Define the flow of combat with exit_early checks
    workflow.set_entry_point("initialize_combat")

    workflow.add_conditional_edges(
        "initialize_combat",
        lambda state: combat_check_exit_early(state, "surprise_check"),
        {"surprise_check": "surprise_check", "__end__": END}
    )
    workflow.add_conditional_edges(
        "surprise_check",
        lambda state: combat_check_exit_early(state, "roll_initiative"),
        {"roll_initiative": "roll_initiative", "__end__": END}
    )
    workflow.add_conditional_edges(
        "roll_initiative",
        lambda state: combat_check_exit_early(state, "process_turn"),
        {"process_turn": "process_turn", "__end__": END}
    )
    workflow.add_conditional_edges(
        "process_turn",
        lambda state: combat_check_exit_early(state, "resolve_combat_action"),
        {"resolve_combat_action": "resolve_combat_action", "__end__": END}
    )
    workflow.add_conditional_edges(
        "resolve_combat_action",
        lambda state: combat_check_exit_early(state, "death_save"),
        {"death_save": "death_save", "__end__": END}
    )
    workflow.add_conditional_edges(
        "death_save",
        lambda state: combat_check_exit_early(state, "narrate_combat_event"),
        {"narrate_combat_event": "narrate_combat_event", "__end__": END}
    )
    # This node will route to either end_turn (normal flow) or END (early exit)
    # The should_continue_combat function will determine the final end_combat route
    workflow.add_conditional_edges(
        "narrate_combat_event",
        lambda state: combat_check_exit_early(state, "end_turn"),
        {"end_turn": "end_turn", "__end__": END}
    )

    # Conditional logic to loop or end combat with exit_early support
    workflow.add_conditional_edges(
        "end_turn",
        should_continue_combat,
        {
            "process_turn": "process_turn",  # Loop back for next turn
            "end_combat": "narrate_combat_event",  # Narrate before ending combat
        },
    )
    # Removed duplicate conditional edge to avoid naming conflict

    return workflow.compile()
