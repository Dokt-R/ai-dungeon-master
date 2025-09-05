"""
Unit tests for the combat_initialization_node module.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.backend.ai.nodes.combat.combat_initiative_node import (
    roll_initiative_node,
)
from packages.backend.ai.testing.factories import create_test_state_for_initiative_roll
from packages.shared.models.langgraph_state_models import (
    CombatParticipant,
    CombatState,
)


@pytest.mark.asyncio
async def test_initialize_combat_node(mock_game_state_service: MagicMock):
    """
    Tests that initialize_combat_node correctly creates a combat state
    from player, NPC, and enemy keys in the game state, including a hostile NPC.
    """
    # Arrange
    state = create_test_state_for_initiative_roll()

    # Act
    result = await roll_initiative_node(state, game_service=mock_game_state_service)

    # Assert
    assert "combat_state" in result
    combat_state = result["combat_state"]

    assert isinstance(combat_state, CombatState)

    # Check participants
    assert len(combat_state.participants) == 4


    # Check active participants
    assert len(combat_state.active_participants) == 4


    # Check other state properties
    assert combat_state.current_round == 1
    assert combat_state.combat_phase == "initiative"
    assert combat_state.combat_started is True
    assert combat_state.combat_ended is False

    initiatives = [entry['initiative'] for entry in combat_state.initiative_order]

    assert initiatives == sorted(initiatives, reverse=True)