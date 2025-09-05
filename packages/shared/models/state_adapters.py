from __future__ import annotations
import json
from typing import Any, Dict, Optional, TYPE_CHECKING

from .langgraph_state_models import MinimalGameState
from packages.shared.models.not_utilized import CampaignGameState


if TYPE_CHECKING:
    from packages.backend.components.game_state_manager import GameStateService


class StateAdapter:
    """Adapter for integrating CampaignGameState with LangGraph workflows."""

    @staticmethod
    def campaign_db_to_minimal_state(
        game_state_service: "GameStateService",
        campaign_id: int,
        discord_user_id: str = "",
        discord_channel_id: str = "",
        correlation_id: str = ""
    ) -> MinimalGameState:
        """Convert CampaignGameState from DB to MinimalGameState for LangGraph."""
        from packages.backend.components.game_state_manager import GameStateService
        # Get campaign context using existing service
        campaign_context = game_state_service.get_campaign_context(campaign_id)

        return MinimalGameState(
            campaign_id=campaign_id,
            character_id=campaign_context.get('current_character_turn'),
            discord_user_id=discord_user_id,
            discord_channel_id=discord_channel_id,
            correlation_id=correlation_id,
            player_action="",  # Will be set by player input
            parsed_intent=None,
            action_result={},
            dice_results={},
            exit_early=False,
            error=None
        )

    @staticmethod
    def minimal_state_to_db_update(minimal_state: MinimalGameState) -> Dict[str, Any]:
        """Convert MinimalGameState changes to database update fields."""
        return {
            "current_character_turn": minimal_state.character_id,
            # Add other mappings as needed based on action results
        }

    @staticmethod
    async def enrich_minimal_state(
        minimal_state: MinimalGameState,
        discord_user_id: str,
        discord_channel_id: str
    ) -> MinimalGameState:
        """Enrich MinimalGameState with Discord context."""
        return MinimalGameState(
            **minimal_state,
            discord_user_id=discord_user_id,
            discord_channel_id=discord_channel_id
        )

    @staticmethod
    def update_from_action_result(
        current_state: MinimalGameState,
        action_result: Dict[str, Any]
    ) -> MinimalGameState:
        """Update MinimalGameState based on action results."""
        return MinimalGameState(
            **current_state,
            action_result=action_result
        )

    @staticmethod
    def update_from_parsed_intent(
        current_state: MinimalGameState,
        parsed_intent: Dict[str, Any]
    ) -> MinimalGameState:
        """Update MinimalGameState with parsed intent."""
        return MinimalGameState(
            **current_state,
            parsed_intent=parsed_intent
        )

    @staticmethod
    def extract_context_from_minimal_state(state: MinimalGameState) -> Dict[str, Any]:
        """Extract context data for node operations."""
        return {
            'campaign_id': state.campaign_id,
            'character_id': state.character_id,
            'discord_user_id': state.discord_user_id,
            'discord_channel_id': state.discord_channel_id,
            'correlation_id': state.correlation_id,
            'player_action': state.player_action,
            'parsed_intent': state.parsed_intent,
        }

    @staticmethod
    def prepare_state_for_logging(state: MinimalGameState, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare state data for action history logging."""
        return {
            'campaign_id': state.campaign_id,
            'character_id': state.character_id,
            'discord_user_id': state.discord_user_id,
            'discord_channel_id': state.discord_channel_id,
            'action_text': state.player_action,
            'parsed_intent': state.parsed_intent or {},
            'result': json.dumps(action_result),
            'dice_rolls': state.dice_results
        }