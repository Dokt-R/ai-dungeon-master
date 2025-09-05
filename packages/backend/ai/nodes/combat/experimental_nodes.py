"""
Temporary file used for testing
"""
from typing import Any, Dict

from your_app.database import get_db_session  # Your DB session

from packages.backend.ai.tools import DiceRoller
from packages.backend.components.game_state_manager import GameStateService
from packages.shared.models import MinimalGameState


async def initiative_node_with_db(state: MinimalGameState) -> Dict[str, Any]:
    """Initiative node using existing database"""
    

    
    # Get database session (however you handle this in your API)
    db_session = get_db_session()
    game_service = GameStateService(db_session)
    
    try:
        # Get all characters in the campaign
        characters = await game_service.get_campaign_characters(state['campaign_id'])
        
        if not characters:
            return {'action_result': 'No characters found in campaign'}
        
        # Roll initiative for each character
        dice_roller = DiceRoller()
        initiative_results = {}
        
        for character in characters:
            roll = await dice_roller.roll_dice("1d20")
            total = roll['total'] + character['dex_modifier']
            initiative_results[character['id']] = total
        
        # Update database with initiative order
        round_order = await game_service.update_initiative_order(
            state['campaign_id'], 
            initiative_results
        )
        
        # Create result message
        result_lines = ["🎲 **Initiative Order:**"]
        for i, char_id in enumerate(round_order, 1):
            char = next(c for c in characters if c['id'] == char_id)
            result_lines.append(
                f"{i}. {char['name']} ({initiative_results[char_id]})"
            )
        
        result = "\n".join(result_lines)
        
        # Log the action
        await game_service.log_action(
            state['campaign_id'],
            None,  # Initiative is campaign-wide
            state['discord_user_id'],
            state['discord_channel_id'],
            "roll initiative",
            {'intent': 'combat', 'action_type': 'initiative'},
            result,
            {'initiative_rolls': initiative_results}
        )
        
        return {
            'action_result': result,
            'dice_results': {'initiative': initiative_results}
        }
    
    finally:
        db_session.close()

async def combat_node_with_db(state: MinimalGameState) -> Dict[str, Any]:
    """Combat node using existing database"""
    
    db_session = get_db_session()
    game_service = GameStateService(db_session)
    
    try:
        # Get current campaign context
        campaign_context = await game_service.get_campaign_context(state['campaign_id'])
        
        if not campaign_context['in_combat']:
            return {'action_result': 'Not currently in combat. Use `/initiative` to start combat.'}
        
        current_char_id = campaign_context['current_character_turn']
        if current_char_id != state['character_id']:
            current_char = await game_service.get_character_combat_data(current_char_id)
            return {
                'action_result': f"It's {current_char['name']}'s turn, not yours!"
            }
        
        # Get attacker data
        attacker = await game_service.get_character_combat_data(state['character_id'])
        if not attacker:
            return {'action_result': 'Character not found'}
        
        # Extract target from parsed intent
        target_name = state.get('parsed_intent', {}).get('target')
        if not target_name:
            return {'action_result': 'No target specified'}
        
        # Find target character (simple name matching - you might want to improve this)
        campaign_chars = await game_service.get_campaign_characters(state['campaign_id'])
        target = None
        for char in campaign_chars:
            if target_name.lower() in char['name'].lower():
                target = await game_service.get_character_combat_data(char['id'])
                break
        
        if not target:
            return {'action_result': f'Target "{target_name}" not found'}
        
        # Simple combat resolution
        damage = 8  # You can enhance this with proper D&D rules
        new_hp = max(0, target['hp'] - damage)
        
        # Update target's HP
        await game_service.update_character_hp(target['id'], new_hp)
        
        result = f"⚔️ {attacker['name']} attacks {target['name']} for {damage} damage!\n"
        result += f"🩸 {target['name']} HP: {new_hp}/{target['max_hp']}"
        
        if new_hp <= 0:
            result += f"\n💀 {target['name']} is defeated!"
        
        # Log the action
        await game_service.log_action(
            state['campaign_id'],
            state['character_id'],
            state['discord_user_id'],
            state['discord_channel_id'],
            state['player_action'],
            state['parsed_intent'],
            result,
            {'damage': damage}
        )
        
        return {
            'action_result': result,
            'dice_results': {'damage': damage}
        }
    
    finally:
        db_session.close()