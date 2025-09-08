"""
Minimal Action Resolution Graph for DnD Adventure

GOAL: The player must retrieve the key from the chest in the room
ROOM: Contains a single goblin (hostile) and a one locked chest
WIN CONDITION: Player gets the key

This module implements a LangGraph-based action resolution system that:
- Parses player intent from text input
- Routes to appropriate action handlers (combat, exploration, etc.)
- Resolves combat actions using dice rolls and DnD rules
- Updates game state and generates narrative responses

Architecture follows patterns from dm_graph.py and combat_graph.py.
"""

from typing import Any, Dict

from packages.backend.ai.constants.actions import ROUTE_MAPPING
from packages.backend.components.game_state_manager import GameStateService
from packages.shared.models.langgraph_state_models import MinimalGameState
from packages.shared.models.state_adapters import StateAdapter

# from packages.backend.components.database import get_db_session

# LangGraph imports
try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    # Fallback types if imports fail

# Node imports

from packages.backend.ai.graphs.subgraphs.combat_subgraph import get_combat_subgraph
from packages.backend.ai.nodes.core import (
    error_handler_node,
    narrate_result_node,
    parse_intent_node,
    update_state_node,
)
from packages.backend.ai.nodes.exploration.exploration_resolution_node import (
    exploration_node,
)
from packages.backend.ai.nodes.social.interaction_resolution_node import (
    interaction_node,
)

# Dice roller integration
from packages.backend.ai.tools import DiceRoller
from packages.shared.errors import ErrorCode
from packages.shared.logging_config import configure_logging, get_logger

configure_logging(level="INFO")
logger = get_logger(__name__)


async def route_by_intent(state: MinimalGameState) -> str:
    """Route to appropriate node based on parsed intent or error state."""
    if state.get("error"):
        return "error_handler"

    # Check for exit_early signal
    if state.get("exit_early"):
        logger.debug("exit_early_detected", correlation_id=state["correlation_id"])
        return END

    if not state.get("parsed_intent"):
        state["error"] = {
            "error_code": ErrorCode.INTENT_PARSING_FAILED,
            "details": {"player_action": state.get("player_action")},
        }
        return "error_handler"

    action_type = state["parsed_intent"].get("action_type", "").lower()

    # Use standardized routing mapping from constants
    routing_map = ROUTE_MAPPING

    route_target = routing_map.get(
        action_type, "exploration_node"
    )  # Default to exploration
    logger.debug(
        "routing_decision",
        action_type=action_type,
        route_target=route_target,
        correlation_id=state["correlation_id"],
    )

    return route_target


async def check_exit_early(state: MinimalGameState, next_node: str) -> str:
    """
    Helper function to check for exit_early and route accordingly.
    If exit_early is set, returns END, otherwise returns the next_node.
    """
    if state.get("exit_early"):
        logger.debug(
            "exit_early_detected_mid_flow", correlation_id=state["correlation_id"]
        )
        return END
    return next_node


def check_exit_early_sync(state: MinimalGameState, next_node: str) -> str:
    """
    Synchronous helper function to check for exit_early and route accordingly.
    If exit_early is set, returns END, otherwise returns the next_node.
    """
    if state.get("exit_early"):
        logger.debug(
            "exit_early_detected_mid_flow", correlation_id=state["correlation_id"]
        )
        return END
    return next_node


class ActionResolutionService:
    """Service for handling player actions in a DnD adventure context."""

    def __init__(self):
        self.dice_roller = DiceRoller()
        self._graph = None
        self._is_initialized = False

    async def initialize(self) -> bool:
        """Initialize the action resolution graph."""
        if not LANGGRAPH_AVAILABLE:
            logger.error("LangGraph not available for action resolution")
            return False

        try:
            self._graph = await self._build_graph()
            self._is_initialized = True
            logger.debug("action_resolution_graph_initialized")
            return True
        except Exception as e:
            logger.error("action_resolution_initialization_failed", error=str(e))
            return False

    async def _build_graph(self) -> Any:
        """Build the LangGraph workflow for action resolution."""

        workflow = StateGraph(MinimalGameState)

        # Add nodes (imported from modular node modules)
        workflow.add_node("parse_intent", parse_intent_node)
        combat_subgraph = get_combat_subgraph()
        workflow.add_node("combat_subgraph", combat_subgraph)
        workflow.add_node("exploration_node", exploration_node)
        workflow.add_node(
            "interaction_node", interaction_node
        )  # New node for interactions
        workflow.add_node("update_state", update_state_node)
        workflow.add_node("narrate_result", narrate_result_node)
        workflow.add_node("error_handler", error_handler_node)

        # Set Entry Point
        workflow.set_entry_point("parse_intent")

        # Add edges between core nodes
        # CRITICAL: Add conditional routing based on intent
        workflow.add_conditional_edges(
            "parse_intent",
            route_by_intent,
            {
                "combat_node": "combat_subgraph",
                "exploration_node": "exploration_node",
                "interaction_node": "interaction_node",
                "narrate_result": "narrate_result",  # For errors or unrecognized actions
                "error_handler": "error_handler",
                END: END,  # Added for exit_early routing
                # MAYBE: Add Social Node and Error Handler specific routes
            },
        )

        # All action nodes converge to update_state with exit_early check
        def route_to_update_or_end(state):
            return check_exit_early_sync(state, "update_state")

        workflow.add_conditional_edges(
            "combat_subgraph",
            route_to_update_or_end,
            {"update_state": "update_state", END: END},
        )
        workflow.add_conditional_edges(
            "exploration_node",
            route_to_update_or_end,
            {"update_state": "update_state", END: END},
        )
        workflow.add_conditional_edges(
            "interaction_node",
            route_to_update_or_end,
            {"update_state": "update_state", END: END},
        )
        workflow.add_conditional_edges(
            "error_handler",
            route_to_update_or_end,
            {"update_state": "update_state", END: END},
        )

        # Final edges with exit_early check
        def route_to_narrate_or_end(state):
            return check_exit_early_sync(state, "narrate_result")

        def route_to_end_only(state):
            return check_exit_early_sync(state, END)

        workflow.add_conditional_edges(
            "update_state",
            route_to_narrate_or_end,
            {"narrate_result": "narrate_result", END: END},
        )
        workflow.add_conditional_edges("narrate_result", route_to_end_only, {END: END})

        return workflow.compile()

    # @observability_service.trace_ai_workflow_decorator(
    #     workflow_name="action_resolution_workflow",
    #     workflow_type="game_action_processing"
    # )
    async def resolve_action(
        self, player_action: str, game_state: Dict[str, Any], correlation_id: str
    ) -> Dict[str, Any]:
        """
        Resolve a player action and return updated game state with narrative.

        Args:
            player_action: The player's action text (e.g., "I attack the goblin")
            game_state: Current game state with player and NPCs
            correlation_id: For tracing and logging

        Returns:
            Dict containing narrative response and updated game state
        """
        if not self._is_initialized or not self._graph:
            raise Exception("Action resolution service not initialized")

        # Initialize performance tracking
        import time

        start_time = time.time()

        # Use StateAdapter to convert the incoming game_state dict to MinimalGameState
        # and enrich it with player_action and correlation_id
        initial_minimal_state = StateAdapter.campaign_db_to_minimal_state(
            game_state_service=GameStateService(),
            campaign_id=game_state.get("campaign_id"),
            discord_user_id=game_state.get("discord_user_id"),
            discord_channel_id=game_state.get("discord_channel_id"),
            correlation_id=correlation_id,
        )
        initial_minimal_state["player_action"] = player_action

        print("--------> resolve_action before aiinvoke")
        result: MinimalGameState = await self._graph.ainvoke(initial_minimal_state)
        print("--------> resolve_action after aiinvoke")

        if result.get("error"):
            logger.error(
                "action_resolution_failed",
                correlation_id=correlation_id,
                error=result["error"],
            )

        # Calculate performance metrics
        execution_time = time.time() - start_time
        performance_data = {
            "execution_time": execution_time,
            "node_count": 6,  # Based on our 6 nodes
            "action_type": result.get("parsed_intent", {}).get(
                "action_type", "unknown"
            ),
        }

        # Extract narrative from action result if available
        narrative = result.get("narrative_response", "")
        if not narrative:
            # Generate narrative from action result if available
            action_result = result.get("action_result", {})
            if action_result.get("success"):
                narrative = action_result.get(
                    "description", "Action completed successfully."
                )
            else:
                narrative = action_result.get(
                    "description", "Action could not be resolved."
                )
                error = action_result.get("description", "Unknown error occurred")

        # Get updated game state from the result
        # The result itself is a MinimalGameState, which we can convert back or use its components
        updated_game_state_dict = {
            "campaign_id": result.get("campaign_id"),
            "character_id": result.get("character_id"),
            "discord_user_id": result.get("discord_user_id"),
            "discord_channel_id": result.get("discord_channel_id"),
            # Add other fields from MinimalGameState that should be part of the returned game_state
            # For now, we'll just return the core IDs and let the GameStateService handle persistence
        }

        # Calculate performance metrics - node count is now accurate with 6 nodes
        action_type = result.get("parsed_intent", {}).get("action_type", "unknown")
        performance_data = {
            "execution_time": execution_time,
            "node_count": len(
                [
                    "parse_intent",
                    "combat_subgraph",
                    "exploration_node",
                    "interaction_node",
                    "update_state",
                    "narrate_result",
                ]
            ),  # Accurate count
            "action_type": action_type,
            "routing_path": ROUTE_MAPPING.get(action_type, "exploration_node"),
        }

        return {
            "narrative": narrative,
            "updated_game_state": updated_game_state_dict,  # Return the dict representation
            "correlation_id": correlation_id,
            "error": result.get("error"),
            "performance": performance_data,
        }

    # Game state creation moved to packages.backend.ai.testing.game_state_utils
    # Test function moved to testing module as well


# Global service instance
action_resolution_service = ActionResolutionService()


# Test function moved to packages.backend.ai.testing.game_state_utils
