from packages.backend.ai.graphs.subgraphs.combat_subgraph import (
    get_combat_subgraph,
    should_continue_combat,
)
from packages.backend.ai.testing.factories import create_test_minimal_game_state


def test_should_continue_combat_continue():
    """Test that the combat continues when conditions are met."""
    state = create_test_minimal_game_state()
    result = should_continue_combat(state)
    assert result == "process_turn"

def test_should_continue_combat_exit_early():
    """Test that combat ends when exit_early is true."""
    state = create_test_minimal_game_state(exit_early=True)
    result = should_continue_combat(state)
    assert result == "end_combat"

def test_get_combat_subgraph_structure():
    """Test the structure of the compiled combat subgraph."""
    combat_subgraph = get_combat_subgraph()
    
    # Check that all expected nodes are present
    expected_nodes = [
        "initialize_combat",
        "surprise_check",
        "roll_initiative",
        "process_turn",
        "resolve_combat_action",
        "death_save",
        "end_turn",
        "narrate_combat_event",
        "end_combat",
    ]
    for node in expected_nodes:
        assert node in combat_subgraph.nodes