"""
Voice Command Processor Component for AI Dungeon Master.

This module provides intelligent voice command processing with intent recognition,
entity extraction, and confidence scoring to enable natural language interaction
with the AI Dungeon Master.

Features:
- Intent classification for game actions and system commands
- Entity extraction for characters, items, locations, and quantities
- Fuzzy pattern matching with confidence scoring
- Context-aware command interpretation
- Multi-turn conversation support
- Command history and preference learning
"""

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import CommandHistory, CommandPattern, VoiceCommandIntent

logger = get_logger(__name__)


@dataclass
class IntentMatch:
    """Result of intent matching."""

    intent: str
    confidence: float
    pattern_id: str
    matched_text: str
    entities: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityExtraction:
    """Result of entity extraction."""

    entity_type: str
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    normalized_value: str = ""


class VoiceCommandProcessor:
    """
    Process voice commands with intent recognition and entity extraction.

    Features:
    - Intent classification for game actions
    - Entity extraction for game elements
    - Fuzzy pattern matching
    - Confidence scoring and disambiguation
    - Context-aware processing
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Command patterns for different intents
        self.command_patterns: Dict[str, CommandPattern] = {}

        # Entity extraction patterns
        self.entity_patterns: Dict[str, List[str]] = {}

        # User command history for learning
        self.user_histories: Dict[str, CommandHistory] = {}

        # Performance tracking
        self.processing_stats = {
            "total_commands": 0,
            "successful_recognition": 0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0,
        }

        # Initialize default command patterns
        self._initialize_default_patterns()

        # Initialize entity extraction
        self._initialize_entity_patterns()

        logger.info("voice_command_processor_initialized")

    def _initialize_default_patterns(self) -> None:
        """Initialize default command patterns for game actions."""

        # Combat patterns
        self.command_patterns["attack"] = CommandPattern(
            pattern_id="attack_basic",
            intent="attack",
            patterns=[
                "attack {target}",
                "hit {target}",
                "strike {target}",
                "fight {target}",
                "attack the {target}",
                "kill {target}",
                "slay {target}",
            ],
            entities={"target": "MONSTER"},
            priority=10,
            examples=["attack the goblin", "hit the orc", "strike the dragon"],
        )

        # Movement patterns
        self.command_patterns["move"] = CommandPattern(
            pattern_id="move_basic",
            intent="move",
            patterns=[
                "move to {location}",
                "go to {location}",
                "walk to {location}",
                "run to {location}",
                "travel to {location}",
                "head to {location}",
            ],
            entities={"location": "LOCATION"},
            priority=8,
            examples=["move to the dungeon", "go to the tavern", "walk to the forest"],
        )

        # Inventory patterns
        self.command_patterns["inventory"] = CommandPattern(
            pattern_id="inventory_basic",
            intent="inventory",
            patterns=[
                "check inventory",
                "show inventory",
                "what do I have",
                "inventory",
                "my items",
                "my stuff",
            ],
            priority=9,
            examples=["check inventory", "show my items", "what do I have"],
        )

        # Character patterns
        self.command_patterns["character"] = CommandPattern(
            pattern_id="character_status",
            intent="character",
            patterns=[
                "check {character}",
                "status of {character}",
                "how is {character}",
                "{character} status",
                "health of {character}",
            ],
            entities={"character": "PERSON"},
            priority=7,
            examples=["check my character", "how is Eldrin", "status of Throg"],
        )

        # Item usage patterns
        self.command_patterns["use_item"] = CommandPattern(
            pattern_id="use_item_basic",
            intent="use_item",
            patterns=[
                "use {item}",
                "drink {item}",
                "eat {item}",
                "equip {item}",
                "use {quantity} {item}",
                "drink {quantity} {item}",
            ],
            entities={"item": "ITEM", "quantity": "NUMBER"},
            priority=9,
            examples=[
                "use health potion",
                "drink mana potion",
                "equip sword",
                "use 2 potions",
            ],
        )

        # System patterns
        self.command_patterns["save"] = CommandPattern(
            pattern_id="save_game",
            intent="system",
            patterns=["save game", "save", "save progress"],
            priority=10,
            examples=["save game", "save"],
        )

        self.command_patterns["help"] = CommandPattern(
            pattern_id="help_command",
            intent="system",
            patterns=["help", "help me", "what can I say", "commands", "how do I"],
            priority=5,
            examples=["help", "what can I say"],
        )

    def _initialize_entity_patterns(self) -> None:
        """Initialize patterns for entity extraction."""

        # Monster patterns
        self.entity_patterns["MONSTER"] = [
            r"\b(goblin|orc|dragon|wolf|bear|spider|rat|bandit)\b",
            r"\b(skeleton|zombie|ghost|vampire|werewolf)\b",
            r"\b(demon|devil|angel|elemental|construct)\b",
        ]

        # Location patterns
        self.entity_patterns["LOCATION"] = [
            r"\b(dungeon|cave|tavern|forest|castle|town|village)\b",
            r"\b(mountain|river|bridge|road|path|clearing)\b",
            r"\b(room|chamber|hall|corridor|entrance|exit)\b",
        ]

        # Item patterns
        self.entity_patterns["ITEM"] = [
            r"\b(sword|axe|bow|shield|armor|helmet)\b",
            r"\b(potion|elixir|scroll|wand|ring|amulet)\b",
            r"\b(key|lockpick|torch|rope|backpack)\b",
        ]

        # Character patterns (generic)
        self.entity_patterns["PERSON"] = [
            r"\b(my character|me|myself|I)\b",
            r"\b(Eldrin|Throg|Lyra|Finn|Mira|Kael)\b",  # Common fantasy names
        ]

        # Number patterns
        self.entity_patterns["NUMBER"] = [
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b"
        ]

    async def process_voice_command(
        self, text: str, session_id: str, user_id: str, context: Dict[str, Any] = None
    ) -> VoiceCommandIntent:
        """
        Process a voice command and return intent analysis.

        Args:
            text: Transcribed voice command text
            session_id: Voice session identifier
            user_id: User identifier
            context: Additional context for processing

        Returns:
            VoiceCommandIntent with classification and entities
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="voice_command_processing",
                session_id=session_id,
                user_id=user_id,
                text_length=len(text),
            ) as trace_id:
                # Normalize text
                normalized_text = self._normalize_text(text)

                # Get user history for learning
                user_history = self._get_user_history(user_id)

                # Find intent matches
                intent_matches = await self._find_intent_matches(
                    normalized_text, context, user_history
                )

                # Select best intent
                best_match = self._select_best_intent(intent_matches)

                # Extract entities
                entities = self._extract_entities(normalized_text, best_match)

                # Create intent result
                intent = VoiceCommandIntent(
                    intent_id=f"intent_{int(time.time() * 1000)}",
                    primary_intent=best_match.intent if best_match else "unknown",
                    confidence_score=best_match.confidence if best_match else 0.0,
                    alternative_intents=[
                        {"intent": match.intent, "confidence": match.confidence}
                        for match in intent_matches[:3]  # Top 3 alternatives
                    ],
                    entities=entities,
                    context={
                        "session_id": session_id,
                        "user_id": user_id,
                        "original_text": text,
                        "game_state": context.get("game_state") if context else None,
                        "matched_pattern": best_match.pattern_id
                        if best_match
                        else None,
                    },
                    original_text=text,
                    processed_text=normalized_text,
                    processing_time=time.time() - start_time,
                )

                # Update user history
                self._update_user_history(user_id, intent, user_history)

                # Update statistics
                self._update_processing_stats(intent, time.time() - start_time)

                logger.info(
                    "voice_command_processed",
                    session_id=session_id,
                    user_id=user_id,
                    intent=intent.primary_intent,
                    confidence=intent.confidence_score,
                    entities=len(intent.entities),
                    processing_time=intent.processing_time,
                    trace_id=trace_id,
                )

                return intent

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "voice_command_processing_failed",
                session_id=session_id,
                user_id=user_id,
                text=text,
                processing_time=processing_time,
                error=str(e),
            )

            # Return minimal intent on error
            return VoiceCommandIntent(
                intent_id=f"error_{int(time.time() * 1000)}",
                primary_intent="error",
                confidence_score=0.0,
                original_text=text,
                processed_text=text,
                processing_time=processing_time,
            )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for processing."""
        # Convert to lowercase
        normalized = text.lower()

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Remove punctuation except for entity-relevant chars
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Remove extra whitespace again
        normalized = " ".join(normalized.split())

        return normalized

    async def _find_intent_matches(
        self, text: str, context: Dict[str, Any], user_history: CommandHistory
    ) -> List[IntentMatch]:
        """Find intent matches for the given text."""
        matches = []

        for pattern in self.command_patterns.values():
            # Check context requirements
            if not self._check_context_requirements(pattern, context):
                continue

            # Try exact pattern matching
            exact_match = self._match_exact_pattern(text, pattern)
            if exact_match:
                matches.append(exact_match)
                continue

            # Try fuzzy matching if enabled
            if pattern.fuzzy_matching:
                fuzzy_match = self._match_fuzzy_pattern(text, pattern)
                if fuzzy_match:
                    matches.append(fuzzy_match)

        # Sort by confidence and priority
        matches.sort(
            key=lambda m: (m.confidence, self.command_patterns[m.intent].priority),
            reverse=True,
        )

        return matches

    def _match_exact_pattern(
        self, text: str, pattern: CommandPattern
    ) -> Optional[IntentMatch]:
        """Try to match text against a pattern exactly."""
        for pattern_text in pattern.patterns:
            # Simple placeholder matching (in real implementation, use NLP)
            if self._simple_pattern_match(text, pattern_text):
                confidence = self._calculate_pattern_confidence(
                    text, pattern_text, pattern
                )

                return IntentMatch(
                    intent=pattern.intent,
                    confidence=confidence,
                    pattern_id=pattern.pattern_id,
                    matched_text=text,
                    entities=self._extract_pattern_entities(
                        text, pattern_text, pattern
                    ),
                )

        return None

    def _match_fuzzy_pattern(
        self, text: str, pattern: CommandPattern
    ) -> Optional[IntentMatch]:
        """Try fuzzy matching against a pattern."""
        best_match = None
        best_confidence = 0.0

        for pattern_text in pattern.patterns:
            # Calculate fuzzy similarity
            similarity = SequenceMatcher(None, text, pattern_text).ratio()

            # Apply fuzzy threshold
            fuzzy_threshold = 0.7 if pattern.priority >= 8 else 0.6

            if similarity >= fuzzy_threshold:
                confidence = similarity * 0.8  # Reduce confidence for fuzzy matches

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = IntentMatch(
                        intent=pattern.intent,
                        confidence=confidence,
                        pattern_id=pattern.pattern_id,
                        matched_text=text,
                        entities=self._extract_pattern_entities(
                            text, pattern_text, pattern
                        ),
                    )

        return best_match

    def _simple_pattern_match(self, text: str, pattern: str) -> bool:
        """Simple pattern matching implementation."""
        # Remove entity placeholders for basic matching
        clean_pattern = re.sub(r"\{[^}]+\}", "", pattern).strip()

        # Check if all significant words in pattern are in text
        pattern_words = set(clean_pattern.split())
        text_words = set(text.split())

        # Allow for some word variations
        common_words = pattern_words.intersection(text_words)
        match_ratio = len(common_words) / max(len(pattern_words), 1)

        return match_ratio >= 0.7

    def _calculate_pattern_confidence(
        self, text: str, pattern: str, pattern_obj: CommandPattern
    ) -> float:
        """Calculate confidence score for a pattern match."""
        # Base confidence from word overlap
        pattern_words = set(re.sub(r"\{[^}]+\}", "", pattern).split())
        text_words = set(text.split())

        overlap = len(pattern_words.intersection(text_words))
        total_pattern_words = len(pattern_words)

        base_confidence = (
            overlap / max(total_pattern_words, 1) if total_pattern_words > 0 else 0.0
        )

        # Boost confidence based on pattern priority
        priority_boost = min(pattern_obj.priority / 10.0, 0.2)
        confidence = min(base_confidence + priority_boost, 1.0)

        # Boost confidence if exact phrase match
        if pattern.lower() in text.lower():
            confidence = min(confidence + 0.3, 1.0)

        return confidence

    def _extract_pattern_entities(
        self, text: str, pattern: str, pattern_obj: CommandPattern
    ) -> Dict[str, Any]:
        """Extract entities from matched pattern."""
        entities = {}

        # Simple entity extraction based on patterns
        for entity_name, entity_type in pattern_obj.entities.items():
            if entity_type in self.entity_patterns:
                for entity_pattern in self.entity_patterns[entity_type]:
                    matches = re.finditer(entity_pattern, text, re.IGNORECASE)
                    for match in matches:
                        entities[entity_name] = {
                            "value": match.group(0),
                            "type": entity_type,
                            "confidence": 0.9,
                        }
                        break  # Take first match

        return entities

    def _extract_entities(
        self, text: str, best_match: Optional[IntentMatch]
    ) -> Dict[str, Any]:
        """Extract entities from text."""
        entities = {}

        # If we have a matched pattern, use its entities
        if best_match and best_match.entities:
            entities.update(best_match.entities)

        # Additional entity extraction for common patterns
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity_value = match.group(0).lower()
                    if entity_type not in entities:
                        entities[entity_type.lower()] = {
                            "value": entity_value,
                            "type": entity_type,
                            "confidence": 0.8,
                        }

        return entities

    def _select_best_intent(self, matches: List[IntentMatch]) -> Optional[IntentMatch]:
        """Select the best intent from matches."""
        if not matches:
            return None

        # Return the highest confidence match
        return max(matches, key=lambda m: m.confidence)

    def _check_context_requirements(
        self, pattern: CommandPattern, context: Dict[str, Any]
    ) -> bool:
        """Check if pattern context requirements are met."""
        if not pattern.context_requirements or not context:
            return True

        # Simple context checking (could be more sophisticated)
        for key, required_value in pattern.context_requirements.items():
            if key not in context or context[key] != required_value:
                return False

        return True

    def _get_user_history(self, user_id: str) -> CommandHistory:
        """Get or create user command history."""
        if user_id not in self.user_histories:
            self.user_histories[user_id] = CommandHistory(user_id=user_id)

        return self.user_histories[user_id]

    def _update_user_history(
        self, user_id: str, intent: VoiceCommandIntent, history: CommandHistory
    ) -> None:
        """Update user command history with learning."""
        # Add to command history
        history.command_history.append(
            {
                "intent": intent.primary_intent,
                "confidence": intent.confidence_score,
                "entities": intent.entities,
                "timestamp": intent.created_at.isoformat(),
                "success": intent.confidence_score >= 0.7,  # Simple success metric
            }
        )

        # Update preferred patterns
        if intent.primary_intent != "unknown":
            pattern_key = f"{intent.primary_intent}_{intent.confidence_score:.1f}"
            history.preferred_patterns[pattern_key] = (
                history.preferred_patterns.get(pattern_key, 0) + 1
            )

        # Update entity preferences
        for entity_type, entity_data in intent.entities.items():
            if entity_type not in history.common_entities:
                history.common_entities[entity_type] = {}
            entity_value = entity_data["value"]
            history.common_entities[entity_type][entity_value] = (
                history.common_entities[entity_type].get(entity_value, 0) + 1
            )

        # Update statistics
        history.total_commands += 1
        if intent.confidence_score >= 0.7:
            history.successful_commands += 1
        else:
            history.failed_commands += 1

        history.command_success_rate = history.successful_commands / max(
            history.total_commands, 1
        )
        history.last_updated = datetime.utcnow()

    def _update_processing_stats(
        self, intent: VoiceCommandIntent, processing_time: float
    ) -> None:
        """Update processing statistics."""
        self.processing_stats["total_commands"] += 1

        if intent.primary_intent != "unknown" and intent.confidence_score >= 0.5:
            self.processing_stats["successful_recognition"] += 1

        # Update rolling averages
        current_avg_confidence = self.processing_stats["average_confidence"]
        current_avg_time = self.processing_stats["average_processing_time"]

        self.processing_stats["average_confidence"] = (
            (current_avg_confidence * (self.processing_stats["total_commands"] - 1))
            + intent.confidence_score
        ) / self.processing_stats["total_commands"]

        self.processing_stats["average_processing_time"] = (
            (current_avg_time * (self.processing_stats["total_commands"] - 1))
            + processing_time
        ) / self.processing_stats["total_commands"]

    def add_custom_pattern(self, pattern: CommandPattern) -> bool:
        """Add a custom command pattern."""
        try:
            if pattern.pattern_id in self.command_patterns:
                logger.warning("pattern_already_exists", pattern_id=pattern.pattern_id)
                return False

            self.command_patterns[pattern.pattern_id] = pattern
            logger.info(
                "custom_pattern_added",
                pattern_id=pattern.pattern_id,
                intent=pattern.intent,
            )
            return True

        except Exception as e:
            logger.error("add_custom_pattern_failed", error=str(e))
            return False

    def remove_pattern(self, pattern_id: str) -> bool:
        """Remove a command pattern."""
        if pattern_id in self.command_patterns:
            del self.command_patterns[pattern_id]
            logger.info("pattern_removed", pattern_id=pattern_id)
            return True

        return False

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about command patterns."""
        total_patterns = len(self.command_patterns)
        patterns_by_intent = {}

        for pattern in self.command_patterns.values():
            if pattern.intent not in patterns_by_intent:
                patterns_by_intent[pattern.intent] = 0
            patterns_by_intent[pattern.intent] += 1

        return {
            "total_patterns": total_patterns,
            "patterns_by_intent": patterns_by_intent,
            "processing_stats": self.processing_stats.copy(),
        }

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get learned user preferences."""
        if user_id not in self.user_histories:
            return {}

        history = self.user_histories[user_id]

        return {
            "preferred_intents": history.preferred_patterns,
            "common_entities": history.common_entities,
            "success_rate": history.command_success_rate,
            "total_commands": history.total_commands,
        }

    def reset_user_history(self, user_id: str) -> bool:
        """Reset user command history."""
        if user_id in self.user_histories:
            self.user_histories[user_id] = CommandHistory(user_id=user_id)
            logger.info("user_history_reset", user_id=user_id)
            return True

        return False

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the command processor."""
        success_rate = 0.0
        if self.processing_stats["total_commands"] > 0:
            success_rate = (
                self.processing_stats["successful_recognition"]
                / self.processing_stats["total_commands"]
            )

        return {
            "status": "healthy" if success_rate >= 0.7 else "degraded",
            "total_patterns": len(self.command_patterns),
            "total_users": len(self.user_histories),
            "processing_stats": self.processing_stats.copy(),
            "success_rate": success_rate,
            "average_confidence": self.processing_stats["average_confidence"],
            "average_processing_time": self.processing_stats["average_processing_time"],
        }


# Global voice command processor instance
voice_command_processor = VoiceCommandProcessor()
