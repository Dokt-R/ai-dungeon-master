import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from packages.backend.components.game_operations.combat_operations import (
    roll_initiative_for_participants,
)
from packages.shared.db import get_async_session_dependency
from packages.shared.models.core_db_models import (
    ActionHistory,
    Character,
)
from packages.shared.models.game.loaders import CombatCreatureLoader
from packages.shared.models.langgraph_state_models import (
    CombatParticipant,
    MinimalGameState,
)
from packages.shared.models.not_utilized import CampaignGameState


class GameStateService:
    """Service layer for game state operations"""

    def __init__(self, session: AsyncSession = Depends(get_async_session_dependency)):
        self.session = session

    async def character_to_combat_participant(
        self, participant_key: str, campaign_id: int
    ) -> CombatParticipant:
        # player_id is a character

        """Factory function to create a CombatParticipant from a creature"""
        creature_type, creature_id = participant_key.split("_")

        # Load the source creature
        loader = CombatCreatureLoader(self.session)
        creature = loader.load_creature(participant_key)

        participant = CombatParticipant(
            participant_key=participant_key,
            campaign_id=campaign_id,
            creature_type=creature_type,
            creature_id=int(creature_id),
            creature_name=creature.name,
            current_hp=creature.hp,
            max_hp=creature.max_hp,
            initiative_modifier=creature.dex_modifier,
        )

        #! populate and create or update the CombatParticipant table
        # get a returned dict of "name": combat_participants_id
        # append where needed
        return participant

    async def get_campaign_context(self, campaign_id: int) -> Dict[str, Any]:
        """Get current campaign state and context"""

        # Get campaign game state
        game_state = (
            self.session.execute(
                select(CampaignGameState).where(
                    CampaignGameState.campaign_id == campaign_id
                )
            )
            .scalars()
            .first()
        )

        if not game_state:
            # Create initial game state
            game_state = CampaignGameState(campaign_id=campaign_id)
            self.session.add(game_state)
            self.session.commit()

        return {
            "current_room_id": game_state.current_room_id,
            "current_turn": game_state.current_turn,
            "in_combat": game_state.in_combat,
            "round_order": json.loads(game_state.round_order or "[]"),
            "current_character_turn": game_state.current_character_turn,
        }

    async def get_character_by_id(self, character_id: int) -> Optional[Character]:
        """Get a character by their ID."""
        statement = select(Character).where(Character.character_id == character_id)
        results = await self.session.execute(statement)
        result = results.scalars().first()
        return result

    async def get_character_by_name(
        self, name: str, campaign_id: Optional[int] = None
    ) -> Optional[Character]:
        """Get a character by name, optionally within a specific campaign."""
        query = select(Character).where(Character.name == name)
        if campaign_id:
            query = query.where(Character.campaign_id == campaign_id)
        return self.session.execute(query).first()

    async def get_campaign_characters(self, campaign_id: int) -> List[Character]:
        """Get all characters in a campaign."""
        return self.session.execute(
            select(Character).where(Character.campaign_id == campaign_id)
        ).all()

    async def update_character(self, character: Character) -> Character:
        """Update an existing character."""
        self.session.add(character)
        self.session.commit()
        self.session.refresh(character)
        return character

    async def create_character(self, character: Character) -> Character:
        """Create a new character and add it to state."""
        self.session.add(character)
        await self.session.commit()
        await self.session.refresh(character)

    async def add_combat_participant(
        self, state: MinimalGameState, character: Character
    ) -> Character:
        """Create a new character and add it to state."""
        existing_participants = state.get("combat_participants") or []
        updated_participants = existing_participants + [{"id": character.character_id}]
        print(state)
        new_state = {
            **state,
            "combat_participants": updated_participants,
            # "character_id": character.character_id,
            # "action_result": f"Character '{character.name}' created and added to combat!",
            # "dice_results": None,
            # "error": None,
        }
        # new_state = state | {"combat_participants": character.character_id}
        print(new_state)
        return new_state

    async def delete_character(self, character_id: int):
        """Delete a character by ID."""
        character = self.session.execute(
            select(Character).where(Character.character_id == character_id)
        ).first()
        if character:
            self.session.delete(character)
            self.session.commit()

    async def get_campaign_state(self, campaign_id: int) -> Optional[CampaignGameState]:
        """Get the campaign game state."""
        return self.session.execute(
            select(CampaignGameState).where(
                CampaignGameState.campaign_id == campaign_id
            )
        ).first()

    async def update_campaign_state(
        self, minimal_state: MinimalGameState
    ) -> MinimalGameState:
        """Update the campaign game state using MinimalGameState."""
        campaign_game_state = self.session.execute(
            select(CampaignGameState).where(
                CampaignGameState.campaign_id == minimal_state["campaign_id"]
            )
        ).first()

        if not campaign_game_state:
            # If no existing CampaignGameState, create a new one
            campaign_game_state = CampaignGameState(
                campaign_id=minimal_state["campaign_id"],
                current_character_turn=minimal_state.get("character_id"),
                updated_at=datetime.utcnow(),
            )
        else:
            # Update existing fields from MinimalGameState
            campaign_game_state.current_character_turn = minimal_state.get(
                "character_id"
            )
            campaign_game_state.updated_at = datetime.utcnow()

        self.session.add(campaign_game_state)
        await self.session.commit()
        await self.session.refresh(campaign_game_state)
        return minimal_state  # Return the input minimal_state, as the persistence is handled

    async def log_action(
        self,
        campaign_id: int,
        character_id: Optional[int],
        discord_user_id: str,
        discord_channel_id: str,
        action_text: str,
        parsed_intent: Dict,
        result: str,
        dice_rolls: Dict = None,
    ):
        """Log action to history."""
        action_log = ActionHistory(
            campaign_id=campaign_id,
            character_id=character_id,
            discord_user_id=discord_user_id,
            discord_channel_id=discord_channel_id,
            action_text=action_text,
            parsed_intent=json.dumps(parsed_intent),
            result=result,
            dice_rolls=json.dumps(dice_rolls or {}),
        )
        self.session.add(action_log)
        self.session.commit()
        self.session.refresh(action_log)
        return action_log

    async def resolve_initiative(self, participants: List[Character]) -> List[Dict]:
        results = roll_initiative_for_participants(participants)
        return results
