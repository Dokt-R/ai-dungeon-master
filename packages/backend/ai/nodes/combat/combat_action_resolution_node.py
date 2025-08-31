"""
Combat Action Resolution Node
"""
from typing import Any, Dict

from packages.backend.ai.state import ActionResolutionState
from packages.backend.ai.tools import DiceRoller


async def resolve_combat_action_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Resolves the specific action taken by the participant (e.g., attack)."""
    combat_state = state["combat_state"]
    game_state = state["game_state"]
    parsed_intent = state["parsed_intent"]

    if not combat_state or not parsed_intent or parsed_intent.get("action_type") != "attack":
        return {}

    dice_roller = DiceRoller()
    active_participant_id = combat_state["active_turn_participant_id"]
    attacker = combat_state["participants"][active_participant_id]
    
    # Find the target
    target_name = parsed_intent.get("target")
    target_id = None
    for pid, p in combat_state["participants"].items():
        if game_state["npcs"].get(pid, {}).get("name", "").lower() == target_name.lower() or game_state["player"].get("name", "").lower() == target_name.lower():
            target_id = pid
            break
    
    if not target_id:
        print(f"---TARGET {target_name} NOT FOUND IN COMBAT---")
        return {}

    defender = combat_state["participants"][target_id]
    
    # Simplified attack roll logic
    # In a real implementation, get these values from the character sheet
    attack_bonus = 5 
    defender_ac = 15
    damage_dice = "1d8+3"

    attack_roll_result = dice_roller.roll_attack(attack_bonus)
    is_critical_hit = attack_roll_result.actual == 20 # Check for natural 20 on the actual d20 roll

    if attack_roll_result.total >= defender_ac:
        actual_damage_dice = damage_dice
        if is_critical_hit:
            # Double the number of damage dice for a critical hit
            num_dice = int(damage_dice.split('d')[0]) if 'd' in damage_dice else 1
            rest_of_dice = damage_dice.split('d')[1] if 'd' in damage_dice else ""
            actual_damage_dice = f"{num_dice * 2}d{rest_of_dice}"
            print(f"---CRITICAL HIT! {attacker['id']} rolls with {actual_damage_dice} damage dice!---")

        damage_roll_result = dice_roller.roll_damage(actual_damage_dice)
        defender["current_health"] -= damage_roll_result.total
        print(f"---{attacker['id']} HITS {defender['id']} for {damage_roll_result.total} damage! (Roll: {attack_roll_result.total} vs AC: {defender_ac})---")
        if defender["current_health"] <= 0:
            if defender["type"] == "player": # Only players make death saves
                defender["status_conditions"].add("unconscious")
                print(f"---{defender['id']} drops to 0 HP and is UNCONSCIOUS! They must make death saving throws.---")
            else:
                defender["status_conditions"].add("dead")
                print(f"---{defender['id']} has been defeated!---")
        else:
            print(f"---{attacker['id']} HITS {defender['id']} for {damage_roll_result.total} damage! (Roll: {attack_roll_result.total} vs AC: {defender_ac})---")
    else:
        print(f"---{attacker['id']} MISSES {defender['id']}! (Roll: {attack_roll_result.total} vs AC: {defender_ac})---")

    return {"combat_state": combat_state}