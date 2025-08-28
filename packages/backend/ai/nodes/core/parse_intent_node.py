"""
Parse Intent Node for Action Resolution

This module contains the functionality for parsing player action text
to determine intent and extract relevant information.
"""

from typing import Any, Dict, List, Optional

from packages.backend.ai.state.action_resolution_state import ActionResolutionState, ParsedIntent
from packages.backend.ai.tools import DiceRoller
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


def _display_action(message: str) -> None:
    """Display action message to screen."""
    print(message)


@observability_service.trace_ai_operation(
    operation_name="parse_player_intent",
    operation_type="intent_parsing",
    include_args=True,
    include_result=False
)
def _parse_action_text(action_text: str) -> ParsedIntent:
    """Parse action text to determine intent (simplified NLP)."""

    # Basic keyword matching for now
    attack_keywords = ["attack", "strike", "hit", "fight", "swing", "stab", "slash"]
    investigate_keywords = ["look", "examine", "check", "search", "investigate", "inspect"]
    item_keywords = ["use", "open", "unlock", "take", "get", "grab", "pick"]

    if any(keyword in action_text for keyword in attack_keywords):
        # Find target (usually the noun after attack keywords)
        target = _extract_target(action_text, ["goblin", "chest", "door"])
        return ParsedIntent(
            action_type="attack",
            target=target,
            modifier=None,
            confidence=0.8
        )

    elif any(keyword in action_text for keyword in item_keywords):
        target = _extract_target(action_text, ["chest", "key", "door", "item"])
        return ParsedIntent(
            action_type="use_item",
            target=target,
            modifier=None,
            confidence=0.7
        )

    elif any(keyword in action_text for keyword in investigate_keywords):
        target = _extract_target(action_text, ["room", "chest", "goblin", "area"])
        return ParsedIntent(
            action_type="investigate",
            target=target,
            modifier=None,
            confidence=0.6
        )

    else:
        return ParsedIntent(
            action_type="unknown",
            target=None,
            modifier=None,
            confidence=0.1
        )


def _extract_target(text: str, possible_targets: List[str]) -> Optional[str]:
    """Extract the most likely target from action text."""
    for target in possible_targets:
        if target in text:
            return target
    return None


async def parse_intent_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Parse the player's action text to determine intent."""
    try:
        action_text = state["player_action"].lower().strip()

        parsed_intent = _parse_action_text(action_text)

        _display_action(f"🎯 Parsed Intent: {parsed_intent.action_type}")
        if parsed_intent.target:
            _display_action(f"🎯 Target: {parsed_intent.target}")

        return {"parsed_intent": parsed_intent.__dict__}

    except Exception as e:
        error_msg = f"Intent parsing failed: {str(e)}"
        logger.error("intent_parsing_failed", error=str(e), correlation_id=state["correlation_id"])
        return {"error": error_msg}