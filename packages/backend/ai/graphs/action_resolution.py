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

import asyncio
from typing import Any, Dict, List, Optional

from packages.backend.ai.state import ParsedIntent

# LangGraph imports
try:
    from langgraph.graph import END, StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None

# State definitions
from packages.backend.ai.nodes.combat.combat_resolution_node import combat_node

# Node imports
from packages.backend.ai.nodes.core import (
    narrate_result_node,
    parse_intent_node,
    resolve_action_node,
    update_state_node,
)
from packages.backend.ai.nodes.exploration.exploration_resolution_node import (
    exploration_node,
)
from packages.backend.ai.state import ActionResolutionState

# Dice roller integration
from packages.backend.ai.tools import DiceRoller
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)




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
        workflow = StateGraph(ActionResolutionState)

        # Add nodes (imported from modular node modules)
        workflow.add_node("parse_intent", parse_intent_node)
        workflow.add_node("resolve_action", resolve_action_node)
        workflow.add_node("combat_node", combat_node)
        workflow.add_node("exploration_node", exploration_node)
        workflow.add_node("update_state", update_state_node)
        workflow.add_node("narrate_result", narrate_result_node)

        # Set linear flow
        workflow.set_entry_point("parse_intent")
        workflow.add_edge("parse_intent", "resolve_action")
        workflow.add_edge("resolve_action", "combat_node")

        # For now, we'll have a simplified flow - combat node leads to state update
        # In a full implementation, resolve_action would conditionally route
        workflow.add_edge("combat_node", "update_state")
        workflow.add_edge("update_state", "narrate_result")
        workflow.add_edge("narrate_result", END)

        return workflow.compile()

    @observability_service.trace_ai_workflow_decorator(
        workflow_name="action_resolution_workflow",
        workflow_type="game_action_processing"
    )
    async def resolve_action(self, player_action: str, game_state: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
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
        initial_state = ActionResolutionState(
            player_action=player_action,
            game_state=game_state,
            parsed_intent=None,
            action_result=None,
            narrative_response=None,
            error=None,
            correlation_id=correlation_id,
            trace_context=None,
            performance_metrics=None
        )

        result = await self._graph.ainvoke(initial_state)

        if result.get("error"):
            logger.error("action_resolution_failed", correlation_id=correlation_id, error=result["error"])

        # Calculate performance metrics
        execution_time = time.time() - start_time
        performance_data = {
            "execution_time": execution_time,
            "node_count": 6,  # Based on our 6 nodes
            "action_type": result.get("parsed_intent", {}).get("action_type", "unknown")
        }

        return {
            "narrative": result.get("narrative_response", "Action could not be resolved."),
            "updated_game_state": result.get("game_state", game_state),
            "correlation_id": correlation_id,
            "error": result.get("error"),
            "performance": performance_data
        }



    # All node implementations moved to domain-specific modules
# Global service instance
action_resolution_service = ActionResolutionService()


# Example usage function for testing
def create_example_game_state():
    """Create example game state for testing."""
    return {
        "player": {
            'name': 'Roric',
            'hp': 12,
            'ac': 14,
            'attack': {'bonus': 3, 'damage': '1d8+1'}
        },
        "npcs": [
            {'name': 'Goblin', 'hp': 1, 'ac': 12, 'is_alive': True}
        ],
        "room_description": "A small, damp room with a locked chest in the corner."
    }


# Test function to demonstrate the system
async def test_action_resolution():
    """Test the action resolution system."""
    print("=" * 50)
    print("🎲 TESTING ACTION RESOLUTION SYSTEM")
    print("=" * 50)

    # Initialize service
    await action_resolution_service.initialize()

    # Test game state
    game_state = create_example_game_state()

    # Test actions
    test_actions = [
        "I attack the goblin with my sword",
        "I swing my sword at the goblin"
    ]

    for action in test_actions:
        print(f"\n🎮 Testing action: '{action}'")
        print("-" * 30)

        result = await action_resolution_service.resolve_action(
            player_action=action,
            game_state=game_state.copy(),
            correlation_id="test_123"
        )

        if result.get('error'):
            print(f"❌ Error: {result['error']}")
        print()


if __name__ == "__main__":
    asyncio.run(test_action_resolution())

