"""
Campaign Memory Service for AI Dungeon Master.

This module provides the core memory management functionality for campaign data,
including memory events, facts, and AI integration context. It serves as the
central service for all memory-related operations in the AI Dungeon Master system.

Key Features:
- Memory event and fact CRUD operations
- AI context generation for memory integration
- Memory search and retrieval with filtering
- Data validation and integrity enforcement
- Integration with campaign and character data

Architecture:
- Uses in-memory storage for MVP (will be replaced with persistent storage)
- Integrates with shared memory validation module
- Provides clean interface for AI integration
- Follows repository pattern for data access
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from packages.shared.logging_config import get_logger
from packages.shared.memory_validation import ValidationResult, memory_validator
from packages.shared.models import (
    CreateMemoryEventRequest,
    CreateMemoryFactRequest,
    MemoryContext,
    MemoryEvent,
    MemoryFact,
    MemoryOperation,
    MemoryQueryRequest,
    UpdateMemoryEventRequest,
    UpdateMemoryFactRequest,
)


@dataclass
class MemoryStorage:
    """In-memory storage for memory data (MVP implementation)."""

    events: Dict[str, MemoryEvent] = field(default_factory=dict)
    facts: Dict[str, MemoryFact] = field(default_factory=dict)
    event_index: Dict[str, Set[str]] = field(default_factory=dict)  # For quick lookups
    fact_index: Dict[str, Set[str]] = field(default_factory=dict)  # For quick lookups


class CampaignMemoryService:
    """
    Core service for managing campaign memory data.

    This service handles all memory-related operations including:
    - Creating, reading, updating, and deleting memory events and facts
    - Generating AI context from memory data
    - Searching and filtering memory data
    - Data validation and integrity enforcement

    The service uses in-memory storage for the MVP but is designed to be
    easily replaced with persistent storage solutions.
    """

    def __init__(self, campaign_id: Optional[str] = None):
        """
        Initialize the CampaignMemoryService.

        Args:
            campaign_id: Optional campaign identifier for multi-campaign support
        """
        self.campaign_id = campaign_id or "default"
        self.logger = get_logger(
            f"{__name__}.CampaignMemoryService[{self.campaign_id}]"
        )

        # Initialize in-memory storage
        self._storage = MemoryStorage()

        # Initialize indexes for efficient querying
        self._initialize_indexes()

        self.logger.info(
            "CampaignMemoryService initialized", campaign_id=self.campaign_id
        )

    def _initialize_indexes(self) -> None:
        """Initialize search indexes for memory data."""
        # Event indexes
        self._storage.event_index["participants"] = set()
        self._storage.event_index["event_type"] = set()
        self._storage.event_index["location"] = set()

        # Fact indexes
        self._storage.fact_index["subject"] = set()
        self._storage.fact_index["fact_type"] = set()
        self._storage.fact_index["tags"] = set()

    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        return f"event_{uuid.uuid4().hex[:16]}"

    def _generate_fact_id(self) -> str:
        """Generate a unique fact ID."""
        return f"fact_{uuid.uuid4().hex[:16]}"

    def _update_indexes_for_event(
        self, event: MemoryEvent, operation: str = "add"
    ) -> None:
        """Update search indexes for a memory event."""
        if operation == "add":
            # Add to indexes
            for participant in event.participants:
                if "participants" not in self._storage.event_index:
                    self._storage.event_index["participants"] = set()
                self._storage.event_index["participants"].add(participant)

            if "event_type" not in self._storage.event_index:
                self._storage.event_index["event_type"] = set()
            self._storage.event_index["event_type"].add(event.event_type)

            if event.location:
                if "location" not in self._storage.event_index:
                    self._storage.event_index["location"] = set()
                self._storage.event_index["location"].add(event.location)

        elif operation == "remove":
            # Remove from indexes (simplified - would need cleanup in production)
            pass

    def _update_indexes_for_fact(
        self, fact: MemoryFact, operation: str = "add"
    ) -> None:
        """Update search indexes for a memory fact."""
        if operation == "add":
            # Add to indexes
            if "subject" not in self._storage.fact_index:
                self._storage.fact_index["subject"] = set()
            self._storage.fact_index["subject"].add(fact.subject)

            if "fact_type" not in self._storage.fact_index:
                self._storage.fact_index["fact_type"] = set()
            self._storage.fact_index["fact_type"].add(fact.fact_type)

            for tag in fact.tags:
                if "tags" not in self._storage.fact_index:
                    self._storage.fact_index["tags"] = set()
                self._storage.fact_index["tags"].add(tag)

        elif operation == "remove":
            # Remove from indexes (simplified - would need cleanup in production)
            pass

    def _validate_memory_event(self, event: MemoryEvent) -> ValidationResult:
        """Validate a memory event."""
        return memory_validator.validate_memory_event(event)

    def _validate_memory_fact(self, fact: MemoryFact) -> ValidationResult:
        """Validate a memory fact."""
        return memory_validator.validate_memory_fact(fact)

    def _create_memory_operation(
        self,
        operation: str,
        success: bool,
        memory_id: str,
        memory_type: str,
        error: Optional[str] = None,
    ) -> MemoryOperation:
        """Create a memory operation result."""
        return MemoryOperation(
            operation=operation,
            success=success,
            memory_id=memory_id,
            memory_type=memory_type,
            error=error,
        )

    # Memory Event CRUD Operations
    def create_memory_event_from_request(
        self, request: CreateMemoryEventRequest, user: str = "system"
    ) -> MemoryOperation:
        """
        Create a new memory event from a request.

        Args:
            request: The create event request
            user: User performing the operation

        Returns:
            MemoryOperation result
        """
        try:
            # Validate the request
            validation_result = memory_validator.validate_create_event_request(request)
            if not validation_result.is_valid:
                return self._create_memory_operation(
                    "create",
                    False,
                    "",
                    "event",
                    f"Validation failed: {', '.join(validation_result.errors)}",
                )

            # Generate event ID
            event_id = self._generate_event_id()

            # Create the memory event
            event = MemoryEvent(
                event_id=event_id,
                timestamp=datetime.utcnow(),
                event_type=request.event_type,
                description=request.description,
                participants=request.participants,
                location=request.location,
                metadata=request.metadata or {},
            )

            # Validate the created event
            event_validation = self._validate_memory_event(event)
            if not event_validation.is_valid:
                return self._create_memory_operation(
                    "create",
                    False,
                    event_id,
                    "event",
                    f"Event validation failed: {', '.join(event_validation.errors)}",
                )

            # Store the event
            self._storage.events[event_id] = event
            self._update_indexes_for_event(event, "add")

            self.logger.info(
                "Memory event created",
                event_id=event_id,
                event_type=request.event_type,
                participant_count=len(request.participants),
                user=user,
            )

            return self._create_memory_operation("create", True, event_id, "event")

        except Exception as e:
            self.logger.error(
                "Failed to create memory event",
                error=str(e),
                error_type=type(e).__name__,
                user=user,
            )
            return self._create_memory_operation(
                "create", False, "", "event", f"Internal error: {str(e)}"
            )

    def get_memory_event(self, event_id: str) -> Optional[MemoryEvent]:
        """Get a memory event by ID."""
        return self._storage.events.get(event_id)

    def get_memory_events(
        self,
        event_type: Optional[str] = None,
        participant: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryEvent]:
        """Get memory events with optional filtering."""
        events = list(self._storage.events.values())

        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if participant:
            events = [e for e in events if participant in e.participants]

        # Sort by timestamp (newest first) and apply limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def update_memory_event(
        self, event_id: str, updates: UpdateMemoryEventRequest, user: str = "system"
    ) -> MemoryOperation:
        """Update an existing memory event."""
        try:
            # Get existing event
            existing_event = self._storage.events.get(event_id)
            if not existing_event:
                return self._create_memory_operation(
                    "update", False, event_id, "event", "Event not found"
                )

            # Create updated event
            updated_data = existing_event.model_dump()

            if updates.description is not None:
                updated_data["description"] = updates.description
            if updates.participants is not None:
                updated_data["participants"] = updates.participants
            if updates.location is not None:
                updated_data["location"] = updates.location
            if updates.metadata is not None:
                updated_data["metadata"] = updates.metadata

            updated_data["version"] = existing_event.version + 1
            updated_data["updated_at"] = datetime.utcnow()

            updated_event = MemoryEvent(**updated_data)

            # Validate updated event
            validation_result = self._validate_memory_event(updated_event)
            if not validation_result.is_valid:
                return self._create_memory_operation(
                    "update",
                    False,
                    event_id,
                    "event",
                    f"Validation failed: {', '.join(validation_result.errors)}",
                )

            # Store updated event
            self._storage.events[event_id] = updated_event

            self.logger.info(
                "Memory event updated",
                event_id=event_id,
                version=updated_event.version,
                user=user,
            )

            return self._create_memory_operation("update", True, event_id, "event")

        except Exception as e:
            self.logger.error(
                "Failed to update memory event",
                event_id=event_id,
                error=str(e),
                user=user,
            )
            return self._create_memory_operation(
                "update", False, event_id, "event", f"Internal error: {str(e)}"
            )

    def delete_memory_event(
        self, event_id: str, user: str = "system"
    ) -> MemoryOperation:
        """Delete a memory event."""
        try:
            if event_id not in self._storage.events:
                return self._create_memory_operation(
                    "delete", False, event_id, "event", "Event not found"
                )

            # Remove event
            deleted_event = self._storage.events.pop(event_id)
            self._update_indexes_for_event(deleted_event, "remove")

            self.logger.info(
                "Memory event deleted",
                event_id=event_id,
                event_type=deleted_event.event_type,
                user=user,
            )

            return self._create_memory_operation("delete", True, event_id, "event")

        except Exception as e:
            self.logger.error(
                "Failed to delete memory event",
                event_id=event_id,
                error=str(e),
                user=user,
            )
            return self._create_memory_operation(
                "delete", False, event_id, "event", f"Internal error: {str(e)}"
            )

    # Memory Fact CRUD Operations
    def create_memory_fact_from_request(
        self, request: CreateMemoryFactRequest, user: str = "system"
    ) -> MemoryOperation:
        """Create a new memory fact from a request."""
        try:
            # Validate the request
            validation_result = memory_validator.validate_create_fact_request(request)
            if not validation_result.is_valid:
                return self._create_memory_operation(
                    "create",
                    False,
                    "",
                    "fact",
                    f"Validation failed: {', '.join(validation_result.errors)}",
                )

            # Generate fact ID
            fact_id = self._generate_fact_id()

            # Create the memory fact
            fact = MemoryFact(
                fact_id=fact_id,
                fact_type=request.fact_type,
                subject=request.subject,
                description=request.description,
                confidence=request.confidence,
                source=request.source,
                tags=request.tags or [],
                related_events=request.related_events or [],
            )

            # Validate the created fact
            fact_validation = self._validate_memory_fact(fact)
            if not fact_validation.is_valid:
                return self._create_memory_operation(
                    "create",
                    False,
                    fact_id,
                    "fact",
                    f"Fact validation failed: {', '.join(fact_validation.errors)}",
                )

            # Store the fact
            self._storage.facts[fact_id] = fact
            self._update_indexes_for_fact(fact, "add")

            self.logger.info(
                "Memory fact created",
                fact_id=fact_id,
                fact_type=request.fact_type,
                confidence=request.confidence,
                tag_count=len(request.tags or []),
                user=user,
            )

            return self._create_memory_operation("create", True, fact_id, "fact")

        except Exception as e:
            self.logger.error(
                "Failed to create memory fact",
                error=str(e),
                error_type=type(e).__name__,
                user=user,
            )
            return self._create_memory_operation(
                "create", False, "", "fact", f"Internal error: {str(e)}"
            )

    def get_memory_fact(self, fact_id: str) -> Optional[MemoryFact]:
        """Get a memory fact by ID."""
        return self._storage.facts.get(fact_id)

    def get_memory_facts(
        self,
        fact_type: Optional[str] = None,
        subject: Optional[str] = None,
        tag: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 100,
    ) -> List[MemoryFact]:
        """Get memory facts with optional filtering."""
        facts = list(self._storage.facts.values())

        # Apply filters
        if fact_type:
            facts = [f for f in facts if f.fact_type == fact_type]

        if subject:
            facts = [f for f in facts if subject.lower() in f.subject.lower()]

        if tag:
            facts = [f for f in facts if tag in f.tags]

        if min_confidence > 0.0:
            facts = [f for f in facts if f.confidence >= min_confidence]

        # Sort by confidence and last updated (highest confidence, newest first)
        facts.sort(key=lambda f: (-f.confidence, -f.last_updated.timestamp()))
        return facts[:limit]

    def update_memory_fact(
        self, fact_id: str, updates: UpdateMemoryFactRequest, user: str = "system"
    ) -> MemoryOperation:
        """Update an existing memory fact."""
        try:
            # Get existing fact
            existing_fact = self._storage.facts.get(fact_id)
            if not existing_fact:
                return self._create_memory_operation(
                    "update", False, fact_id, "fact", "Fact not found"
                )

            # Create updated fact
            updated_data = existing_fact.model_dump()

            if updates.description is not None:
                updated_data["description"] = updates.description
            if updates.confidence is not None:
                updated_data["confidence"] = updates.confidence
            if updates.tags is not None:
                updated_data["tags"] = updates.tags
            if updates.related_events is not None:
                updated_data["related_events"] = updates.related_events

            updated_data["last_updated"] = datetime.utcnow()

            updated_fact = MemoryFact(**updated_data)

            # Validate updated fact
            validation_result = self._validate_memory_fact(updated_fact)
            if not validation_result.is_valid:
                return self._create_memory_operation(
                    "update",
                    False,
                    fact_id,
                    "fact",
                    f"Validation failed: {', '.join(validation_result.errors)}",
                )

            # Store updated fact
            self._storage.facts[fact_id] = updated_fact

            self.logger.info(
                "Memory fact updated",
                fact_id=fact_id,
                new_confidence=updates.confidence,
                tag_count=len(updates.tags or []),
                user=user,
            )

            return self._create_memory_operation("update", True, fact_id, "fact")

        except Exception as e:
            self.logger.error(
                "Failed to update memory fact", fact_id=fact_id, error=str(e), user=user
            )
            return self._create_memory_operation(
                "update", False, fact_id, "fact", f"Internal error: {str(e)}"
            )

    def delete_memory_fact(self, fact_id: str, user: str = "system") -> MemoryOperation:
        """Delete a memory fact."""
        try:
            if fact_id not in self._storage.facts:
                return self._create_memory_operation(
                    "delete", False, fact_id, "fact", "Fact not found"
                )

            # Remove fact
            deleted_fact = self._storage.facts.pop(fact_id)
            self._update_indexes_for_fact(deleted_fact, "remove")

            self.logger.info(
                "Memory fact deleted",
                fact_id=fact_id,
                fact_type=deleted_fact.fact_type,
                user=user,
            )

            return self._create_memory_operation("delete", True, fact_id, "fact")

        except Exception as e:
            self.logger.error(
                "Failed to delete memory fact", fact_id=fact_id, error=str(e), user=user
            )
            return self._create_memory_operation(
                "delete", False, fact_id, "fact", f"Internal error: {str(e)}"
            )

    # Query and Context Generation
    def query_memory(self, request: MemoryQueryRequest) -> Dict[str, Any]:
        """Query memory data with flexible filtering."""
        try:
            # Validate query request
            validation_result = memory_validator.validate_query_request(request)
            if not validation_result.is_valid:
                return {
                    "success": False,
                    "error": f"Query validation failed: {', '.join(validation_result.errors)}",
                    "data": [],
                }

            # Execute query based on type
            if request.query_type == "events":
                events = self.get_memory_events(
                    event_type=request.filters.get("event_type")
                    if request.filters
                    else None,
                    participant=request.filters.get("participant")
                    if request.filters
                    else None,
                    limit=request.limit or 100,
                )
                return {
                    "success": True,
                    "query_type": "events",
                    "count": len(events),
                    "data": events,
                }

            elif request.query_type == "facts":
                facts = self.get_memory_facts(
                    fact_type=request.filters.get("fact_type")
                    if request.filters
                    else None,
                    subject=request.filters.get("subject") if request.filters else None,
                    tag=request.filters.get("tag") if request.filters else None,
                    min_confidence=request.filters.get("confidence_min", 0.0)
                    if request.filters
                    else 0.0,
                    limit=request.limit or 100,
                )
                return {
                    "success": True,
                    "query_type": "facts",
                    "count": len(facts),
                    "data": facts,
                }

            elif request.query_type == "context":
                context = self.generate_ai_context()
                return {"success": True, "query_type": "context", "data": context}

            else:
                return {
                    "success": False,
                    "error": f"Unsupported query type: {request.query_type}",
                    "data": [],
                }

        except Exception as e:
            self.logger.error(
                "Memory query failed", error=str(e), query_type=request.query_type
            )
            return {
                "success": False,
                "error": f"Query execution failed: {str(e)}",
                "data": [],
            }

    def generate_ai_context(
        self, max_events: int = 10, max_facts: int = 20
    ) -> MemoryContext:
        """Generate AI context from memory data."""
        try:
            # Get recent events (last 24 hours by default)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_events = [
                event
                for event in self._storage.events.values()
                if event.timestamp >= recent_cutoff
            ]
            recent_events.sort(key=lambda e: e.timestamp, reverse=True)
            recent_events = recent_events[:max_events]

            # Get high-confidence facts
            high_confidence_facts = [
                fact for fact in self._storage.facts.values() if fact.confidence >= 0.7
            ]
            high_confidence_facts.sort(key=lambda f: f.confidence, reverse=True)
            high_confidence_facts = high_confidence_facts[:max_facts]

            # Build character knowledge mapping (placeholder)
            character_knowledge = {}
            for fact in high_confidence_facts:
                if fact.fact_type == "knowledge":
                    # Extract character names from fact (simplified)
                    # In production, this would use NLP or structured data
                    pass

            # Build world state summary (placeholder)
            world_state = {
                "total_events": len(self._storage.events),
                "total_facts": len(self._storage.facts),
                "last_activity": datetime.utcnow().isoformat(),
                "campaign_id": self.campaign_id,
            }

            # Generate summary
            event_count = len(recent_events)
            fact_count = len(high_confidence_facts)
            summary = f"Campaign memory context: {event_count} recent events, {fact_count} high-confidence facts."

            # Estimate token count (rough approximation)
            total_text = " ".join(
                [e.description for e in recent_events]
                + [f.description for f in high_confidence_facts]
            )
            context_size = len(total_text) // 4  # Rough token estimation

            return MemoryContext(
                recent_events=recent_events,
                relevant_facts=high_confidence_facts,
                character_knowledge=character_knowledge,
                world_state=world_state,
                summary=summary,
                context_size=context_size,
            )

        except Exception as e:
            self.logger.error("Failed to generate AI context", error=str(e))
            # Return empty context on error
            return MemoryContext(
                recent_events=[],
                relevant_facts=[],
                character_knowledge={},
                world_state={"error": str(e)},
                summary=f"Error generating context: {str(e)}",
                context_size=0,
            )

    # Service Management
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory service statistics."""
        return {
            "campaign_id": self.campaign_id,
            "total_events": len(self._storage.events),
            "total_facts": len(self._storage.facts),
            "event_types": list(self._storage.event_index.get("event_type", set())),
            "fact_types": list(self._storage.fact_index.get("fact_type", set())),
            "last_activity": datetime.utcnow().isoformat(),
            "memory_usage_estimate": self._estimate_memory_usage(),
        }

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes."""
        # Rough estimation - would be more accurate with actual memory profiling
        event_memory = sum(len(str(event)) for event in self._storage.events.values())
        fact_memory = sum(len(str(fact)) for fact in self._storage.facts.values())
        return event_memory + fact_memory

    def clear_memory(self, user: str = "system") -> bool:
        """Clear all memory data (use with caution)."""
        try:
            self._storage = MemoryStorage()
            self._initialize_indexes()

            self.logger.warning(
                "Memory cleared", campaign_id=self.campaign_id, user=user
            )
            return True

        except Exception as e:
            self.logger.error("Failed to clear memory", error=str(e))
            return False


# Global service instance (for MVP - would use dependency injection in production)
campaign_memory_service = CampaignMemoryService()
