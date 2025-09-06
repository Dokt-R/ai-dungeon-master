import pytest

from packages.backend.ai.graphs.action_resolution import route_by_intent
from packages.shared.models.langgraph_state_models import MinimalGameState


@pytest.mark.asyncio
async def test_route_by_intent_combat():
    """Test that combat intent routes to combat_subgraph."""
    state = MinimalGameState(
        campaign_id=1,
        character_id=1,
        discord_user_id="test_user",
        discord_channel_id="test_channel",
        correlation_id="test_correlation",
        player_action="I attack the goblin",
        parsed_intent={"action_type": "combat"},
        action_result=None,
        dice_results=None,
        exit_early=False,
        error=None,
    )
    route = await route_by_intent(state)
    assert route == "combat_subgraph"


@pytest.mark.asyncio
async def test_route_by_intent_exploration():
    """Test that exploration intent routes to exploration_node."""
    state = MinimalGameState(
        campaign_id=1,
        character_id=1,
        discord_user_id="test_user",
        discord_channel_id="test_channel",
        correlation_id="test_correlation",
        player_action="I look around the room",
        parsed_intent={"action_type": "exploration"},
        action_result=None,
        dice_results=None,
        exit_early=False,
        error=None,
    )
    route = await route_by_intent(state)
    assert route == "exploration_node"


@pytest.mark.asyncio
async def test_route_by_intent_interaction():
    """Test that interaction intent routes to interaction_node."""
    state = MinimalGameState(
        campaign_id=1,
        character_id=1,
        discord_user_id="test_user",
        discord_channel_id="test_channel",
        correlation_id="test_correlation",
        player_action="I talk to the merchant",
        parsed_intent={"action_type": "interaction"},
        action_result=None,
        dice_results=None,
        exit_early=False,
        error=None,
    )
    route = await route_by_intent(state)
    assert route == "interaction_node"


@pytest.mark.asyncio
async def test_route_by_intent_error():
    """Test that an error in the state routes to error_handler."""
    state = MinimalGameState(
        campaign_id=1,
        character_id=1,
        discord_user_id="test_user",
        discord_channel_id="test_channel",
        correlation_id="test_correlation",
        player_action="I do something weird",
        parsed_intent=None,
        action_result=None,
        dice_results=None,
        exit_early=False,
        error={"error_code": "some_error", "details": {}},
    )
    route = await route_by_intent(state)
    assert route == "error_handler"
