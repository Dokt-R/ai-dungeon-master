from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, Optional

from packages.backend.components.character_manager import CharacterManager
from packages.shared.models.langgraph_state_models import CombatParticipant

from .core_db_models import Character
from .langgraph_state_models import CampaignGameState, MinimalGameState

if TYPE_CHECKING:
    from packages.backend.components.game_state_manager import GameStateService

class CombatAdapters:
    """Adapter for integrating CampaignGameState with LangGraph workflows."""
    @staticmethod
    async def character_to_combat_participant(
        game_state_service: "GameStateService",
        character_id: int
    ) -> CombatParticipant:
        """
        Transform a Character from database into a CombatParticipant for combat scenarios.
        """
        # Retrieve the character from the database
        character = await CharacterManager.get_character_by_id(character_id)
                
        # Create CombatParticipant with mapped data
        combat_participant = CombatParticipant(
            campaign_id=character.campaign_id,
            participant_type="player",
            participant_id=character.character_id,
            participant_name=character.name,
            current_health=character.hp,
            max_health=character.max_hp,
            status_conditions=character.conditions,
            is_active=character.in_game,
            initiative_modifier=character.dex_modifier,  # Use DEX modifier for initiative
        )
        
        # Save the combat participant to the database
        await game_state_service.session.add(combat_participant)
        await game_state_service.session.commit()
        await game_state_service.session.refresh(combat_participant)
        
        return combat_participant

    @staticmethod
    async def npc_to_combat_participant(
        game_state_service: "GameStateService",
        npc_id: int
    ) -> CombatParticipant:
        """
        Transform an NPC from database into a CombatParticipant for combat scenarios.
        """

        #! Needs Table
        npc = await CharacterManager.get_npc_by_id(npc_id)
                
        # Create CombatParticipant with mapped data
        combat_participant = CombatParticipant(
            campaign_id=npc.campaign_id,
            participant_type="npc",
            participant_id=npc.npc_id,
            participant_name=npc.name,
            current_health=npc.hp,
            max_health=npc.max_hp,
            status_conditions=npc.conditions,
            is_active=npc.in_game,
            initiative_modifier=npc.dex_modifier,  # Use DEX modifier for initiative
        )
        
        # Save the combat participant to the database
        await game_state_service.session.add(combat_participant)
        await game_state_service.session.commit()
        await game_state_service.session.refresh(combat_participant)
        
        return combat_participant
    
    staticmethod
    async def monster_to_combat_participant(
        game_state_service: "GameStateService",
        enemy_id: int
    ) -> CombatParticipant:
        """
        Transform a Monster from database into a CombatParticipant for combat scenarios.
        """
        
        #! Needs Table
        enemy = await CharacterManager.get_character_by_id(enemy_id)
        
        # Determine participant type

        
        # Determine participant type based on enemy properties
        #! Should check both all 3 tables and determine with a is hostile flag, to ensure characters under spells and so on
        
        # Create CombatParticipant with mapped data
        combat_participant = CombatParticipant(
            campaign_id=enemy.campaign_id,
            participant_type="enemy",
            participant_id=enemy.enemy_id,
            participant_name=enemy.name,
            current_health=enemy.hp,
            max_health=enemy.max_hp,
            status_conditions=enemy.conditions,
            is_active=enemy.in_game,
            initiative_modifier=enemy.dex_modifier,  # Use DEX modifier for initiative
        )
        
        # Save the combat participant to the database
        await game_state_service.session.add(combat_participant)
        await game_state_service.session.commit()
        await game_state_service.session.refresh(combat_participant)
        
        return combat_participant