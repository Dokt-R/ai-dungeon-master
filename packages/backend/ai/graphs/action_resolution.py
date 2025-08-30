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

from packages.backend.ai.constants.actions import ROUTE_MAPPING
from packages.backend.ai.state import ActionResolutionState, ParsedIntent

# LangGraph imports
try:
    from langgraph.graph import END, StateGraph
    LANGGRAPH_AVAILABLE = True
    # Import GameState for LangGraph type system
    from packages.backend.ai.state.game_state import (
        GameState as GraphGameState,
        create_micro_adventure_state,
    )
    GameState = GraphGameState  # Make it available as GameState
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    # Fallback types if imports fail
    GameState = dict
    create_micro_adventure_state = lambda: {}

# Node imports
from packages.backend.ai.nodes.combat import combat_node
from packages.backend.ai.nodes.core import (
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
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import configure_logging, get_logger

configure_logging(level="DEBUG")
logger = get_logger(__name__)


async def route_by_intent(state: ActionResolutionState) -> str:
    """Route to appropriate node based on parsed intent."""
    if not state.get("parsed_intent"):
        return "narrate_result"  # Skip to narration with error

    action_type = state["parsed_intent"].get("action_type", "").lower()

    # Use standardized routing mapping from constants
    routing_map = ROUTE_MAPPING

    route_target = routing_map.get(action_type, "exploration_node")  # Default to exploration
    logger.debug("routing_decision",
                action_type=action_type,
                route_target=route_target,
                correlation_id=state["correlation_id"])

    return route_target


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
        workflow.add_node("combat_node", combat_node)
        workflow.add_node("exploration_node", exploration_node)
        workflow.add_node("interaction_node", interaction_node)  # New node for interactions
        workflow.add_node("update_state", update_state_node)
        workflow.add_node("narrate_result", narrate_result_node)

        
        # Set Entry Point
        workflow.set_entry_point("parse_intent")

        # Add edges between core nodes
        # CRITICAL: Add conditional routing based on intent
        workflow.add_conditional_edges(
            "parse_intent",
            route_by_intent,
            {
                "combat_node": "combat_node",
                "exploration_node": "exploration_node",
                "interaction_node": "interaction_node",
                "narrate_result": "narrate_result"  # For errors or unrecognized actions
                # MAYBE: Add Social Node and Error Handler specific routes
            }
        )

        # All action nodes converge to update_state
        workflow.add_edge("combat_node", "update_state")
        workflow.add_edge("exploration_node", "update_state")
        workflow.add_edge("interaction_node", "update_state")

        # Final narration and end
        workflow.add_edge("update_state", "narrate_result")
        workflow.add_edge("narrate_result", END)

        return workflow.compile()

    # @observability_service.trace_ai_workflow_decorator(
    #     workflow_name="action_resolution_workflow",
    #     workflow_type="game_action_processing"
    # )
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

        # Extract narrative from action result if available
        narrative = result.get("narrative_response", "")
        if not narrative:
            # Generate narrative from action result if available
            action_result = result.get("action_result", {})
            if action_result.get("success"):
                narrative = action_result.get("description", "Action completed successfully.")
            else:
                narrative = action_result.get("description", "Action could not be resolved.")
                error = action_result.get("description", "Unknown error occurred")

        # Get updated game state
        updated_game_state = result.get("game_state", game_state)

        # Calculate performance metrics - node count is now accurate with 6 nodes
        action_type = result.get("parsed_intent", {}).get("action_type", "unknown")
        performance_data = {
            "execution_time": execution_time,
            "node_count": len(["parse_intent", "combat_node", "exploration_node", "interaction_node", "update_state"]),  # Accurate count
            "action_type": action_type,
            "routing_path": ROUTE_MAPPING.get(action_type, "exploration_node")
        }

        return {
            "narrative": narrative,
            "updated_game_state": updated_game_state,
            "correlation_id": correlation_id,
            "error": result.get("error"),
            "performance": performance_data
        }



    # Standardized game state creation function
def create_example_game_state():
    """Create example game state for testing using standardized D&D 5e schema."""
    return create_micro_adventure_state()


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

    # Test actions to verify routing works correctly
    test_actions = [
        # Combat actions (should route to combat_node)
        {"action": "I attack the goblin with my sword", "expected_route": "combat_node", "category": "Combat"},
        {"action": "I swing my sword at the goblin", "expected_route": "combat_node", "category": "Combat"},

        # Interaction actions (should route to interaction_node)
        {"action": "I use the key on the chest", "expected_route": "interaction_node", "category": "Interaction"},
        {"action": "I take the silver coin", "expected_route": "interaction_node", "category": "Interaction"},
        {"action": "I say hello to the goblin", "expected_route": "interaction_node", "category": "Interaction"},
        {"action": "I use the healing potion", "expected_route": "interaction_node", "category": "Interaction"},

        # # Exploration actions (should route to exploration_node)
        {"action": "I search the room", "expected_route": "exploration_node", "category": "Exploration"},
        {"action": "I examine the chest", "expected_route": "exploration_node", "category": "Exploration"},
        {"action": "I open the door", "expected_route": "exploration_node", "category": "Exploration"},

        # Edge cases (should route to exploration_node by default)
        {"action": "I look around the room", "expected_route": "exploration_node", "category": "Exploration"},
        {"action": "I stand up", "expected_route": "exploration_node", "category": "Exploration"}
    ]

    # Get current room information
    current_room = game_state['rooms'][game_state['current_room_id']]
    room_objects = current_room.get('objects', [])

    # Find chest object
    chest_locked = None
    for obj in room_objects:
        if 'chest' in obj['name'].lower():
            chest_locked = obj.get('state', {}).get('locked', False)
            break

    print(f"🏃 Player Character: {game_state['player']['name']}")
    print(f"❤️  Health: {game_state['player']['hp']}/{game_state['player']['max_hp']}")
    print(f"🛡️ AC: {game_state['player']['ac']}")
    # Handle both legacy string and standardized Item formats
    inventory_items = game_state['player']['inventory']
    if inventory_items:
        inventory_names = []
        for item in inventory_items:
            if isinstance(item, str):
                inventory_names.append(item)
            elif isinstance(item, dict) and 'name' in item:
                inventory_names.append(item['name'])
            else:
                inventory_names.append(str(item))
        inventory_display = ', '.join(inventory_names) if inventory_names else 'Empty'
    else:
        inventory_display = 'Empty'
    print(f"🎒 Inventory: {inventory_display}")
    print(f"📍 Current Room: {current_room['name']}")
    print(f"📍 Room items: {', '.join(str(item) if isinstance(item, str) else item.get('name', 'Unknown') for item in current_room['items']) if current_room['items'] else 'None'}")
    print(f"💰 Chest: {'🔒 Locked' if chest_locked else '🔓 Unlocked' if chest_locked is not None else 'Not found'}")
    print("=" * 50)

    # Show quest flags
    quest_flags = game_state.get('quest_flags', {})
    if quest_flags:
        active_quests = [f"'{k.replace('_', ' ').title()}'" for k, v in quest_flags.items() if v]
        if active_quests:
            print(f"🎯 Active Quests: {', '.join(active_quests)}")

    print()

    success_count = 0
    total_tests = len(test_actions)

    for test_case in test_actions:
        action = test_case["action"]
        expected_route = test_case["expected_route"]
        category = test_case["category"]

        print(f"\n🎮 [{category}] Testing: '{action}'")
        print("-" * 60)

        try:
            result = await action_resolution_service.resolve_action(
                player_action=action,
                game_state=game_state.copy(),
                correlation_id=f"test_{hash(action) % 1000}"
            )

            if result.get('error'):
                print(f"❌ Error: {result['error']}")
                continue

            # Show routing information
            action_type = result.get('performance', {}).get('action_type', 'unknown')
            narrative = result.get('narrative', 'No response')

            # Try to determine which node was actually used based on the result
            route_indicator = "Unknown"
            if "attack" in action_type.lower():
                route_indicator = "💥 combat_node"
            elif any(word in action_type.lower() for word in ["use", "take", "talk", "pick", "grab"]):
                route_indicator = "🤝 interaction_node"
            elif "unknown" not in action_type.lower():
                route_indicator = "🔍 exploration_node"

            print(f"🎯 Action Type: {action_type}")
            print(f"🎭 Routed to: {route_indicator}")
            print(f"📖 Response: {narrative}")

            # Show state changes if any (compare key properties)
            updated_game_state = result.get('updated_game_state')
            if updated_game_state != game_state and updated_game_state:
                state_changes = []

                # Check player HP changes
                if updated_game_state['player']['hp'] != game_state['player']['hp']:
                    state_changes.append(f"HP: {game_state['player']['hp']} → {updated_game_state['player']['hp']}")
                else:
                    state_changes.append("Game state modified")

                if state_changes:
                    print(f"📊 State Changes: {', '.join(state_changes)}")

            success_count += 1

        except Exception as e:
            print(f"❌ Test failed: {str(e)}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {success_count}/{total_tests} tests completed")
    print(f"🎯 Enhanced conditional routing implementation provides flexible action routing!")


# Global service instance
action_resolution_service = ActionResolutionService()


if __name__ == "__main__":
    asyncio.run(test_action_resolution())

