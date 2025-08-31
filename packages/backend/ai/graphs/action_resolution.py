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
from typing import Any, Dict, List, Optional, Tuple

from packages.backend.ai.constants.actions import ROUTE_MAPPING
from packages.backend.ai.state import ActionResolutionState, ParsedIntent
from packages.backend.ai.state.base_state import Character, Item, Attack, InteractionType, Condition
from packages.backend.ai.state.environment_state import TacticalRoom, InteractiveObject, EnvironmentalEffect, TerrainType
from packages.backend.ai.state.game_state import GameState as GraphGameState # Import GameState for LangGraph type system

# LangGraph imports
try:
    from langgraph.graph import END, StateGraph
    LANGGRAPH_AVAILABLE = True
    GameState = GraphGameState  # Make it available as GameState
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    # Fallback types if imports fail
    GameState = dict

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
from packages.backend.components.observability_service import observability_service
from packages.shared.errors import ErrorCode
from packages.shared.logging_config import configure_logging, get_logger
import random # For dynamic room descriptions

configure_logging(level="DEBUG")
logger = get_logger(__name__)


async def route_by_intent(state: ActionResolutionState) -> str:
    """Route to appropriate node based on parsed intent or error state."""
    if state.get("error"):
        return "error_handler"

    if not state.get("parsed_intent"):
        state["error"] = {
            "error_code": ErrorCode.INTENT_PARSING_FAILED,
            "details": {"player_action": state.get("player_action")},
        }
        return "error_handler"

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
        combat_subgraph = get_combat_subgraph()
        workflow.add_node("combat_subgraph", combat_subgraph)
        workflow.add_node("exploration_node", exploration_node)
        workflow.add_node("interaction_node", interaction_node)  # New node for interactions
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
                # MAYBE: Add Social Node and Error Handler specific routes
            }
        )

        # All action nodes converge to update_state
        workflow.add_edge("combat_subgraph", "update_state")
        workflow.add_edge("exploration_node", "update_state")
        workflow.add_edge("interaction_node", "update_state")
        workflow.add_edge("error_handler", "update_state")

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
def create_example_game_state() -> GameState:
    """Create example game state for testing using enhanced D&D 5e schema."""
    
    # Create player character
    player_character = Character(
        name="Roric",
        hp=12,
        max_hp=12,
        ac=14,
        speed=30,
        strength=14,
        dexterity=13,
        constitution=14,
        intelligence=10,
        wisdom=12,
        charisma=8,
        attacks=[
            Attack(
                name="Shortsword",
                bonus=4,  # +2 str mod, +2 proficiency
                damage="1d6+2",
                damage_type="piercing",
                range=5
            )
        ],
        proficiency_bonus=2,
        conditions=[],
        is_alive=True,
        is_hostile=False,
        inventory=[
            Item(
                name="Sword",
                type="weapon",
                weight=3.0,
                value=50,
                description="A simple iron shortsword.",
                source="SRD",
                quantity=1,
                is_stackable=False,
                rarity="common",
                requires_attunement=False,
                effects={},
                interactions={},
                properties={"weapon_type": "shortsword"},
                equipped=False
            ),
            Item(
                name="Shield",
                type="armor",
                weight=6.0,
                value=30,
                description="A stout wooden shield.",
                source="SRD",
                quantity=1,
                is_stackable=False,
                rarity="common",
                requires_attunement=False,
                effects={},
                interactions={},
                properties={"armor": 2},
                equipped=False
            ),
            Item(
                name="Healing Potion",
                type="consumable",
                weight=0.5,
                value=50,
                description="A red potion that restores health.",
                source="SRD",
                quantity=1,
                is_stackable=True,
                rarity="common",
                requires_attunement=False,
                effects={"on_use": {"heal": "2d4+2"}},
                interactions={InteractionType.USE: {"effect": "heal"}},
                properties={},
                equipped=False
            ),
            Item(
                name="Key",
                type="key",
                weight=0.1,
                value=25,
                description="A simple iron key.",
                source="SRD",
                quantity=1,
                is_stackable=False,
                rarity="common",
                requires_attunement=False,
                effects={},
                interactions={InteractionType.USE: {"unlocks": "some_lock"}},
                properties={},
                equipped=False
            )
        ],
        equipped_items={},
        wallet={"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0},
    )

    # Create NPC (Goblin)
    goblin_character = Character(
        name="Goblin",
        hp=7,
        max_hp=7,
        ac=15,
        speed=30,
        strength=8,
        dexterity=14,
        constitution=10,
        intelligence=10,
        wisdom=8,
        charisma=8,
        attacks=[
            Attack(
                name="Scimitar",
                bonus=4,
                damage="1d6+2",
                damage_type="slashing",
                range=5
            )
        ],
        proficiency_bonus=2,
        conditions=[],
        is_alive=True,
        is_hostile=True,
        inventory=[],
        equipped_items={},
        wallet={"cp": 5, "sp": 0, "ep": 0, "gp": 0, "pp": 0},
    )

    # Create interactive objects
    iron_chest = InteractiveObject(
        name="Iron Chest",
        description={
            "default": "a sturdy iron chest with an intricate lock",
            "unlocked": "an unlocked iron chest",
            "open": "an open chest containing treasures",
            "trapped": "a chest with a visible poison dart trap!"
        },
        current_state="default",
        interactions={
            InteractionType.EXAMINE: {
                "effects": [{"type": "skill_check", "skill": "investigation", "dc": 12,
                           "success": {"reveal": "trap", "message": "You spot a poison dart trap!"},
                           "failure": {"message": "The chest looks valuable."}}]
            },
            InteractionType.USE: {
                "requires": {"item": "golden_key"},
                "next_state": "unlocked",
                "message": "The key turns with a satisfying click!"
            },
            InteractionType.OPEN: {
                "requires": {"state": "unlocked"},
                "next_state": "open",
                "message": "The chest creaks open, revealing its contents!"
            }
        },
        state_transitions={},
        properties={"locked": True, "trap_present": True}
    )

    # Create environmental effects
    goblin_reinforcements_effect = EnvironmentalEffect(
        name="Goblin Reinforcements",
        trigger_condition="every_n_turns",
        trigger_frequency=5,
        effect_type="spawn",
        effect_data={"spawn": "goblin_warrior", "location": "entrance"},
        warning_signs=[
            "You hear footsteps echoing from the entrance...",
            "The footsteps grow louder!",
            "Something is coming!"
        ],
        active=True,
        turns_until_trigger=5
    )

    # Create the TacticalRoom
    dungeon_room = TacticalRoom(
        name="Goblin's Lair",
        base_description="A damp stone chamber lit by a flickering torch.",
        conditional_descriptions=[
            ("goblin_dead", "The goblin's body lies crumpled on the floor."),
            ("chest_open", "The chest stands open, revealing its treasures."),
            ("hp<5", "Your vision blurs from your wounds."),
            ("trap_triggered", "Poison darts stick out from the walls!")
        ],
        lighting="dim",
        sounds=["dripping water", "distant scratching", "your own breathing"],
        smells=["mildew", "goblin stench", "old leather"],
        zones={
            "entrance": {"terrain": TerrainType.NORMAL, "cover": "none", "elevation": 0},
            "center": {"terrain": TerrainType.NORMAL, "cover": "none", "elevation": 0},
            "chest_area": {"terrain": TerrainType.DIFFICULT, "cover": "half", "elevation": 0},
            "goblin_corner": {"terrain": TerrainType.NORMAL, "cover": "three_quarters", "elevation": 5}
        },
        positions={"player": "entrance", "goblin_1": "goblin_corner"},
        objects=[iron_chest],
        environmental_effects=[goblin_reinforcements_effect],
        flags=set()
    )

    return GameState(
        player=player_character.to_dict(),
        npcs={"goblin_1": goblin_character.to_dict()},
        current_room_id="goblin_lair",
        rooms={"goblin_lair": dungeon_room.model_dump()}, # Convert TacticalRoom to dict
        quest_flags={"has_key": False, "chest_opened": False, "goblin_defeated": False},
        completed_objectives=[],
        in_combat=False,
        combat_order=None,
        current_turn=None,
        recent_actions=[],
        narrative_tone="heroic",
        turn_count=0,
        session_id="enhanced_micro_adventure",
        difficulty="medium"
    )


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
        {"action": "I attack the goblin with my sword", "expected_route": "combat_subgraph", "category": "Combat"},
        # {"action": "I swing my sword at the goblin", "expected_route": "combat_subgraph", "category": "Combat"},

        # # Interaction actions (should route to interaction_node)
        # {"action": "I use the key on the chest", "expected_route": "interaction_node", "category": "Interaction"},
        # {"action": "I take the silver coin", "expected_route": "interaction_node", "category": "Interaction"},
        # {"action": "I say hello to the goblin", "expected_route": "interaction_node", "category": "Interaction"},
        # {"action": "I use the healing potion", "expected_route": "interaction_node", "category": "Interaction"},
        # {"action": "I open the chest", "expected_route": "interaction_node", "category": "Interaction"},


        # # Exploration actions (should route to exploration_node)
        # {"action": "I search the room", "expected_route": "exploration_node", "category": "Exploration"},
        # {"action": "I examine the chest", "expected_route": "exploration_node", "category": "Exploration"},
        # {"action": "I look around the room", "expected_route": "exploration_node", "category": "Exploration"},
        # {"action": "I stand up", "expected_route": "exploration_node", "category": "Exploration"}
    ]

    # Get current room information
    current_room = TacticalRoom(**game_state['rooms'][game_state['current_room_id']]) # Re-instantiate for methods
    
    # Explicitly convert inventory items to Item models for the test's Character instantiation
    player_char_data = game_state['player'].copy()
    player_char_data['inventory'] = [Item(**item_data) for item_data in player_char_data['inventory']]
    player_char = Character(**player_char_data)

    print(f"🏃 Player Character: {player_char.name}")
    print(f"❤️  Health: {player_char.hp}/{player_char.max_hp}")
    print(f"🛡️ AC: {player_char.ac}")
    
    inventory_display = ', '.join([item.name for item in player_char.inventory]) if player_char.inventory else 'Empty'
    print(f"🎒 Inventory: {inventory_display}")
    print(f"📍 Current Room: {current_room.name}")
    
    room_objects_display = ', '.join([obj.name for obj in current_room.objects]) if current_room.objects else 'None'
    print(f"📍 Room objects: {room_objects_display}")
    
    chest_obj = next((obj for obj in current_room.objects if obj.name == "Iron Chest"), None)
    chest_status = "Not found"
    if chest_obj:
        if chest_obj.current_state == "open":
            chest_status = "🔓 Open"
        elif chest_obj.properties.get("locked"):
            chest_status = "🔒 Locked"
        else:
            chest_status = "   box Unlocked"
    print(f"💰 Chest: {chest_status}")
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
            # Pass a copy of the game_state to avoid side effects between tests
            result = await action_resolution_service.resolve_action(
                player_action=action,
                game_state=game_state.copy(),
                correlation_id=f"test_{hash(action) % 1000}"
            )

            if result.get('error'):
                print(f"❌ Error: {result['error']}")
                continue

            # Show routing information
            action_type = result.get('parsed_intent', {}).get('action_type', 'unknown')
            narrative = result.get('narrative', 'No response')
            routed_to = result.get('performance', {}).get('routing_path', 'unknown')

            print(f"🎯 Action Type: {action_type}")
            print(f"🎭 Routed to: {routed_to}")
            print(f"📖 Response: {narrative}")

            # Show state changes if any (compare key properties)
            updated_game_state = result.get('updated_game_state')
            if updated_game_state and updated_game_state != game_state:
                state_changes = []
                
                # Explicitly convert inventory items for updated_player_char and original_player_char
                updated_player_data = updated_game_state['player'].copy()
                updated_player_data['inventory'] = [Item(**item_data) for item_data in updated_player_data['inventory']]
                updated_player_char = Character(**updated_player_data)

                original_player_data = game_state['player'].copy()
                original_player_data['inventory'] = [Item(**item_data) for item_data in original_player_data['inventory']]
                original_player_char = Character(**original_player_data)

                if updated_player_char.hp != original_player_char.hp:
                    state_changes.append(f"HP: {original_player_char.hp} → {updated_player_char.hp}")
                
                if updated_player_char.wallet != original_player_char.wallet:
                    state_changes.append(f"Wallet: {original_player_char.wallet} → {updated_player_char.wallet}")

                if updated_player_char.inventory != original_player_char.inventory:
                    state_changes.append(f"Inventory changed.")

                updated_room = TacticalRoom(**updated_game_state['rooms'][updated_game_state['current_room_id']])
                original_room = TacticalRoom(**game_state['rooms'][game_state['current_room_id']])

                if updated_room.objects != original_room.objects:
                    state_changes.append(f"Room objects changed.")
                
                if updated_game_state['quest_flags'] != game_state['quest_flags']:
                    state_changes.append(f"Quest flags changed.")


                if state_changes:
                    print(f"📊 State Changes: {', '.join(state_changes)}")
                else:
                    print("📊 No significant state changes detected.")

            if routed_to == expected_route:
                print("✅ Routing test passed.")
                success_count += 1
            else:
                print(f"❌ Routing test FAILED. Expected: {expected_route}, Got: {routed_to}")


        except Exception as e:
            print(f"❌ Test failed: {str(e)}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")
    print(f"🎯 Enhanced conditional routing implementation provides flexible action routing!")


# Global service instance
action_resolution_service = ActionResolutionService()


if __name__ == "__main__":
    asyncio.run(test_action_resolution())

