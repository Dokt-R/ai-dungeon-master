"""
Unit tests for the combat_initialization_node module.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.backend.ai.nodes.combat.combat_initialization_node import (
    initialize_combat_node,
)
from packages.backend.ai.testing.factories import create_test_state_for_combat_init
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
    state, mock_characters = create_test_state_for_combat_init()

    # Create mock CombatParticipant objects that the service should return
    participants_map = {}
    for key, char in mock_characters.items():
        creature_type = "player"  # Default
        if "npc" in key:
            creature_type = "npc"
        if char.is_hostile:
            creature_type = "enemy"

        participants_map[key] = CombatParticipant(
            participant_id=char.character_id,
            campaign_id=1,
            creature_type=creature_type,
            creature_id=char.character_id,
            creature_name=char.name,
            current_health=char.hp,
            max_health=char.max_hp,
            initiative_modifier=char.dex_modifier,
            temp_hp=0,
        )

    # Mock the service to return the appropriate CombatParticipant for each key
    async def mock_char_to_participant(key: str, creature_type: str = None):
        return participants_map.get(key)

    mock_game_state_service.character_to_combat_participant = AsyncMock(
        side_effect=mock_char_to_participant
    )

    # Act
    result = await initialize_combat_node(state, game_service=mock_game_state_service)

    # Assert
    assert "combat_state" in result
    combat_state = result["combat_state"]

    assert isinstance(combat_state, CombatState)

    # Check participants
    assert len(combat_state.participants) == 4

    player_p = participants_map["character_1"]
    friendly_npc_p = participants_map["character_2"]
    hostile_npc_p = participants_map["character_3"]
    enemy_p = participants_map["character_4"]

    expected_participants = {
        player_p.participant_key: player_p,
        friendly_npc_p.participant_key: friendly_npc_p,
        hostile_npc_p.participant_key: hostile_npc_p,
        enemy_p.participant_key: enemy_p,
    }
    assert combat_state.participants == expected_participants

    # Check active participants
    assert len(combat_state.active_participants) == 4
    assert set(combat_state.active_participants) == {
        player_p.participant_key,
        friendly_npc_p.participant_key,
        hostile_npc_p.participant_key,
        enemy_p.participant_key,
    }

    # Check other state properties
    assert combat_state.current_round == 1
    assert combat_state.combat_phase == "initialize"
    assert combat_state.combat_started is True
    assert combat_state.combat_ended is False