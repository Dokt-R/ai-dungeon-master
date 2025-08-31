import pytest
from packages.backend.ai.graphs.subgraphs.combat_subgraph import get_combat_subgraph
from packages.backend.ai.state import ActionResolutionState, GameState, create_micro_adventure_state

@pytest.fixture
def initial_state() -> ActionResolutionState:
    """Provides a fresh game state for each test."""
    game_state = create_micro_adventure_state()
    return ActionResolutionState(
        player_action="",
        game_state=game_state,
        combat_state=None,
        parsed_intent=None,
        action_result=None,
        narrative_response=None,
        error=None,
        correlation_id="test-combat-subgraph",
        trace_context=None,
        performance_metrics=None,
    )

@pytest.mark.asyncio
async def test_combat_subgraph_initialization(initial_state):
    """Tests that the combat subgraph can be compiled and initialized."""
    combat_subgraph = get_combat_subgraph()
    assert combat_subgraph is not None, "Subgraph should compile without errors."

@pytest.mark.asyncio
async def test_full_combat_flow(initial_state):
    """
    Tests a complete combat scenario from initialization to conclusion.
    This is an integration test for the subgraph's logic.
    """
    combat_subgraph = get_combat_subgraph()

    # 1. Initialize Combat
    initial_state["parsed_intent"] = {"action_type": "enter_combat"} # Simulate entering combat
    result_state = await combat_subgraph.ainvoke(initial_state)
    
    assert result_state["combat_state"] is not None, "Combat state should be initialized."
    assert len(result_state["combat_state"]["participants"]) == 2, "Should have player and one goblin."
    assert result_state["combat_state"]["current_round"] == 1, "Should start at round 1."

    # For this test, we'll manually step through the graph's logic since we don't have a live game loop.
    # In a real application, the graph would be invoked repeatedly.
    
    # Assume player attacks goblin
    result_state["player_action"] = "I attack the goblin"
    result_state["parsed_intent"] = {"action_type": "attack", "target": "Goblin"}

    # Keep running turns until combat is over
    for _ in range(10): # Max 10 rounds to prevent infinite loops
        if result_state.get("combat_over"):
            break
        
        result_state = await combat_subgraph.ainvoke(result_state)

    assert result_state.get("combat_over"), "Combat should have concluded."
    
    # Check if one of the parties is defeated
    player_alive = any(p["type"] == "player" and "dead" not in p["status_conditions"] for p in result_state["combat_state"]["participants"].values())
    enemies_alive = any(p["type"] == "enemy" and "dead" not in p["status_conditions"] for p in result_state["combat_state"]["participants"].values())
    
    assert player_alive or not enemies_alive, "Either the player or all enemies should be defeated."
