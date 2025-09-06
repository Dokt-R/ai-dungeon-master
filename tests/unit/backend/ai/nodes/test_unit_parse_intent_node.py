import pytest

from packages.backend.ai.nodes.core.parse_intent_node import parse_intent_node
from tests.utils.factories import create_test_minimal_game_state

pytestmark = pytest.mark.asyncio


async def test_parse_intent_node_combat():
    """Test that parse_intent_node correctly identifies combat intent."""
    state = create_test_minimal_game_state("I attack the goblin with my sword")

    result_state = await parse_intent_node(state)
    assert result_state["parsed_intent"]["intent"] == "combat"
    assert result_state["parsed_intent"]["action_type"] == "attack"
    assert result_state["parsed_intent"]["target"] == "goblin"


async def test_parse_intent_node_exploration():
    """Test that parse_intent_node correctly identifies exploration intent."""
    state = create_test_minimal_game_state("I search the room for traps")

    result_state = await parse_intent_node(state)
    assert result_state["parsed_intent"]["intent"] == "exploration"
    assert result_state["parsed_intent"]["action_type"] == "search"
    assert result_state["parsed_intent"]["target"] == "room"


async def test_parse_intent_node_interaction():
    """Test that parse_intent_node correctly identifies interaction intent."""

    state = create_test_minimal_game_state("I talk to the merchant")

    result_state = await parse_intent_node(state)
    assert result_state["parsed_intent"]["intent"] == "social"
    assert result_state["parsed_intent"]["action_type"] == "talk"
    assert result_state["parsed_intent"]["target"] == "merchant"
