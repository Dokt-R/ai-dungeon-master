"""
Memory data validation and constraint enforcement for AI Dungeon Master.

This module provides comprehensive validation for memory events, facts, and operations
to ensure data integrity and enforce business rules for campaign memory management.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List

from packages.shared.logging_config import get_logger
from packages.shared.models import (
    CreateMemoryEventRequest,
    CreateMemoryFactRequest,
    MemoryContext,
    MemoryEvent,
    MemoryFact,
    MemoryQueryRequest,
)

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    suggestions: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.suggestions is None:
            self.suggestions = []


class MemoryValidator:
    """
    Comprehensive validator for memory data with business rule enforcement.
    """

    def __init__(self):
        self.logger = get_logger(f"{__name__}.MemoryValidator")

        # Define validation constraints
        self._max_description_length = 1000
        self._max_subject_length = 200
        self._max_participants = 20
        self._max_tags = 10
        self._max_related_events = 50
        self._min_confidence_threshold = 0.1

        # Define allowed values
        self._valid_event_types = {"narrative", "combat", "social", "exploration"}
        self._valid_fact_types = {
            "npc",
            "location",
            "quest",
            "relationship",
            "knowledge",
        }

        # Define reserved words that cannot be used in certain fields
        self._reserved_words = {
            "system",
            "admin",
            "null",
            "undefined",
            "none",
            "n/a",
            "unknown",
        }

    def validate_memory_event(self, event: MemoryEvent) -> ValidationResult:
        """
        Validate a memory event against business rules and constraints.

        Args:
            event: MemoryEvent to validate

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []
        suggestions = []

        # Basic field validation
        if not event.event_id or not event.event_id.strip():
            errors.append("Event ID cannot be empty")

        if not self._is_valid_id_format(event.event_id):
            errors.append(
                "Event ID must contain only alphanumeric characters, underscores, and hyphens"
            )

        # Skip basic event_type and participants validation here - will be handled later
        # if event.event_type not in self._valid_event_types:
        #     errors.append(
        #         f"Invalid event type: {event.event_type}. Must be one of: {', '.join(self._valid_event_types)}"
        #     )

        if not event.description or not event.description.strip():
            errors.append("Event description cannot be empty")
        elif len(event.description) > self._max_description_length:
            errors.append(
                f"Event description exceeds maximum length of {self._max_description_length} characters"
            )

        # Skip basic participants validation here - will be handled later
        # if not event.participants or len(event.participants) == 0:
        #     errors.append("Event must have at least one participant")
        elif event.participants and len(event.participants) > self._max_participants:
            errors.append(
                f"Event cannot have more than {self._max_participants} participants"
            )

        # Validate timestamp
        if event.timestamp > datetime.utcnow() + timedelta(minutes=5):
            warnings.append("Event timestamp is significantly in the future")

        if event.timestamp < datetime.utcnow() - timedelta(days=365 * 10):
            warnings.append("Event timestamp is more than 10 years in the past")

        # Business rule validation - call this early to catch specific business rules
        business_issues = self._validate_event_business_rules(event)
        errors.extend(business_issues)

        # Validate participants
        participant_issues = self._validate_participants(event.participants)
        errors.extend(participant_issues)

        # Validate location if provided
        if event.location:
            location_issues = self._validate_location(event.location)
            errors.extend(location_issues)

        # Validate metadata
        if event.metadata:
            metadata_issues = self._validate_metadata(event.metadata)
            errors.extend(metadata_issues)

        # Additional validation for manually modified fields
        if event.event_type not in self._valid_event_types:
            errors.append(
                f"Invalid event type: {event.event_type}. Must be one of: {', '.join(self._valid_event_types)}"
            )

        if not event.participants or len(event.participants) == 0:
            errors.append("Event must have at least one participant")

        # Generate suggestions
        if not event.location and event.event_type in ["combat", "exploration"]:
            suggestions.append(
                "Consider adding location information for combat and exploration events"
            )

        if len(event.description) < 50:
            suggestions.append(
                "Consider providing more detailed event descriptions for better AI context"
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def validate_memory_fact(self, fact: MemoryFact) -> ValidationResult:
        """
        Validate a memory fact against business rules and constraints.

        Args:
            fact: MemoryFact to validate

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []
        suggestions = []

        # Basic field validation
        if not fact.fact_id or not fact.fact_id.strip():
            errors.append("Fact ID cannot be empty")

        if not self._is_valid_id_format(fact.fact_id):
            errors.append(
                "Fact ID must contain only alphanumeric characters, underscores, and hyphens"
            )

        # Skip basic fact_type validation here - will be handled later
        # if fact.fact_type not in self._valid_fact_types:
        #     errors.append(
        #         f"Invalid fact type: {fact.fact_type}. Must be one of: {', '.join(self._valid_fact_types)}"
        #     )

        if not fact.subject or not fact.subject.strip():
            errors.append("Fact subject cannot be empty")
        elif len(fact.subject) > self._max_subject_length:
            errors.append(
                f"Fact subject exceeds maximum length of {self._max_subject_length} characters"
            )

        if not fact.description or not fact.description.strip():
            errors.append("Fact description cannot be empty")

        if fact.confidence < 0.0 or fact.confidence > 1.0:
            errors.append("Confidence must be between 0.0 and 1.0")
        elif fact.confidence < self._min_confidence_threshold:
            warnings.append(
                f"Confidence is below recommended threshold of {self._min_confidence_threshold}"
            )

        # Validate source
        if not fact.source or not fact.source.strip():
            errors.append("Fact source cannot be empty")

        # Validate tags
        if fact.tags:
            if len(fact.tags) > self._max_tags:
                errors.append(f"Fact cannot have more than {self._max_tags} tags")

            tag_issues = self._validate_tags(fact.tags)
            errors.extend(tag_issues)

        # Validate related events
        if fact.related_events:
            if len(fact.related_events) > self._max_related_events:
                errors.append(
                    f"Fact cannot have more than {self._max_related_events} related events"
                )

            event_id_issues = [
                eid for eid in fact.related_events if not self._is_valid_id_format(eid)
            ]
            if event_id_issues:
                errors.append(
                    f"Invalid event IDs in related_events: {', '.join(event_id_issues)}"
                )

        # Business rule validation - call this before checking for errors
        business_issues = self._validate_fact_business_rules(fact)
        errors.extend(business_issues)

        # Additional validation for manually modified fields
        if fact.fact_type not in self._valid_fact_types:
            errors.append(
                f"Invalid fact type: {fact.fact_type}. Must be one of: {', '.join(self._valid_fact_types)}"
            )

        # Generate suggestions
        if fact.confidence > 0.9 and len(fact.description) < 100:
            suggestions.append(
                "High confidence facts should have detailed descriptions"
            )

        if not fact.tags:
            suggestions.append("Consider adding tags for better searchability")

        if fact.fact_type == "relationship" and "relationship" not in (fact.tags or []):
            suggestions.append(
                "Consider adding 'relationship' tag for relationship-type facts"
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def validate_memory_context(self, context: MemoryContext) -> ValidationResult:
        """
        Validate a memory context for AI integration.

        Args:
            context: MemoryContext to validate

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []
        suggestions = []

        # Validate recent events
        if not context.recent_events:
            warnings.append(
                "Memory context should include recent events for better AI context"
            )

        for event in context.recent_events:
            event_result = self.validate_memory_event(event)
            if not event_result.is_valid:
                errors.append(
                    f"Invalid event in context: {event.event_id} - {event_result.errors}"
                )

        # Validate relevant facts
        if not context.relevant_facts:
            warnings.append(
                "Memory context should include relevant facts for better AI context"
            )

        for fact in context.relevant_facts:
            fact_result = self.validate_memory_fact(fact)
            if not fact_result.is_valid:
                errors.append(
                    f"Invalid fact in context: {fact.fact_id} - {fact_result.errors}"
                )

        # Validate character knowledge
        if not context.character_knowledge:
            warnings.append("Character knowledge mapping is empty")

        for char_name, knowledge in context.character_knowledge.items():
            if not isinstance(knowledge, list):
                errors.append(f"Character knowledge for {char_name} must be a list")
            elif len(knowledge) == 0:
                warnings.append(f"Character {char_name} has no knowledge entries")

        # Validate world state
        if not context.world_state:
            warnings.append("World state snapshot is empty")

        # Validate summary
        if not context.summary or not context.summary.strip():
            errors.append("Memory context summary cannot be empty")
        elif len(context.summary) > 2000:
            errors.append("Memory context summary exceeds 2000 characters")

        # Validate context size
        if context.context_size < 0:
            errors.append("Context size cannot be negative")
        elif context.context_size > 100000:
            warnings.append("Context size is very large, may exceed AI token limits")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def validate_create_event_request(
        self, request: CreateMemoryEventRequest
    ) -> ValidationResult:
        """
        Validate a create memory event request.

        Args:
            request: CreateMemoryEventRequest to validate

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []
        suggestions = []

        # Validate event type
        if request.event_type not in self._valid_event_types:
            errors.append(f"Invalid event type: {request.event_type}")

        # Validate description
        if not request.description or not request.description.strip():
            errors.append("Event description cannot be empty")
        elif len(request.description) > self._max_description_length:
            errors.append(
                f"Event description exceeds maximum length of {self._max_description_length} characters"
            )

        # Validate participants
        if not request.participants or len(request.participants) == 0:
            errors.append("Event must have at least one participant")
        elif len(request.participants) > self._max_participants:
            errors.append(
                f"Event cannot have more than {self._max_participants} participants"
            )

        participant_issues = self._validate_participants(request.participants)
        errors.extend(participant_issues)

        # Validate location if provided
        if request.location:
            location_issues = self._validate_location(request.location)
            errors.extend(location_issues)

        # Validate metadata if provided
        if request.metadata:
            metadata_issues = self._validate_metadata(request.metadata)
            errors.extend(metadata_issues)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def validate_create_fact_request(
        self, request: CreateMemoryFactRequest
    ) -> ValidationResult:
        """
        Validate a create memory fact request.

        Args:
            request: CreateMemoryFactRequest to validate

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []
        suggestions = []

        # Validate fact type
        if request.fact_type not in self._valid_fact_types:
            errors.append(f"Invalid fact type: {request.fact_type}")

        # Validate subject
        if not request.subject or not request.subject.strip():
            errors.append("Fact subject cannot be empty")
        elif len(request.subject) > self._max_subject_length:
            errors.append(
                f"Fact subject exceeds maximum length of {self._max_subject_length} characters"
            )

        # Validate description
        if not request.description or not request.description.strip():
            errors.append("Fact description cannot be empty")

        # Validate confidence
        if request.confidence < 0.0 or request.confidence > 1.0:
            errors.append("Confidence must be between 0.0 and 1.0")
        elif request.confidence < self._min_confidence_threshold:
            warnings.append(
                f"Confidence is below recommended threshold of {self._min_confidence_threshold}"
            )

        # Validate source
        if not request.source or not request.source.strip():
            errors.append("Fact source cannot be empty")

        # Validate tags if provided
        if request.tags:
            if len(request.tags) > self._max_tags:
                errors.append(f"Fact cannot have more than {self._max_tags} tags")
            tag_issues = self._validate_tags(request.tags)
            errors.extend(tag_issues)

        # Validate related events if provided
        if request.related_events:
            if len(request.related_events) > self._max_related_events:
                errors.append(
                    f"Fact cannot have more than {self._max_related_events} related events"
                )
            event_id_issues = [
                eid
                for eid in request.related_events
                if not self._is_valid_id_format(eid)
            ]
            if event_id_issues:
                errors.append(f"Invalid event IDs: {', '.join(event_id_issues)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def validate_query_request(self, request: MemoryQueryRequest) -> ValidationResult:
        """
        Validate a memory query request.

        Args:
            request: MemoryQueryRequest to validate

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []
        suggestions = []

        # Validate query type
        valid_query_types = {"events", "facts", "context"}
        if request.query_type not in valid_query_types:
            errors.append(
                f"Invalid query type: {request.query_type}. Must be one of: {', '.join(valid_query_types)}"
            )

        # Validate limit
        if request.limit is not None:
            if request.limit < 1:
                errors.append("Query limit must be at least 1")
            elif request.limit > 1000:
                errors.append("Query limit cannot exceed 1000")

        # Validate filters if provided
        if request.filters:
            filter_issues = self._validate_query_filters(request.filters)
            errors.extend(filter_issues)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _is_valid_id_format(self, id_str: str) -> bool:
        """Check if an ID string has valid format."""
        if not id_str or not isinstance(id_str, str):
            return False

        # Must contain only alphanumeric, underscore, and hyphen
        pattern = r"^[a-zA-Z0-9_-]+$"
        return bool(re.match(pattern, id_str))

    def _validate_participants(self, participants: List[str]) -> List[str]:
        """Validate participant names."""
        errors = []

        if not all(isinstance(p, str) and p.strip() for p in participants):
            errors.append("All participants must be non-empty strings")

        # Check for reserved words
        for participant in participants:
            if participant.lower().strip() in self._reserved_words:
                errors.append(f"Participant name '{participant}' is reserved")

        # Check for duplicates
        if len(participants) != len(set(p.lower().strip() for p in participants)):
            errors.append("Duplicate participant names found")

        # Check length constraints
        for participant in participants:
            if len(participant) > 100:
                errors.append(
                    f"Participant name '{participant}' exceeds 100 characters"
                )

        return errors

    def _validate_location(self, location: str) -> List[str]:
        """Validate location string."""
        errors = []

        if not isinstance(location, str):
            errors.append("Location must be a string")
            return errors

        if not location.strip():
            errors.append("Location cannot be empty")
        elif len(location) > 200:
            errors.append("Location exceeds 200 characters")

        if location.lower().strip() in self._reserved_words:
            errors.append(f"Location '{location}' uses reserved word")

        return errors

    def _validate_tags(self, tags: List[str]) -> List[str]:
        """Validate tag list."""
        errors = []

        if not all(isinstance(tag, str) and tag.strip() for tag in tags):
            errors.append("All tags must be non-empty strings")

        # Check for duplicates
        if len(tags) != len(set(t.lower().strip() for t in tags)):
            errors.append("Duplicate tags found")

        # Check length constraints
        for tag in tags:
            if len(tag) > 50:
                errors.append(f"Tag '{tag}' exceeds 50 characters")

        # Check for reserved words
        for tag in tags:
            if tag.lower().strip() in self._reserved_words:
                errors.append(f"Tag '{tag}' uses reserved word")

        return errors

    def _validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Validate metadata dictionary."""
        errors = []

        if not isinstance(metadata, dict):
            errors.append("Metadata must be a dictionary")
            return errors

        # Check size constraints
        if len(str(metadata)) > 5000:  # 5KB limit
            errors.append("Metadata size exceeds 5KB limit")

        # Check nesting depth (prevent deeply nested structures)
        def check_nesting(obj, depth=0):
            if depth > 3:
                return True  # Too deep
            if isinstance(obj, dict):
                return any(check_nesting(v, depth + 1) for v in obj.values())
            elif isinstance(obj, list):
                return any(check_nesting(item, depth + 1) for item in obj)
            return False

        if check_nesting(metadata):
            errors.append("Metadata nesting depth exceeds 3 levels")

        return errors

    def _validate_query_filters(self, filters: Dict[str, Any]) -> List[str]:
        """Validate query filters."""
        errors = []

        # Define allowed filter keys based on query type
        allowed_filters = {
            "event_type": list(self._valid_event_types),
            "fact_type": list(self._valid_fact_types),
            "participant": None,  # Any string
            "subject": None,  # Any string
            "confidence_min": None,  # Float 0.0-1.0
            "confidence_max": None,  # Float 0.0-1.0
            "timestamp_after": None,  # ISO datetime string
            "timestamp_before": None,  # ISO datetime string
            "tags": None,  # List of strings
        }

        for key, value in filters.items():
            if key not in allowed_filters:
                errors.append(f"Unknown filter key: {key}")
                continue

            # Type-specific validation
            if key in ["event_type"] and value not in allowed_filters[key]:
                errors.append(f"Invalid {key}: {value}")
            elif key in ["fact_type"] and value not in allowed_filters[key]:
                errors.append(f"Invalid {key}: {value}")
            elif key in ["confidence_min", "confidence_max"]:
                if not isinstance(value, (int, float)) or value < 0.0 or value > 1.0:
                    errors.append(f"{key} must be a number between 0.0 and 1.0")
            elif key in ["timestamp_after", "timestamp_before"]:
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"Invalid ISO datetime format for {key}")

        return errors

    def _validate_event_business_rules(self, event: MemoryEvent) -> List[str]:
        """Validate business rules specific to memory events."""
        errors = []

        # Business rule: Combat events should have at least 2 participants
        if event.event_type == "combat" and len(event.participants) < 2:
            errors.append("Combat events should have at least 2 participants")

        # Business rule: Exploration events should have a location
        if event.event_type == "exploration" and not event.location:
            errors.append("Exploration events should specify a location")

        # Business rule: Event descriptions should be descriptive
        if len(event.description.split()) < 5:
            errors.append(
                "Event description should be more descriptive (at least 5 words)"
            )

        return errors

    def _validate_fact_business_rules(self, fact: MemoryFact) -> List[str]:
        """Validate business rules specific to memory facts."""
        errors = []

        # Business rule: NPC facts should have relationship information
        if fact.fact_type == "npc" and "relationship" not in fact.description.lower():
            errors.append("NPC facts should include relationship information")

        # Business rule: Quest facts should mention objectives or progress
        if fact.fact_type == "quest":
            quest_keywords = ["objective", "goal", "progress", "complete", "task"]
            if not any(
                keyword in fact.description.lower() for keyword in quest_keywords
            ):
                errors.append(
                    "Quest facts should mention objectives, goals, or progress"
                )

        # Business rule: High confidence facts should have sources
        if fact.confidence > 0.8 and not fact.source:
            errors.append("High confidence facts must have a source")

        return errors


# Global memory validator instance
memory_validator = MemoryValidator()
