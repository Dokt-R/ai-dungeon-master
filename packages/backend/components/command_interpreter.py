"""
Command Interpreter Component for AI Dungeon Master.

This module provides advanced natural language processing and context-aware
interpretation for voice commands, enabling intelligent understanding of
player intent and game context.

Features:
- Context-aware command interpretation
- Multi-turn conversation support
- Command disambiguation for ambiguous inputs
- Game state integration and awareness
- Entity resolution and normalization
- Intent confidence scoring and validation
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import CommandExecutionResult, VoiceCommandIntent

logger = get_logger(__name__)


@dataclass
class ConversationContext:
    """Context for multi-turn conversations."""

    conversation_id: str
    session_id: str
    user_id: str
    turns: List[Dict[str, Any]] = field(default_factory=list)
    current_game_state: Dict[str, Any] = field(default_factory=dict)
    pending_actions: List[Dict[str, Any]] = field(default_factory=list)
    clarification_needed: bool = False
    clarification_question: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)

    def add_turn(self, intent: VoiceCommandIntent, response: str) -> None:
        """Add a conversation turn."""
        self.turns.append(
            {
                "intent": intent.primary_intent,
                "confidence": intent.confidence_score,
                "user_text": intent.original_text,
                "system_response": response,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@dataclass
class DisambiguationOption:
    """Option for command disambiguation."""

    intent: str
    description: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    clarification_needed: bool = False


class CommandInterpreter:
    """
    Advanced command interpreter with NLP and context awareness.

    Features:
    - Context-aware interpretation
    - Multi-turn conversation support
    - Command disambiguation
    - Game state integration
    - Entity resolution and validation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Conversation contexts
        self.conversation_contexts: Dict[str, ConversationContext] = {}

        # Game state integration
        self.game_state_cache: Dict[str, Dict[str, Any]] = {}

        # Entity resolution mappings
        self.entity_resolutions: Dict[str, Dict[str, str]] = {}

        # Performance tracking
        self.interpretation_stats = {
            "total_interpretations": 0,
            "successful_interpretations": 0,
            "disambiguation_events": 0,
            "context_usage": 0,
            "average_confidence": 0.0,
        }

        # Configuration
        self.enable_context_awareness = True
        self.enable_multi_turn = True
        self.enable_disambiguation = True
        self.max_conversation_turns = 10
        self.context_timeout_minutes = 30

        logger.info("command_interpreter_initialized")

    async def interpret_command(
        self,
        intent: VoiceCommandIntent,
        session_id: str,
        user_id: str,
        game_context: Dict[str, Any] = None,
    ) -> Tuple[CommandExecutionResult, Optional[str]]:
        """
        Interpret a voice command with context and NLP.

        Args:
            intent: Voice command intent
            session_id: Voice session identifier
            user_id: User identifier
            game_context: Current game context

        Returns:
            Tuple of (execution result, clarification question if needed)
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="command_interpretation",
                session_id=session_id,
                user_id=user_id,
                intent=intent.primary_intent,
            ) as trace_id:
                # Get or create conversation context
                conversation = self._get_conversation_context(session_id, user_id)

                # Update game context
                if game_context:
                    conversation.current_game_state.update(game_context)

                # Check if disambiguation is needed
                if self.enable_disambiguation and self._needs_disambiguation(intent):
                    disambiguation_options = self._generate_disambiguation_options(
                        intent
                    )
                    clarification = self._create_clarification_question(
                        disambiguation_options
                    )
                    conversation.clarification_needed = True
                    conversation.clarification_question = clarification

                    return CommandExecutionResult(
                        execution_id=f"clarify_{int(time.time() * 1000)}",
                        intent_id=intent.intent_id,
                        session_id=session_id,
                        user_id=user_id,
                        command=intent.original_text,
                        intent="clarification_needed",
                        success=False,
                        error_message="Command needs clarification",
                        execution_time=time.time() - start_time,
                        confidence_score=intent.confidence_score,
                    ), clarification

                # Apply context-aware interpretation
                if self.enable_context_awareness:
                    intent = await self._apply_context_awareness(intent, conversation)

                # Resolve entities
                resolved_entities = self._resolve_entities(
                    intent.entities, conversation
                )

                # Validate command against game state
                validation_result = self._validate_command(
                    intent, resolved_entities, conversation
                )

                if not validation_result["valid"]:
                    return CommandExecutionResult(
                        execution_id=f"invalid_{int(time.time() * 1000)}",
                        intent_id=intent.intent_id,
                        session_id=session_id,
                        user_id=user_id,
                        command=intent.original_text,
                        intent=intent.primary_intent,
                        entities=resolved_entities,
                        success=False,
                        error_message=validation_result["error"],
                        execution_time=time.time() - start_time,
                        confidence_score=intent.confidence_score,
                    ), None

                # Generate response text
                response_text = self._generate_response_text(
                    intent, resolved_entities, conversation
                )

                # Create execution result
                result = CommandExecutionResult(
                    execution_id=f"exec_{int(time.time() * 1000)}",
                    intent_id=intent.intent_id,
                    session_id=session_id,
                    user_id=user_id,
                    command=intent.original_text,
                    intent=intent.primary_intent,
                    entities=resolved_entities,
                    success=True,
                    result_data={
                        "interpreted_intent": intent.primary_intent,
                        "confidence": intent.confidence_score,
                        "context_used": len(conversation.turns) > 0,
                    },
                    response_text=response_text,
                    execution_time=time.time() - start_time,
                    confidence_score=intent.confidence_score,
                )

                # Update conversation context
                conversation.add_turn(intent, response_text)

                # Update statistics
                self._update_interpretation_stats(result)

                logger.info(
                    "command_interpreted",
                    session_id=session_id,
                    user_id=user_id,
                    intent=intent.primary_intent,
                    confidence=intent.confidence_score,
                    entities=len(resolved_entities),
                    execution_time=result.execution_time,
                    trace_id=trace_id,
                )

                return result, None

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "command_interpretation_failed",
                session_id=session_id,
                user_id=user_id,
                intent=intent.primary_intent,
                execution_time=execution_time,
                error=str(e),
            )

            return CommandExecutionResult(
                execution_id=f"error_{int(time.time() * 1000)}",
                intent_id=intent.intent_id,
                session_id=session_id,
                user_id=user_id,
                command=intent.original_text,
                intent=intent.primary_intent,
                success=False,
                error_message=str(e),
                execution_time=execution_time,
                confidence_score=intent.confidence_score,
            ), None

    def _get_conversation_context(
        self, session_id: str, user_id: str
    ) -> ConversationContext:
        """Get or create conversation context."""
        if session_id not in self.conversation_contexts:
            self.conversation_contexts[session_id] = ConversationContext(
                conversation_id=f"conv_{int(time.time() * 1000)}",
                session_id=session_id,
                user_id=user_id,
            )

        return self.conversation_contexts[session_id]

    def _needs_disambiguation(self, intent: VoiceCommandIntent) -> bool:
        """Check if intent needs disambiguation."""
        # Check confidence threshold
        if intent.confidence_score < 0.6:
            return True

        # Check for ambiguous entities
        ambiguous_entities = []
        for entity_type, entity_data in intent.entities.items():
            if entity_data.get("confidence", 1.0) < 0.7:
                ambiguous_entities.append(entity_type)

        # Check alternative intents with close confidence
        if intent.alternative_intents:
            primary_confidence = intent.confidence_score
            close_alternatives = [
                alt
                for alt in intent.alternative_intents
                if abs(alt.get("confidence", 0) - primary_confidence) < 0.2
            ]

            if len(close_alternatives) > 1:
                return True

        return len(ambiguous_entities) > 0 or len(intent.alternative_intents) > 2

    def _generate_disambiguation_options(
        self, intent: VoiceCommandIntent
    ) -> List[DisambiguationOption]:
        """Generate disambiguation options."""
        options = []

        # Add primary intent
        options.append(
            DisambiguationOption(
                intent=intent.primary_intent,
                description=self._get_intent_description(intent.primary_intent),
                confidence=intent.confidence_score,
                entities=intent.entities,
            )
        )

        # Add alternative intents
        for alt in intent.alternative_intents[:3]:  # Top 3 alternatives
            alt_intent = alt.get("intent", "unknown")
            options.append(
                DisambiguationOption(
                    intent=alt_intent,
                    description=self._get_intent_description(alt_intent),
                    confidence=alt.get("confidence", 0.0),
                )
            )

        return options

    def _create_clarification_question(
        self, options: List[DisambiguationOption]
    ) -> str:
        """Create clarification question for user."""
        if len(options) == 1:
            return f"I heard '{options[0].intent}' with {options[0].confidence:.1%} confidence. Is that correct?"

        question = (
            "I heard your command but I'm not sure what you meant. Did you want to:\n"
        )
        for i, option in enumerate(options, 1):
            question += (
                f"{i}. {option.description} ({option.confidence:.1%} confidence)\n"
            )

        question += "\nPlease clarify what you'd like to do."
        return question

    async def _apply_context_awareness(
        self, intent: VoiceCommandIntent, conversation: ConversationContext
    ) -> VoiceCommandIntent:
        """Apply context awareness to improve intent interpretation."""
        if not conversation.turns:
            return intent

        # Look for context clues in recent turns
        recent_turns = conversation.turns[-3:]  # Last 3 turns

        context_hints = {}

        for turn in recent_turns:
            # Extract entities that might be relevant
            if "entities" in turn:
                for entity_type, entity_value in turn.get("entities", {}).items():
                    if entity_type not in intent.entities:
                        context_hints[entity_type] = entity_value

            # Check for pending actions
            if conversation.pending_actions:
                for action in conversation.pending_actions:
                    if action.get("intent") == intent.primary_intent:
                        # This might be a follow-up to a pending action
                        intent.context["pending_action"] = action
                        break

        # Apply context hints to entities
        for entity_type, entity_value in context_hints.items():
            if entity_type not in intent.entities:
                intent.entities[entity_type] = {
                    "value": entity_value,
                    "type": entity_type.upper(),
                    "confidence": 0.6,  # Lower confidence for context-derived entities
                    "source": "context",
                }

        intent.context["context_applied"] = True
        intent.context["context_hints"] = context_hints

        if context_hints:
            self.interpretation_stats["context_usage"] += 1

        return intent

    def _resolve_entities(
        self, entities: Dict[str, Any], conversation: ConversationContext
    ) -> Dict[str, Any]:
        """Resolve and normalize entities."""
        resolved = {}

        for entity_type, entity_data in entities.items():
            value = entity_data.get("value", "")

            # Apply entity-specific resolution
            if entity_type == "character":
                resolved_value = self._resolve_character_entity(value, conversation)
            elif entity_type == "item":
                resolved_value = self._resolve_item_entity(value, conversation)
            elif entity_type == "location":
                resolved_value = self._resolve_location_entity(value, conversation)
            elif entity_type == "monster":
                resolved_value = self._resolve_monster_entity(value, conversation)
            else:
                resolved_value = value.lower()

            resolved[entity_type] = {
                "original_value": value,
                "resolved_value": resolved_value,
                "normalized_value": resolved_value.lower(),
                "type": entity_data.get("type", entity_type.upper()),
                "confidence": entity_data.get("confidence", 0.9),
                "resolved": True,
            }

        return resolved

    def _resolve_character_entity(
        self, value: str, conversation: ConversationContext
    ) -> str:
        """Resolve character entity with game context."""
        # Check if it's a reference to current character
        if value.lower() in ["me", "myself", "my character", "i"]:
            current_char = conversation.current_game_state.get("current_character")
            return current_char if current_char else "player_character"

        # Check conversation history for character references
        for turn in conversation.turns[-5:]:  # Last 5 turns
            if "character" in turn.get("entities", {}):
                if value.lower() in turn["entities"]["character"].lower():
                    return turn["entities"]["character"]

        return value

    def _resolve_item_entity(
        self, value: str, conversation: ConversationContext
    ) -> str:
        """Resolve item entity with game context."""
        # Check inventory context
        inventory = conversation.current_game_state.get("inventory", [])
        for item in inventory:
            if value.lower() in item.lower():
                return item

        return value

    def _resolve_location_entity(
        self, value: str, conversation: ConversationContext
    ) -> str:
        """Resolve location entity with game context."""
        # Check current location context
        current_location = conversation.current_game_state.get("current_location")
        if current_location and value.lower() in current_location.lower():
            return current_location

        return value

    def _resolve_monster_entity(
        self, value: str, conversation: ConversationContext
    ) -> str:
        """Resolve monster entity with game context."""
        # Check recent combat context
        recent_combat = conversation.current_game_state.get("recent_combat", [])
        for combatant in recent_combat:
            if value.lower() in combatant.lower():
                return combatant

        return value

    def _validate_command(
        self,
        intent: VoiceCommandIntent,
        entities: Dict[str, Any],
        conversation: ConversationContext,
    ) -> Dict[str, Any]:
        """Validate command against game state and rules."""
        try:
            # Basic intent validation
            if intent.primary_intent == "attack":
                target = entities.get("target", {}).get("resolved_value")
                if not target:
                    return {
                        "valid": False,
                        "error": "No target specified for attack command",
                    }

                # Check if target is valid in current context
                valid_targets = conversation.current_game_state.get("valid_targets", [])
                if valid_targets and target not in [t.lower() for t in valid_targets]:
                    return {"valid": False, "error": f"{target} is not a valid target"}

            elif intent.primary_intent == "use_item":
                item = entities.get("item", {}).get("resolved_value")
                if not item:
                    return {"valid": False, "error": "No item specified"}

                # Check inventory
                inventory = conversation.current_game_state.get("inventory", [])
                if inventory and item not in [i.lower() for i in inventory]:
                    return {"valid": False, "error": f"{item} not found in inventory"}

            elif intent.primary_intent == "move":
                location = entities.get("location", {}).get("resolved_value")
                if not location:
                    return {"valid": False, "error": "No destination specified"}

                # Check if location is accessible
                accessible_locations = conversation.current_game_state.get(
                    "accessible_locations", []
                )
                if accessible_locations and location not in [
                    l.lower() for l in accessible_locations
                ]:
                    return {
                        "valid": False,
                        "error": f"Cannot move to {location} from current position",
                    }

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _generate_response_text(
        self,
        intent: VoiceCommandIntent,
        entities: Dict[str, Any],
        conversation: ConversationContext,
    ) -> str:
        """Generate appropriate response text for the command."""
        try:
            intent_type = intent.primary_intent

            if intent_type == "attack":
                target = entities.get("target", {}).get("resolved_value", "target")
                return f"Attacking {target}!"

            elif intent_type == "move":
                location = entities.get("location", {}).get(
                    "resolved_value", "location"
                )
                return f"Moving to {location}."

            elif intent_type == "use_item":
                item = entities.get("item", {}).get("resolved_value", "item")
                quantity = entities.get("quantity", {}).get("resolved_value", "1")
                if quantity != "1":
                    return f"Using {quantity} {item}(s)."
                else:
                    return f"Using {item}."

            elif intent_type == "inventory":
                return "Checking inventory..."

            elif intent_type == "character":
                character = entities.get("character", {}).get(
                    "resolved_value", "character"
                )
                return f"Checking {character} status."

            elif intent_type == "save":
                return "Game saved successfully."

            elif intent_type == "help":
                return "I can help you with combat, movement, inventory, character status, and more. What would you like to know?"

            else:
                return f"Command '{intent.original_text}' processed."

        except Exception as e:
            logger.error("response_generation_failed", error=str(e))
            return "Command processed."

    def _get_intent_description(self, intent: str) -> str:
        """Get human-readable description of intent."""
        descriptions = {
            "attack": "Attack a target",
            "move": "Move to a location",
            "use_item": "Use an item",
            "inventory": "Check inventory",
            "character": "Check character status",
            "save": "Save the game",
            "help": "Get help and commands",
        }
        return descriptions.get(intent, f"Perform {intent} action")

    def _update_interpretation_stats(self, result: CommandExecutionResult) -> None:
        """Update interpretation statistics."""
        self.interpretation_stats["total_interpretations"] += 1

        if result.success:
            self.interpretation_stats["successful_interpretations"] += 1

        # Update average confidence
        current_avg = self.interpretation_stats["average_confidence"]
        total = self.interpretation_stats["total_interpretations"]

        self.interpretation_stats["average_confidence"] = (
            (current_avg * (total - 1)) + result.confidence_score
        ) / total

    def handle_clarification_response(
        self, session_id: str, user_id: str, clarification_response: str
    ) -> Optional[CommandExecutionResult]:
        """Handle user response to clarification question."""
        if session_id not in self.conversation_contexts:
            return None

        conversation = self.conversation_contexts[session_id]

        if not conversation.clarification_needed:
            return None

        # Process clarification response
        # In a real implementation, this would parse the user's choice
        # and execute the appropriate command

        conversation.clarification_needed = False
        conversation.clarification_question = ""

        return CommandExecutionResult(
            execution_id=f"clarify_response_{int(time.time() * 1000)}",
            intent_id="clarification_response",
            session_id=session_id,
            user_id=user_id,
            command=clarification_response,
            intent="clarification_handled",
            success=True,
            response_text="Understood. Processing your command.",
            execution_time=0.1,
            confidence_score=0.9,
        )

    def cleanup_conversation(self, session_id: str) -> bool:
        """Clean up conversation context."""
        if session_id in self.conversation_contexts:
            del self.conversation_contexts[session_id]
            logger.info("conversation_cleaned_up", session_id=session_id)
            return True
        return False

    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of conversation context."""
        if session_id not in self.conversation_contexts:
            return {}

        conversation = self.conversation_contexts[session_id]

        return {
            "conversation_id": conversation.conversation_id,
            "total_turns": len(conversation.turns),
            "clarification_needed": conversation.clarification_needed,
            "pending_actions": len(conversation.pending_actions),
            "started_at": conversation.started_at.isoformat(),
            "last_turn": conversation.turns[-1] if conversation.turns else None,
        }

    def get_interpretation_stats(self) -> Dict[str, Any]:
        """Get interpretation statistics."""
        total = self.interpretation_stats["total_interpretations"]
        successful = self.interpretation_stats["successful_interpretations"]

        return {
            **self.interpretation_stats,
            "success_rate": successful / max(total, 1),
            "disambiguation_rate": self.interpretation_stats["disambiguation_events"]
            / max(total, 1),
            "context_usage_rate": self.interpretation_stats["context_usage"]
            / max(total, 1),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the command interpreter."""
        active_conversations = len(self.conversation_contexts)
        avg_confidence = self.interpretation_stats["average_confidence"]

        success_rate = 0.0
        if self.interpretation_stats["total_interpretations"] > 0:
            success_rate = (
                self.interpretation_stats["successful_interpretations"]
                / self.interpretation_stats["total_interpretations"]
            )

        return {
            "status": "healthy" if success_rate >= 0.8 else "degraded",
            "active_conversations": active_conversations,
            "total_interpretations": self.interpretation_stats["total_interpretations"],
            "success_rate": success_rate,
            "average_confidence": avg_confidence,
            "context_awareness_enabled": self.enable_context_awareness,
            "multi_turn_enabled": self.enable_multi_turn,
            "disambiguation_enabled": self.enable_disambiguation,
        }


# Global command interpreter instance
command_interpreter = CommandInterpreter()
