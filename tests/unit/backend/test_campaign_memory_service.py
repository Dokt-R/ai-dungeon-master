"""
Unit tests for CampaignMemoryService.

Tests cover:
- Service initialization and configuration
- Memory event CRUD operations
- Memory fact CRUD operations
- Memory querying and context generation
- Error handling and edge cases
- Integration with validation module
"""

from datetime import datetime, timedelta
from unittest.mock import patch

from packages.backend.components.campaign_memory_service import CampaignMemoryService
from packages.shared.models import (
    CreateMemoryEventRequest,
    CreateMemoryFactRequest,
    MemoryContext,
    MemoryEvent,
    MemoryFact,
    MemoryQueryRequest,
    UpdateMemoryEventRequest,
    UpdateMemoryFactRequest,
)


class TestCampaignMemoryServiceInitialization:
    """Test CampaignMemoryService initialization and configuration."""

    def test_service_initialization_default_campaign(self):
        """Test service initialization with default campaign ID."""
        service = CampaignMemoryService()

        assert service.campaign_id == "default"
        assert service._storage is not None
        assert service._storage.events == {}
        assert service._storage.facts == {}

    def test_service_initialization_custom_campaign(self):
        """Test service initialization with custom campaign ID."""
        service = CampaignMemoryService(campaign_id="test_campaign")

        assert service.campaign_id == "test_campaign"
        assert service._storage is not None

    def test_index_initialization(self):
        """Test that search indexes are properly initialized."""
        service = CampaignMemoryService()

        assert hasattr(service._storage, "event_index")
        assert hasattr(service._storage, "fact_index")
        assert "participants" in service._storage.event_index
        assert "event_type" in service._storage.event_index
        assert "subject" in service._storage.fact_index
        assert "fact_type" in service._storage.fact_index


class TestMemoryEventCRUD:
    """Test memory event CRUD operations."""

    def test_create_memory_event_from_request_success(self):
        """Test successful creation of memory event from request."""
        service = CampaignMemoryService()

        request = CreateMemoryEventRequest(
            event_type="narrative",
            description="The party enters the dark cave",
            participants=["Eldrin", "Lyra"],
            location="Dark Cave Entrance",
        )

        result = service.create_memory_event_from_request(request)

        assert result.success is True
        assert result.memory_id is not None
        assert result.memory_type == "event"
        assert result.error is None

        # Verify event was stored
        event = service.get_memory_event(result.memory_id)
        assert event is not None
        assert event.event_type == "narrative"
        assert event.description == "The party enters the dark cave"
        assert len(event.participants) == 2

    def test_create_memory_event_validation_failure(self):
        """Test memory event creation with validation failure."""
        service = CampaignMemoryService()

        request = CreateMemoryEventRequest(
            event_type="narrative",
            description="",  # Empty description - validation failure
            participants=["Test"],
        )

        result = service.create_memory_event_from_request(request)

        assert result.success is False
        assert result.memory_id == ""
        assert result.memory_type == "event"
        assert "validation failed" in result.error.lower()

    def test_get_memory_event_exists(self):
        """Test getting an existing memory event."""
        service = CampaignMemoryService()

        # Create an event first
        event = MemoryEvent(
            event_id="test_event",
            timestamp=datetime.utcnow(),
            event_type="combat",
            description="Test event",
            participants=["Hero"],
        )
        service._storage.events["test_event"] = event

        retrieved = service.get_memory_event("test_event")

        assert retrieved is not None
        assert retrieved.event_id == "test_event"
        assert retrieved.event_type == "combat"

    def test_get_memory_event_not_exists(self):
        """Test getting a non-existent memory event."""
        service = CampaignMemoryService()

        retrieved = service.get_memory_event("nonexistent")

        assert retrieved is None

    def test_get_memory_events_with_filter(self):
        """Test getting memory events with filtering."""
        service = CampaignMemoryService()

        # Create test events
        events = [
            MemoryEvent(
                event_id="event_1",
                timestamp=datetime.utcnow(),
                event_type="combat",
                description="Battle event",
                participants=["Hero"],
            ),
            MemoryEvent(
                event_id="event_2",
                timestamp=datetime.utcnow(),
                event_type="narrative",
                description="Story event",
                participants=["Hero"],
            ),
        ]

        for event in events:
            service._storage.events[event.event_id] = event

        # Test filtering by event type
        combat_events = service.get_memory_events(event_type="combat")
        narrative_events = service.get_memory_events(event_type="narrative")

        assert len(combat_events) == 1
        assert len(narrative_events) == 1
        assert combat_events[0].event_type == "combat"
        assert narrative_events[0].event_type == "narrative"

    def test_get_memory_events_with_participant_filter(self):
        """Test getting memory events with participant filtering."""
        service = CampaignMemoryService()

        event = MemoryEvent(
            event_id="event_1",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test event",
            participants=["Eldrin", "Lyra"],
        )
        service._storage.events["event_1"] = event

        # Test filtering by participant
        eldrin_events = service.get_memory_events(participant="Eldrin")
        lyra_events = service.get_memory_events(participant="Lyra")
        thor_events = service.get_memory_events(participant="Throg")  # Not in event

        assert len(eldrin_events) == 1
        assert len(lyra_events) == 1
        assert len(thor_events) == 0

    def test_update_memory_event_success(self):
        """Test successful memory event update."""
        service = CampaignMemoryService()

        # Create initial event
        original_event = MemoryEvent(
            event_id="test_event",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Original description",
            participants=["Hero"],
            version=1,
        )
        service._storage.events["test_event"] = original_event

        # Update request
        update_request = UpdateMemoryEventRequest(
            event_id="test_event",
            description="Updated description",
            participants=["Hero", "Sidekick"],
        )

        result = service.update_memory_event("test_event", update_request)

        assert result.success is True
        assert result.memory_id == "test_event"
        assert result.memory_type == "event"

        # Verify update
        updated_event = service.get_memory_event("test_event")
        assert updated_event.description == "Updated description"
        assert len(updated_event.participants) == 2
        assert updated_event.version == 2

    def test_update_memory_event_not_found(self):
        """Test updating a non-existent memory event."""
        service = CampaignMemoryService()

        update_request = UpdateMemoryEventRequest(
            event_id="nonexistent", description="Updated description"
        )

        result = service.update_memory_event("nonexistent", update_request)

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_delete_memory_event_success(self):
        """Test successful memory event deletion."""
        service = CampaignMemoryService()

        # Create event
        event = MemoryEvent(
            event_id="test_event",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test event",
            participants=["Hero"],
        )
        service._storage.events["test_event"] = event

        # Delete event
        result = service.delete_memory_event("test_event")

        assert result.success is True
        assert result.memory_id == "test_event"
        assert result.memory_type == "event"

        # Verify deletion
        assert service.get_memory_event("test_event") is None

    def test_delete_memory_event_not_found(self):
        """Test deleting a non-existent memory event."""
        service = CampaignMemoryService()

        result = service.delete_memory_event("nonexistent")

        assert result.success is False
        assert "not found" in result.error.lower()


class TestMemoryFactCRUD:
    """Test memory fact CRUD operations."""

    def test_create_memory_fact_from_request_success(self):
        """Test successful creation of memory fact from request."""
        service = CampaignMemoryService()

        request = CreateMemoryFactRequest(
            fact_type="npc",
            subject="Mysterious Merchant",
            description="A merchant with valuable information",
            confidence=0.85,
            source="conversation",
            tags=["merchant", "informant"],
        )

        result = service.create_memory_fact_from_request(request)

        assert result.success is True
        assert result.memory_id is not None
        assert result.memory_type == "fact"
        assert result.error is None

        # Verify fact was stored
        fact = service.get_memory_fact(result.memory_id)
        assert fact is not None
        assert fact.fact_type == "npc"
        assert fact.subject == "Mysterious Merchant"
        assert fact.confidence == 0.85
        assert len(fact.tags) == 2

    def test_create_memory_fact_validation_failure(self):
        """Test memory fact creation with validation failure."""
        service = CampaignMemoryService()

        request = CreateMemoryFactRequest(
            fact_type="npc",
            subject="",  # Empty subject - validation failure
            description="Test description",
            confidence=0.5,
            source="test",
        )

        result = service.create_memory_fact_from_request(request)

        assert result.success is False
        assert result.memory_id == ""
        assert result.memory_type == "fact"
        assert "validation failed" in result.error.lower()

    def test_get_memory_fact_exists(self):
        """Test getting an existing memory fact."""
        service = CampaignMemoryService()

        # Create a fact first
        fact = MemoryFact(
            fact_id="test_fact",
            fact_type="location",
            subject="Ancient Temple",
            description="Test fact",
            confidence=0.8,
            source="discovery",
        )
        service._storage.facts["test_fact"] = fact

        retrieved = service.get_memory_fact("test_fact")

        assert retrieved is not None
        assert retrieved.fact_id == "test_fact"
        assert retrieved.fact_type == "location"

    def test_get_memory_fact_not_exists(self):
        """Test getting a non-existent memory fact."""
        service = CampaignMemoryService()

        retrieved = service.get_memory_fact("nonexistent")

        assert retrieved is None

    def test_get_memory_facts_with_filter(self):
        """Test getting memory facts with filtering."""
        service = CampaignMemoryService()

        # Create test facts
        facts = [
            MemoryFact(
                fact_id="fact_1",
                fact_type="npc",
                subject="Merchant",
                description="NPC fact",
                confidence=0.8,
                source="test",
                tags=["merchant"],
            ),
            MemoryFact(
                fact_id="fact_2",
                fact_type="location",
                subject="Temple",
                description="Location fact",
                confidence=0.7,
                source="test",
                tags=["temple"],
            ),
        ]

        for fact in facts:
            service._storage.facts[fact.fact_id] = fact

        # Test filtering by fact type
        npc_facts = service.get_memory_facts(fact_type="npc")
        location_facts = service.get_memory_facts(fact_type="location")

        assert len(npc_facts) == 1
        assert len(location_facts) == 1
        assert npc_facts[0].fact_type == "npc"
        assert location_facts[0].fact_type == "location"

    def test_get_memory_facts_with_confidence_filter(self):
        """Test getting memory facts with confidence filtering."""
        service = CampaignMemoryService()

        # Create facts with different confidence levels
        facts = [
            MemoryFact(
                fact_id="fact_1",
                fact_type="npc",
                subject="High Confidence NPC",
                description="Test fact",
                confidence=0.9,
                source="reliable",
            ),
            MemoryFact(
                fact_id="fact_2",
                fact_type="npc",
                subject="Low Confidence NPC",
                description="Test fact",
                confidence=0.3,
                source="rumor",
            ),
        ]

        for fact in facts:
            service._storage.facts[fact.fact_id] = fact

        # Test filtering by minimum confidence
        high_confidence_facts = service.get_memory_facts(min_confidence=0.8)
        all_facts = service.get_memory_facts(min_confidence=0.0)

        assert len(high_confidence_facts) == 1
        assert len(all_facts) == 2
        assert high_confidence_facts[0].confidence >= 0.8

    def test_update_memory_fact_success(self):
        """Test successful memory fact update."""
        service = CampaignMemoryService()

        # Create initial fact
        original_fact = MemoryFact(
            fact_id="test_fact",
            fact_type="npc",
            subject="Original Subject",
            description="Original description",
            confidence=0.6,
            source="original",
            tags=["original"],
            related_events=["event_1"],
        )
        service._storage.facts["test_fact"] = original_fact

        # Update request
        update_request = UpdateMemoryFactRequest(
            fact_id="test_fact",
            description="Updated description",
            confidence=0.9,
            tags=["updated", "important"],
        )

        result = service.update_memory_fact("test_fact", update_request)

        assert result.success is True
        assert result.memory_id == "test_fact"
        assert result.memory_type == "fact"

        # Verify update
        updated_fact = service.get_memory_fact("test_fact")
        assert updated_fact.description == "Updated description"
        assert updated_fact.confidence == 0.9
        assert set(updated_fact.tags) == {"updated", "important"}
        assert updated_fact.related_events == ["event_1"]  # Unchanged

    def test_update_memory_fact_not_found(self):
        """Test updating a non-existent memory fact."""
        service = CampaignMemoryService()

        update_request = UpdateMemoryFactRequest(
            fact_id="nonexistent", description="Updated description"
        )

        result = service.update_memory_fact("nonexistent", update_request)

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_delete_memory_fact_success(self):
        """Test successful memory fact deletion."""
        service = CampaignMemoryService()

        # Create fact
        fact = MemoryFact(
            fact_id="test_fact",
            fact_type="npc",
            subject="Test Subject",
            description="Test fact",
            confidence=0.8,
            source="test",
        )
        service._storage.facts["test_fact"] = fact

        # Delete fact
        result = service.delete_memory_fact("test_fact")

        assert result.success is True
        assert result.memory_id == "test_fact"
        assert result.memory_type == "fact"

        # Verify deletion
        assert service.get_memory_fact("test_fact") is None

    def test_delete_memory_fact_not_found(self):
        """Test deleting a non-existent memory fact."""
        service = CampaignMemoryService()

        result = service.delete_memory_fact("nonexistent")

        assert result.success is False
        assert "not found" in result.error.lower()


class TestMemoryQuerying:
    """Test memory querying and context generation."""

    def test_query_memory_events_success(self):
        """Test successful memory event querying."""
        service = CampaignMemoryService()

        # Create test events
        events = [
            MemoryEvent(
                event_id="event_1",
                timestamp=datetime.utcnow(),
                event_type="combat",
                description="Battle event",
                participants=["Hero"],
            ),
            MemoryEvent(
                event_id="event_2",
                timestamp=datetime.utcnow(),
                event_type="narrative",
                description="Story event",
                participants=["Hero"],
            ),
        ]

        for event in events:
            service._storage.events[event.event_id] = event

        # Query events
        request = MemoryQueryRequest(
            query_type="events", filters={"event_type": "combat"}
        )

        result = service.query_memory(request)

        assert result["success"] is True
        assert result["query_type"] == "events"
        assert len(result["data"]) == 1
        assert result["data"][0].event_type == "combat"

    def test_query_memory_facts_success(self):
        """Test successful memory fact querying."""
        service = CampaignMemoryService()

        # Create test facts
        facts = [
            MemoryFact(
                fact_id="fact_1",
                fact_type="npc",
                subject="Merchant",
                description="NPC fact",
                confidence=0.8,
                source="test",
            ),
            MemoryFact(
                fact_id="fact_2",
                fact_type="location",
                subject="Temple",
                description="Location fact",
                confidence=0.9,
                source="test",
            ),
        ]

        for fact in facts:
            service._storage.facts[fact.fact_id] = fact

        # Query facts
        request = MemoryQueryRequest(query_type="facts", filters={"fact_type": "npc"})

        result = service.query_memory(request)

        assert result["success"] is True
        assert result["query_type"] == "facts"
        assert len(result["data"]) == 1
        assert result["data"][0].fact_type == "npc"

    def test_query_memory_context_generation(self):
        """Test memory context generation through query."""
        service = CampaignMemoryService()

        # Create some test data
        event = MemoryEvent(
            event_id="event_1",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test event",
            participants=["Test"],
        )
        service._storage.events["event_1"] = event

        fact = MemoryFact(
            fact_id="fact_1",
            fact_type="npc",
            subject="Test NPC",
            description="Test fact",
            confidence=0.8,
            source="test",
        )
        service._storage.facts["fact_1"] = fact

        # Query context
        request = MemoryQueryRequest(query_type="context")

        result = service.query_memory(request)

        assert result["success"] is True
        assert result["query_type"] == "context"
        assert isinstance(result["data"], MemoryContext)

    def test_query_memory_invalid_type(self):
        """Test querying with invalid type."""
        service = CampaignMemoryService()

        request = MemoryQueryRequest(query_type="invalid_type")

        result = service.query_memory(request)

        assert result["success"] is False
        assert "unsupported query type" in result["error"].lower()


class TestAIContextGeneration:
    """Test AI context generation functionality."""

    def test_generate_ai_context_empty(self):
        """Test AI context generation with no data."""
        service = CampaignMemoryService()

        context = service.generate_ai_context()

        assert isinstance(context, MemoryContext)
        assert len(context.recent_events) == 0
        assert len(context.relevant_facts) == 0
        assert len(context.character_knowledge) == 0
        assert context.context_size == 0

    def test_generate_ai_context_with_data(self):
        """Test AI context generation with memory data."""
        service = CampaignMemoryService()

        # Create recent events
        recent_time = datetime.utcnow() - timedelta(hours=1)
        old_time = datetime.utcnow() - timedelta(hours=25)

        events = [
            MemoryEvent(
                event_id="recent_event",
                timestamp=recent_time,
                event_type="narrative",
                description="Recent event description",
                participants=["Hero"],
            ),
            MemoryEvent(
                event_id="old_event",
                timestamp=old_time,
                event_type="narrative",
                description="Old event description",
                participants=["Hero"],
            ),
        ]

        # Create facts with different confidence levels
        facts = [
            MemoryFact(
                fact_id="high_confidence_fact",
                fact_type="npc",
                subject="Important NPC",
                description="High confidence fact description",
                confidence=0.9,
                source="reliable",
            ),
            MemoryFact(
                fact_id="low_confidence_fact",
                fact_type="location",
                subject="Unimportant Location",
                description="Low confidence fact description",
                confidence=0.3,
                source="rumor",
            ),
        ]

        for event in events:
            service._storage.events[event.event_id] = event
        for fact in facts:
            service._storage.facts[fact.fact_id] = fact

        context = service.generate_ai_context()

        assert isinstance(context, MemoryContext)
        assert len(context.recent_events) == 1  # Only recent event
        assert len(context.relevant_facts) == 1  # Only high confidence fact
        assert context.recent_events[0].event_id == "recent_event"
        assert context.relevant_facts[0].fact_id == "high_confidence_fact"
        assert "Recent event description" in context.recent_events[0].description
        assert "High confidence fact" in context.relevant_facts[0].description
        assert context.context_size > 0

    def test_generate_ai_context_custom_limits(self):
        """Test AI context generation with custom limits."""
        service = CampaignMemoryService()

        # Create multiple events and facts
        for i in range(5):
            event = MemoryEvent(
                event_id=f"event_{i}",
                timestamp=datetime.utcnow() - timedelta(hours=i),
                event_type="narrative",
                description=f"Event {i} description",
                participants=["Hero"],
            )
            service._storage.events[event.event_id] = event

            fact = MemoryFact(
                fact_id=f"fact_{i}",
                fact_type="npc",
                subject=f"NPC {i}",
                description=f"Fact {i} description",
                confidence=0.8,
                source="test",
            )
            service._storage.facts[fact.fact_id] = fact

        # Test with custom limits
        context = service.generate_ai_context(max_events=3, max_facts=2)

        assert len(context.recent_events) <= 3
        assert len(context.relevant_facts) <= 2


class TestServiceManagement:
    """Test service management functionality."""

    def test_get_memory_stats(self):
        """Test getting memory service statistics."""
        service = CampaignMemoryService(campaign_id="test_campaign")

        # Add some test data
        event = MemoryEvent(
            event_id="test_event",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test event",
            participants=["Test"],
        )
        service._storage.events["test_event"] = event

        fact = MemoryFact(
            fact_id="test_fact",
            fact_type="npc",
            subject="Test NPC",
            description="Test fact",
            confidence=0.8,
            source="test",
        )
        service._storage.facts["test_fact"] = fact

        stats = service.get_memory_stats()

        assert stats["campaign_id"] == "test_campaign"
        assert stats["total_events"] == 1
        assert stats["total_facts"] == 1
        assert len(stats["event_types"]) == 1
        assert len(stats["fact_types"]) == 1
        assert stats["event_types"] == ["narrative"]
        assert stats["fact_types"] == ["npc"]

    def test_clear_memory(self):
        """Test clearing all memory data."""
        service = CampaignMemoryService()

        # Add some test data
        event = MemoryEvent(
            event_id="test_event",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test event",
            participants=["Test"],
        )
        service._storage.events["test_event"] = event

        fact = MemoryFact(
            fact_id="test_fact",
            fact_type="npc",
            subject="Test NPC",
            description="Test fact",
            confidence=0.8,
            source="test",
        )
        service._storage.facts["test_fact"] = fact

        # Verify data exists
        assert len(service._storage.events) == 1
        assert len(service._storage.facts) == 1

        # Clear memory
        result = service.clear_memory()

        assert result is True
        assert len(service._storage.events) == 0
        assert len(service._storage.facts) == 0


class TestErrorHandling:
    """Test error handling in memory operations."""

    def test_create_event_with_exception(self):
        """Test error handling during event creation."""
        service = CampaignMemoryService()

        # Mock validation to raise exception
        with patch.object(service, "_validate_memory_event") as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            request = CreateMemoryEventRequest(
                event_type="narrative",
                description="Test description",
                participants=["Test"],
            )

            result = service.create_memory_event_from_request(request)

            assert result.success is False
            assert "internal error" in result.error.lower()

    def test_create_fact_with_exception(self):
        """Test error handling during fact creation."""
        service = CampaignMemoryService()

        # Mock validation to raise exception
        with patch.object(service, "_validate_memory_fact") as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            request = CreateMemoryFactRequest(
                fact_type="npc",
                subject="Test Subject",
                description="Test description",
                confidence=0.5,
                source="test",
            )

            result = service.create_memory_fact_from_request(request)

            assert result.success is False
            assert "internal error" in result.error.lower()

    def test_query_memory_with_exception(self):
        """Test error handling during memory query."""
        service = CampaignMemoryService()

        # Mock get_memory_events to raise exception
        with patch.object(service, "get_memory_events") as mock_get:
            mock_get.side_effect = Exception("Query error")

            request = MemoryQueryRequest(query_type="events")

            result = service.query_memory(request)

            assert result["success"] is False
            assert "failed" in result["error"].lower()


class TestMemoryServiceIntegration:
    """Test integration between different memory service components."""

    def test_full_crud_workflow_events(self):
        """Test complete CRUD workflow for memory events."""
        service = CampaignMemoryService()

        # Create event
        create_request = CreateMemoryEventRequest(
            event_type="narrative",
            description="Initial event description",
            participants=["Hero"],
            location="Starting Area",
        )

        create_result = service.create_memory_event_from_request(create_request)
        assert create_result.success is True
        event_id = create_result.memory_id

        # Read event
        event = service.get_memory_event(event_id)
        assert event is not None
        assert event.description == "Initial event description"

        # Update event
        update_request = UpdateMemoryEventRequest(
            event_id=event_id,
            description="Updated event description",
            participants=["Hero", "Sidekick"],
        )

        update_result = service.update_memory_event(event_id, update_request)
        assert update_result.success is True

        # Verify update
        updated_event = service.get_memory_event(event_id)
        assert updated_event.description == "Updated event description"
        assert len(updated_event.participants) == 2

        # Delete event
        delete_result = service.delete_memory_event(event_id)
        assert delete_result.success is True

        # Verify deletion
        deleted_event = service.get_memory_event(event_id)
        assert deleted_event is None

    def test_full_crud_workflow_facts(self):
        """Test complete CRUD workflow for memory facts."""
        service = CampaignMemoryService()

        # Create fact
        create_request = CreateMemoryFactRequest(
            fact_type="npc",
            subject="Tavern Owner",
            description="Initial fact description",
            confidence=0.7,
            source="observation",
            tags=["tavern", "npc"],
        )

        create_result = service.create_memory_fact_from_request(create_request)
        assert create_result.success is True
        fact_id = create_result.memory_id

        # Read fact
        fact = service.get_memory_fact(fact_id)
        assert fact is not None
        assert fact.description == "Initial fact description"

        # Update fact
        update_request = UpdateMemoryFactRequest(
            fact_id=fact_id,
            description="Updated fact description",
            confidence=0.9,
            tags=["tavern", "npc", "important"],
        )

        update_result = service.update_memory_fact(fact_id, update_request)
        assert update_result.success is True

        # Verify update
        updated_fact = service.get_memory_fact(fact_id)
        assert updated_fact.description == "Updated fact description"
        assert updated_fact.confidence == 0.9
        assert len(updated_fact.tags) == 3

        # Delete fact
        delete_result = service.delete_memory_fact(fact_id)
        assert delete_result.success is True

        # Verify deletion
        deleted_fact = service.get_memory_fact(fact_id)
        assert deleted_fact is None
