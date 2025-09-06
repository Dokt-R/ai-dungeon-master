"""
Combat Action Resolution Node
"""

from typing import Any, Dict

from sqlmodel import Session, create_engine

from packages.backend.ai.state import ActionResolutionState
from packages.backend.ai.tools import DiceRoller
from packages.backend.components.game_state_manager import GameStateService
from packages.shared.models.core_db_models import Attack


async def resolve_combat_action_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Resolves the specific action taken by the participant (e.g., attack)."""
    # In a real application, the session would be managed by a dependency injection system
    engine = create_engine(
        "sqlite:///./data/srd_database.sqlite"
    )  # Use your actual database URL
    with Session(engine) as session:
        game_state_service = GameStateService(session)

        combat_state = state["combat_state"]
        game_state = state[
            "game_state"
        ]  # This is still the in-memory representation for now
        parsed_intent = state["parsed_intent"]

        if (
            not combat_state
            or not parsed_intent
            or parsed_intent.get("action_type") != "attack"
        ):
            return {}

        dice_roller = DiceRoller()
        active_participant_id = combat_state["active_turn_participant_id"]

        # Retrieve attacker from DB
        attacker_char = await game_state_service.get_character_by_id(
            active_participant_id
        )
        if not attacker_char:
            print(f"---ATTACKER {active_participant_id} NOT FOUND IN DB---")
            return {}

        # Find the target
        target_name = parsed_intent.get("target")
        target_char = await game_state_service.get_character_by_name(
            target_name, campaign_id=game_state["campaign_id"]
        )  # Assuming campaign_id is in game_state

        if not target_char:
            print(f"---TARGET {target_name} NOT FOUND IN COMBAT---")
            return {}

        # Get attacker's primary attack (simplified for now)
        if not attacker_char.attacks:
            print(f"---ATTACKER {attacker_char.name} has no attacks defined---")
            return {}

        # Assuming the first attack in the list is the one used for now
        # In a more complex system, intent parsing would specify which attack
        used_attack: Attack = attacker_char.attacks[0]

        attack_bonus = (
            attacker_char.dex_modifier + attacker_char.proficiency_bonus
        )  # Example: using dex for attack bonus
        defender_ac = target_char.ac
        damage_dice = used_attack.damage

        attack_roll_result = dice_roller.roll_attack(attack_bonus)
        is_critical_hit = (
            attack_roll_result.actual == 20
        )  # Check for natural 20 on the actual d20 roll

        if attack_roll_result.total >= defender_ac:
            actual_damage_dice = damage_dice
            if is_critical_hit:
                # Double the number of damage dice for a critical hit
                num_dice = int(damage_dice.split("d")[0]) if "d" in damage_dice else 1
                rest_of_dice = damage_dice.split("d")[1] if "d" in damage_dice else ""
                actual_damage_dice = f"{num_dice * 2}d{rest_of_dice}"
                print(
                    f"---CRITICAL HIT! {attacker_char.name} rolls with {actual_damage_dice} damage dice!---"
                )

            damage_roll_result = dice_roller.roll_damage(actual_damage_dice)
            target_char.hp -= damage_roll_result.total

            # Ensure HP doesn't go below 0
            target_char.hp = max(0, target_char.hp)

            await game_state_service.update_character(target_char)  # Persist HP change

            print(
                f"---{attacker_char.name} HITS {target_char.name} for {damage_roll_result.total} damage! (Roll: {attack_roll_result.total} vs AC: {defender_ac})---"
            )

            if target_char.hp <= 0:
                if target_char.player_id:  # Check if it's a player character
                    target_char.add_condition("unconscious")
                    await game_state_service.update_character(target_char)
                    print(
                        f"---{target_char.name} drops to 0 HP and is UNCONSCIOUS! They must make death saving throws.---"
                    )
                else:
                    target_char.add_condition("dead")
                    await game_state_service.update_character(target_char)
                    print(f"---{target_char.name} has been defeated!---")
            else:
                print(
                    f"---{attacker_char.name} HITS {target_char.name} for {damage_roll_result.total} damage! (Roll: {attack_roll_result.total} vs AC: {defender_ac})---"
                )
        else:
            print(
                f"---{attacker_char.name} MISSES {target_char.name}! (Roll: {attack_roll_result.total} vs AC: {defender_ac})---"
            )

        # Update the in-memory game_state for subsequent nodes in this graph run
        if target_char.player_id:
            game_state["player"]["hp"] = target_char.hp
            game_state["player"]["is_alive"] = target_char.is_alive
        else:
            # Assuming NPC IDs are strings in game_state["npcs"]
            for npc_id, npc_data in game_state["npcs"].items():
                if npc_data.get("character_id") == target_char.character_id:
                    game_state["npcs"][npc_id]["hp"] = target_char.hp
                    game_state["npcs"][npc_id]["is_alive"] = target_char.is_alive
                    break

        return {
            "combat_state": combat_state,
            "game_state": game_state,
            "action_result": {
                "type": "attack",
                "success": True,
                "target_name": target_char.name,
                "new_hp": target_char.hp,
                "defender_alive": target_char.is_alive,
                "target_id": target_char.character_id,
            },
        }
