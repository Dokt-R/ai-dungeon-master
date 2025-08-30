"""
Parse Intent Node for Action Resolution

This module contains the functionality for parsing player action text
to determine intent and extract relevant information.
"""

import time
from typing import Any, Dict, List, Optional

from packages.backend.ai.state.action_resolution_state import ActionResolutionState, ParsedIntent
from packages.backend.ai.constants.actions import (
    COMBAT_KEYWORDS, EXPLORATION_KEYWORDS, INTERACTION_KEYWORDS,
    DIALOGUE_KEYWORDS, SOCIAL_SKILL_MAPPING, ROUTE_MAPPING,
    COMBAT_TARGETS, INTERACTION_TARGETS, EXPLORATION_TARGETS,
    ACTION_TARGET_MAPPING
)
from packages.backend.ai.tools import DiceRoller
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


def _display_action(parsed_intent: str) -> None:
    """Display action message to screen."""
        # Display enhanced parsing results
    print("------PARSED_INTENT_NODE------")
    print()
    print(f"Intent: {parsed_intent.intent}")
    print(f"Action Type: {parsed_intent.action_type}")
    print(f"Target: {parsed_intent.target or 'none'}")
    print(f"Confidence: {parsed_intent.confidence * 100}%")

    if parsed_intent.modifier and parsed_intent.modifier != parsed_intent.action_type:
        if parsed_intent.action_type == "talk":
            print(f"💬 Dialogue: '{parsed_intent.modifier}'")
        else:
            print(f"✨ Modifier: {parsed_intent.modifier}")


def _parse_action_text(action_text: str) -> ParsedIntent:
    """Parse action text to determine intent using standardized action constants."""

    # Extract dialogue content for conversation actions using standardized keywords
    dialogue = _extract_dialogue(action_text)

    # Combat actions - highest priority (using standardized constants)
    if any(keyword in action_text for keyword in COMBAT_KEYWORDS):
        target = _extract_target(action_text, COMBAT_TARGETS)
        action_type = "attack" if any(k in action_text for k in ["attack", "strike", "hit", "fight", "swing"]) else "defend" if "defend" in action_text else "cast"
        return ParsedIntent(
            intent="combat",
            action_type=action_type,
            target=target,
            modifier="combat",
            confidence=0.9
        )

    # Interaction/social actions - medium priority (using standardized constants)
    elif any(keyword in action_text for keyword in INTERACTION_KEYWORDS):
        # Use action-specific target mapping from constants
        target_words = action_text.lower().split()
        target = None
        for word in target_words:
            for action, targets in ACTION_TARGET_MAPPING.items():
                if action in action_text.lower() and word in targets:
                    target = word
                    break
            if target:
                break
        if not target:
            target = _extract_target(action_text, INTERACTION_TARGETS)

        # Determine specific interaction type using standardized mappings
        if any(k in action_text for k in ["take", "get", "grab", "pick"]):
            action_type = "take"
        elif any(k in action_text for k in ["use", "activate"]):
            action_type = "use"
        elif any(k in action_text for k in DIALOGUE_KEYWORDS):  # Use standardized dialogue keywords
            action_type = "talk"
            dialogue = dialogue  # Store extracted dialogue
        elif any(k in action_text for k in ["persuade", "intimidate", "deceive"]):
            # Map to D&D skill using standardized mapping
            social_skill = action_text.split()[1] if len(action_text.split()) > 1 else "persuade"
            action_type = SOCIAL_SKILL_MAPPING.get(social_skill, "persuade")
        else:
            action_type = "use"

        return ParsedIntent(
            intent="social", #! Needs cross checking
            action_type=action_type,
            target=target,
            modifier=dialogue,  # Store dialogue here if present
            confidence=0.8
        )

    # Exploration/investigation actions - lower priority (using standardized constants)
    elif any(keyword in action_text for keyword in EXPLORATION_KEYWORDS):
        target = _extract_target(action_text, EXPLORATION_TARGETS)

        # Determine specific exploration type using standardized logic
        if any(k in action_text for k in ["search", "investigate"]):
            action_type = "search"
        elif any(k in action_text for k in ["open", "unlock"]):
            action_type = "open" if "open" in action_text else "unlock"
        elif any(k in action_text for k in ["look", "examine", "inspect"]):
            action_type = "examine" if any(k in action_text for k in ["examine", "inspect"]) else "look"
        else:
            action_type = "investigate"

        return ParsedIntent(
            intent="exploration",
            action_type=action_type,
            target=target,
            modifier="exploration",
            confidence=0.7
        )

    # Default to exploration for unknown actions (using standardized fallback)
    else:
        return ParsedIntent(
            intent="exploration",
            action_type="look",  # Default exploration action
            target="area",
            modifier="exploration",
            confidence=0.3
        )


def _extract_target(text: str, possible_targets: List[str]) -> Optional[str]:
    """Extract the most likely target from action text."""
    for target in possible_targets:
        if target in text:
            return target
    return None


def _extract_dialogue(text: str) -> Optional[str]:
    """Extract dialogue content from action text."""
    # Look for dialogue patterns like "say X", "speak Y", "hello", etc.

    # Find text after dialogue keywords
    dialogue_keywords = ['say', 'speak', 'talk', 'tell']
    words = text.lower().split()

    for i, word in enumerate(words):
        if word in dialogue_keywords and i < len(words) - 1:
            # Get everything after the dialogue keyword
            dialogue_text = ' '.join(words[i+1:])
            # Clean up punctuation
            dialogue_text = dialogue_text.strip('"\'.,?!')
            return dialogue_text if dialogue_text else None

    return None


async def parse_intent_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Parse the player's action text to determine intent."""
    with observability_service.trace_operation(
        operation_name="parse_intent_node_execution",
        node_type="action_parsing",
        correlation_id=state["correlation_id"]
    ) as node_trace_id:

        start_time = time.time()

        try:
            action_text = state["player_action"].lower().strip()

            parsed_intent = _parse_action_text(action_text)

            _display_action(parsed_intent)

            # Determine routing category using standardized route mapping #! May need to change and route based on intent
            routed_node = ROUTE_MAPPING.get(parsed_intent.action_type, "exploration_node")

            print(f"Routing To ---> {routed_node}")
            print("-" * 30)

            execution_time = time.time() - start_time
            logger.debug("parse_intent_node_completed",
                        trace_id=node_trace_id,
                        execution_time=f"{execution_time:.4f}s",
                        node=routed_node,
                        action_type=parsed_intent.action_type,
                        target=parsed_intent.target,
                        confidence=parsed_intent.confidence)

            return {"parsed_intent": parsed_intent.__dict__}

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Intent parsing failed: {str(e)}"
            logger.error("intent_parsing_failed",
                        error=str(e),
                        correlation_id=state["correlation_id"],
                        execution_time=f"{execution_time:.4f}s",
                        trace_id=node_trace_id)
            return {"error": error_msg}