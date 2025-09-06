"""
Narrate Result Node for Action Resolution

This module handles generating narrative descriptions of action results,
providing engaging storytelling for all action outcomes.
"""

from typing import Any, Dict

from packages.backend.ai.state.action_resolution_state import ActionResolutionState
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


def _display_action(message: str) -> None:
    """Display action message to screen."""
    print(message)


def _generate_attack_success_narrative(attack_result: Dict) -> str:
    """Generate narrative for a successful attack."""
    target = attack_result.get("target_name", "creature")
    damage = attack_result.get("damage", 0)

    narratives = [
        f"Your attack connects! You deal {damage} damage to the {target}.",
        f"A solid hit! The {target} takes {damage} damage.",
        f"You strike true, dealing {damage} damage to the {target}.",
    ]

    return narratives[damage % len(narratives)]  # Simple variation


def _generate_attack_miss_narrative(attack_result: Dict) -> str:
    """Generate narrative for a missed attack."""
    target = attack_result.get("target_name", "creature")

    narratives = [
        f"Your attack misses the {target}!",
        f"You swing wide, missing the {target}.",
        f"The {target} dodges your attack!",
    ]

    roll = attack_result.get("attack_roll", 1)
    return narratives[roll % len(narratives)]


async def narrate_result_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Generate a narrative description of the action result."""
    try:
        action_result = state.get("action_result", {})

        if action_result.get("type") == "attack":
            if action_result.get("success"):
                narrative = _generate_attack_success_narrative(action_result)
            else:
                narrative = _generate_attack_miss_narrative(action_result)
        else:
            narrative = "Your action is noted, but nothing dramatic happens."

        _display_action(f"📖 Narrative: {narrative}")

        return {"narrative_response": narrative}

    except Exception as e:
        error_msg = f"Narrative generation failed: {str(e)}"
        logger.error("narrative_generation_failed", error=str(e))
        return {"error": error_msg}
