"""
Combat Resolution Node for Action Resolution

This module handles combat-specific action resolution including attack rolls,
damage calculation, and hit/miss determination.
"""

from typing import Any, Dict, List, Optional

from packages.backend.ai.state.action_resolution_state import ActionResolutionState
from packages.backend.ai.tools import DiceRoller, safe_observability
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


def _display_action(message: str) -> None:
    """Display action message to screen."""
    print(message)


def _display_attack_result(attack_result: Dict) -> None:
    """Display attack resolution result."""
    if attack_result.get("success"):
        print(f"🎯 HIT! (Roll: {attack_result['attack_roll']}, AC: {attack_result['ac']})")
    else:
        print(f"❌ MISS! (Roll: {attack_result['attack_roll']}, AC: {attack_result['ac']})")


@observability_service.trace_ai_operation(
    operation_name="resolve_combat_attack",
    operation_type="combat_mechanics",
    include_args=True,
    include_result=True
)
def _resolve_attack(attacker: Dict, defender: Dict, correlation_id: str) -> Dict[str, Any]:
    """Resolve an attack action with dice rolls."""
    dice_roller = DiceRoller()

    with observability_service.trace_operation(
        operation_name="combat_attack_resolution",
        correlation_id=correlation_id,
        attacker=attacker.get("name"),
        defender=defender.get("name")
    ):
        # Get attack bonus
        attack_bonus = attacker.get("attack", {}).get("bonus", 0)

        # Roll attack
        attack_roll = dice_roller.roll_attack(attack_bonus)
        _display_action(f"⚔️  Attack Roll: {attack_roll.description}")

        # Check if hit
        ac = defender.get("ac", 10)
        hit = attack_roll.total >= ac

        if hit:
            # Hit - roll damage
            damage_dice = attacker.get("attack", {}).get("damage", "1d6")
            damage_roll = dice_roller.roll_damage(damage_dice)
            _display_action(f"💥 Damage Roll: {damage_roll.description}")

            # Apply damage
            old_hp = defender.get("hp", 0)
            new_hp = max(0, old_hp - damage_roll.total)
            defender_alive = new_hp > 0

            return {
                "type": "attack",
                "success": True,
                "attack_roll": attack_roll.total,
                "ac": ac,
                "damage": damage_roll.total,
                "old_hp": old_hp,
                "new_hp": new_hp,
                "defender_alive": defender_alive,
                "target_name": defender.get("name"),
                "damage_description": damage_roll.description
            }
        else:
            # Miss
            return {
                "type": "attack",
                "success": False,
                "attack_roll": attack_roll.total,
                "ac": ac,
                "target_name": defender.get("name")
            }


async def combat_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Resolve a combat action using dice rolls."""
    try:
        parsed_intent = state.get("parsed_intent", {})
        game_state = state["game_state"]
        correlation_id = state["correlation_id"]

        if parsed_intent.get("action_type") != "attack":
            return {"action_result": {"type": "not_combat", "description": "Not a combat action"}}

        target_name = parsed_intent.get("target", "unknown")

        # Get player and target stats
        player = game_state.get("player", {})
        npcs = game_state.get("npcs", [])
        target = None

        for npc in npcs:
            if npc.get("name", "").lower() == target_name.lower():
                target = npc
                break

        if not target:
            return {"action_result": {"type": "error", "description": f"Target {target_name} not found"}}

        # Resolve attack
        attack_result = _resolve_attack(player, target, correlation_id)

        _display_attack_result(attack_result)

        return {"action_result": attack_result}

    except Exception as e:
        error_msg = f"Combat resolution failed: {str(e)}"
        logger.error("combat_resolution_failed", error=str(e), correlation_id=state["correlation_id"])
        return {"error": error_msg}