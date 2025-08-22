"""
Unit tests for memory data models.

Tests cover:
- MemoryEvent model validation and constraints
- MemoryFact model validation and constraints
- MemoryContext model validation
- MemoryOperation model validation
- CRUD request/response model validation
- Edge cases and error conditions
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from packages.shared.models import (
    MemoryEvent,
    MemoryFact,
    MemoryContext,
    MemoryOperation,
    CreateMemoryEventRequest,
    CreateMemoryFactRequest,
    UpdateMemoryEventRequest,
    UpdateMemoryFactRequest,
    MemoryQueryRequest
)


class TestMemoryEventModel:
    """Test MemoryEvent model validation and functionality."""

    def test_valid_memory_event_creation(self):
        """Test creating a valid memory event."""
        event_data = {
            "event_id": "event_123",
            "timestamp": datetime.utcnow(),
            "event_type": "narrative",
            "description": "The party encounters a mysterious stranger in the tavern",
            "participants": ["Eldrin", "Throg", "Lyra"],
            "location": "The Rusty Dragon Tavern",
            "metadata": {"weather": "stormy", "time_of_day": "evening"}
        }

        event = MemoryEvent(**event_data)

        assert event.event_id == "event_123"
        assert event.event_type == "narrative"
        assert len(event.participants) == 3
        assert event.location == "The Rusty Dragon Tavern"
        assert event.version == 1
        assert isinstance(event.created_at, datetime)
        assert isinstance(event.updated_at, datetime)

    def test_memory_event_with_minimal_fields(self):
        """Test memory event with only required fields."""
        event_data = {
            "event_id": "event_minimal",
            "timestamp": datetime.utcnow(),
            "event_type": "combat",
            "description": "A brief fight",
            "participants": ["Hero"]
        }

        event = MemoryEvent(**event_data)

        assert event.location is None
        assert event.metadata == {}
        assert event.version == 1

    @pytest.mark.parametrize("invalid_event_type", ["invalid", "story", "battle"])
    def test_invalid_event_type(self, invalid_event_type):
        """Test that invalid event types raise validation errors."""
        event_data = {
            "event_id": "event_invalid",
            "timestamp": datetime.utcnow(),
            "event_type": invalid_event_type,
            "description": "Test description",
            "participants": ["Test"]
        }

        with pytest.raises(ValidationError) as exc_info:
            MemoryEvent(**event_data)

        assert "event_type" in str(exc_info.value)

    def test_empty_participants_list(self):
        """Test that empty participants list raises validation error."""
        event_data = {
            "event_id": "event_empty_participants",
            "timestamp": datetime.utcnow(),
            "event_type": "narrative",
            "description": "Test description",
            "participants": []
        }

        with pytest.raises(ValidationError) as exc_info:
            MemoryEvent(**event_data)

        assert "participants" in str(exc_info.value)

    def test_description_too_long(self):
        """Test that descriptions over 1000 characters raise validation error."""
        long_description = "a" * 1001
        event_data = {
            "event_id": "event_long_desc",
            "timestamp": datetime.utcnow(),
            "event_type": "narrative",
            "description": long_description,
            "participants": ["Test"]
        }

        with pytest.raises(ValidationError) as exc_info:
            MemoryEvent(**event_data)

        assert "description" in str(exc_info.value)

    def test_invalid_event_id_format(self):
        """Test that invalid event ID formats raise validation error."""
        invalid_ids = ["event 123", "event@123", "event.123", ""]

        for invalid_id in invalid_ids:
            event_data = {
                "event_id": invalid_id,
                "timestamp": datetime.utcnow(),
                "event_type": "narrative",
                "description": "Test description",
                "participants": ["Test"]
            }

            with pytest.raises(ValidationError):
                MemoryEvent(**event_data)

    def test_event_version_increment(self):
        """Test that event versions start at 1 and can be incremented."""
        event_data = {
            "event_id": "event_version_test",
            "timestamp": datetime.utcnow(),
            "event_type": "narrative",
            "description": "Test description",
            "participants": ["Test"],
            "version": 5
        }

        event = MemoryEvent(**event_data)
        assert event.version == 5

    def test_event_with_future_timestamp(self):
        """Test event creation with future timestamp (should succeed but may have warnings in validation)."""
        future_time = datetime.utcnow() + timedelta(days=1)
        event_data = {
            "event_id": "event_future",
            "timestamp": future_time,
            "event_type": "narrative",
            "description": "Future event",
            "participants": ["Test"]
        }

        event = MemoryEvent(**event_data)
        assert event.timestamp == future_time


class TestMemoryFactModel:
    """Test MemoryFact model validation and functionality."""

    def test_valid_memory_fact_creation(self):
        """Test creating a valid memory fact."""
        fact_data = {
            "fact_id": "fact_123",
            "fact_type": "npc",
            "subject": "Eldrin the Brave",
            "description": "A seasoned warrior with a mysterious past",
            "confidence": 0.85,
            "source": "player_description",
            "tags": ["warrior", "mysterious", "seasoned"],
            "related_events": ["event_001", "event_002"]
        }

        fact = MemoryFact(**fact_data)

        assert fact.fact_id == "fact_123"
        assert fact.fact_type == "npc"
        assert fact.confidence == 0.85
        assert len(fact.tags) == 3
        assert len(fact.related_events) == 2
        assert isinstance(fact.last_updated, datetime)

    def test_memory_fact_with_minimal_fields(self):
        """Test memory fact with only required fields."""
        fact_data = {
            "fact_id": "fact_minimal",
            "fact_type": "location",
            "subject": "Ancient Ruins",
            "description": "Ruins of an ancient civilization",
            "confidence": 0.7,
            "source": "discovered"
        }

        fact = MemoryFact(**fact_data)

        assert fact.tags == []
        assert fact.related_events == []

    @pytest.mark.parametrize("invalid_fact_type", ["invalid", "character", "place"])
    def test_invalid_fact_type(self, invalid_fact_type):
        """Test that invalid fact types raise validation errors."""
        fact_data = {
            "fact_id": "fact_invalid",
            "fact_type": invalid_fact_type,
            "subject": "Test Subject",
            "description": "Test description",
            "confidence": 0.5,
            "source": "test"
        }

        with pytest.raises(ValidationError) as exc_info:
            MemoryFact(**fact_data)

        assert "fact_type" in str(exc_info.value)

    def test_confidence_out_of_range(self):
        """Test that confidence values outside 0.0-1.0 raise validation errors."""
        invalid_confidences = [-0.1, 1.1, 2.0]

        for invalid_confidence in invalid_confidences:
            fact_data = {
                "fact_id": "fact_invalid_confidence",
                "fact_type": "npc",
                "subject": "Test Subject",
                "description": "Test description",
                "confidence": invalid_confidence,
                "source": "test"
            }

            with pytest.raises(ValidationError) as exc_info:
                MemoryFact(**fact_data)

            assert "confidence" in str(exc_info.value)

    def test_too_many_tags(self):
        """Test that too many tags raise validation error."""
        fact_data = {
            "fact_id": "fact_too_many_tags",
            "fact_type": "npc",
            "subject": "Test Subject",
            "description": "Test description",
            "confidence": 0.5,
            "source": "test",
            "tags": [f"tag_{i}" for i in range(12)]  # 12 tags, exceeds limit of 10
        }

        with pytest.raises(ValidationError) as exc_info:
            MemoryFact(**fact_data)

        assert "tags" in str(exc_info.value)

    def test_too_many_related_events(self):
        """Test that too many related events raise validation error."""
        fact_data = {
            "fact_id": "fact_too_many_events",
            "fact_type": "quest",
            "subject": "Test Quest",
            "description": "Test quest description",
            "confidence": 0.5,
            "source": "test",
            "related_events": [f"event_{i}" for i in range(52)]  # 52 events, exceeds limit of 50
        }

        with pytest.raises(ValidationError) as exc_info:
            MemoryFact(**fact_data)

        assert "related_events" in str(exc_info.value)

    def test_invalid_fact_id_format(self):
        """Test that invalid fact ID formats raise validation error."""
        invalid_ids = ["fact 123", "fact@123", "fact.123", ""]

        for invalid_id in invalid_ids:
            fact_data = {
                "fact_id": invalid_id,
                "fact_type": "npc",
                "subject": "Test Subject",
                "description": "Test description",
                "confidence": 0.5,
                "source": "test"
            }

            with pytest.raises(ValidationError):
                MemoryFact(**fact_data)


class TestMemoryContextModel:
    """Test MemoryContext model validation and functionality."""

    def test_valid_memory_context_creation(self):
        """Test creating a valid memory context."""
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test event",
            participants=["Test"]
        )

        fact = MemoryFact(
            fact_id="fact_123",
            fact_type="npc",
            subject="Test NPC",
            description="Test NPC description",
            confidence=0.8,
            source="test"
        )

        context_data = {
            "recent_events": [event],
            "relevant_facts": [fact],
            "character_knowledge": {
                "Eldrin": ["knows about ancient ruins", "skilled fighter"],
                "Lyra": ["magic user", "healer"]
            },
            "world_state": {
                "current_location": "Forest",
                "time_of_day": "morning",
                "weather": "sunny"
            },
            "summary": "Current campaign context summary",
            "context_size": 1500
        }

        context = MemoryContext(**context_data)

        assert len(context.recent_events) == 1
        assert len(context.relevant_facts) == 1
        assert len(context.character_knowledge) == 2
        assert context.context_size == 1500
        assert "Current campaign context" in context.summary

    def test_memory_context_with_empty_fields(self):
        """Test memory context with minimal required fields."""
        context_data = {
            "recent_events": [],
            "relevant_facts": [],
            "character_knowledge": {},
            "world_state": {},
            "summary": "Empty context",
            "context_size": 0
        }

        context = MemoryContext(**context_data)

        assert len(context.recent_events) == 0
        assert len(context.relevant_facts) == 0
        assert len(context.character_knowledge) == 0
        assert len(context.world_state) == 0
        assert context.summary == "Empty context"
        assert context.context_size == 0

    def test_memory_context_empty_summary(self):
        """Test that empty summary raises validation error."""
        context_data = {
            "recent_events": [],
            "relevant_facts": [],
            "character_knowledge": {},
            "world_state": {},
            "summary": "",
            "context_size": 100
        }

        with pytest.raises(ValidationError) as exc_info:
            MemoryContext(**context_data)

        assert "summary" in str(exc_info.value)

    def test_memory_context_negative_size(self):
        """Test that negative context size raises validation error."""
        context_data = {
            "recent_events": [],
            "relevant_facts": [],
            "character_knowledge": {},
            "world_state": {},
            "summary": "Test summary",
            "context_size": -1
        }

        with pytest.raises(ValidationError) as exc_info:
            MemoryContext(**context_data)

        assert "context_size" in str(exc_info.value)


class TestMemoryOperationModel:
    """Test MemoryOperation model validation and functionality."""

    def test_valid_memory_operation_creation(self):
        """Test creating a valid memory operation."""
        operation_data = {
            "operation": "create",
            "success": True,
            "memory_id": "event_123",
            "memory_type": "event"
        }

        operation = MemoryOperation(**operation_data)

        assert operation.operation == "create"
        assert operation.success is True
        assert operation.memory_id == "event_123"
        assert operation.memory_type == "event"
        assert operation.error is None
        assert isinstance(operation.timestamp, datetime)

    def test_memory_operation_with_error(self):
        """Test memory operation with error information."""
        operation_data = {
            "operation": "update",
            "success": False,
            "memory_id": "fact_456",
            "memory_type": "fact",
            "error": "Validation failed: invalid confidence value"
        }

        operation = MemoryOperation(**operation_data)

        assert operation.operation == "update"
        assert operation.success is False
        assert operation.error == "Validation failed: invalid confidence value"

    @pytest.mark.parametrize("invalid_operation", ["invalid", "read", "write"])
    def test_invalid_operation_type(self, invalid_operation):
        """Test that invalid operation types raise validation errors."""
        operation_data = {
            "operation": invalid_operation,
            "success": True,
            "memory_id": "test_123",
            "memory_type": "event"
        }

        with pytest.raises(ValidationError) as exc_info:
            MemoryOperation(**operation_data)

        assert "operation" in str(exc_info.value)


class TestCRUDRequestModels:
    """Test CRUD request model validation."""

    def test_valid_create_event_request(self):
        """Test creating a valid create event request."""
        request_data = {
            "event_type": "combat",
            "description": "Epic battle in the arena",
            "participants": ["Hero", "Villain"],
            "location": "Grand Arena",
            "metadata": {"difficulty": "hard", "rounds": 5}
        }

        request = CreateMemoryEventRequest(**request_data)

        assert request.event_type == "combat"
        assert len(request.participants) == 2
        assert request.location == "Grand Arena"

    def test_create_event_request_minimal(self):
        """Test create event request with minimal fields."""
        request_data = {
            "event_type": "narrative",
            "description": "Simple story event",
            "participants": ["Narrator"]
        }

        request = CreateMemoryEventRequest(**request_data)

        assert request.location is None
        assert request.metadata is None

    def test_invalid_create_event_request(self):
        """Test create event request with validation errors."""
        # Empty description
        request_data = {
            "event_type": "narrative",
            "description": "",
            "participants": ["Test"]
        }

        with pytest.raises(ValidationError):
            CreateMemoryEventRequest(**request_data)

    def test_valid_create_fact_request(self):
        """Test creating a valid create fact request."""
        request_data = {
            "fact_type": "npc",
            "subject": "Mysterious Merchant",
            "description": "A merchant with a hidden agenda",
            "confidence": 0.75,
            "source": "rumor",
            "tags": ["merchant", "mysterious", "suspicious"],
            "related_events": ["event_001"]
        }

        request = CreateMemoryFactRequest(**request_data)

        assert request.fact_type == "npc"
        assert request.confidence == 0.75
        assert len(request.tags) == 3

    def test_create_fact_request_minimal(self):
        """Test create fact request with minimal fields."""
        request_data = {
            "fact_type": "location",
            "subject": "Dark Forest",
            "description": "A foreboding forest",
            "confidence": 0.6,
            "source": "common_knowledge"
        }

        request = CreateMemoryFactRequest(**request_data)

        assert request.tags is None
        assert request.related_events is None

    def test_valid_update_event_request(self):
        """Test creating a valid update event request."""
        request_data = {
            "event_id": "event_123",
            "description": "Updated event description",
            "participants": ["NewHero", "OldHero"],
            "location": "Updated Location"
        }

        request = UpdateMemoryEventRequest(**request_data)

        assert request.event_id == "event_123"
        assert "Updated event description" in request.description
        assert len(request.participants) == 2

    def test_valid_query_request(self):
        """Test creating a valid memory query request."""
        request_data = {
            "query_type": "events",
            "filters": {
                "event_type": "combat",
                "participant": "Hero"
            },
            "limit": 50
        }

        request = MemoryQueryRequest(**request_data)

        assert request.query_type == "events"
        assert request.filters["event_type"] == "combat"
        assert request.limit == 50

    def test_query_request_defaults(self):
        """Test query request with default values."""
        request_data = {
            "query_type": "facts"
        }

        request = MemoryQueryRequest(**request_data)

        assert request.filters is None
        assert request.limit == 100
        assert request.include_metadata is True


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_memory_event_serialization(self):
        """Test MemoryEvent model serialization to dict."""
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test event",
            participants=["Test"]
        )

        event_dict = event.model_dump()

        assert event_dict["event_id"] == "event_123"
        assert event_dict["event_type"] == "narrative"
        assert isinstance(event_dict["timestamp"], str)  # datetime serialized to ISO string
        assert isinstance(event_dict["created_at"], str)

    def test_memory_fact_serialization(self):
        """Test MemoryFact model serialization to dict."""
        fact = MemoryFact(
            fact_id="fact_123",
            fact_type="npc",
            subject="Test NPC",
            description="Test description",
            confidence=0.8,
            source="test"
        )

        fact_dict = fact.model_dump()

        assert fact_dict["fact_id"] == "fact_123"
        assert fact_dict["confidence"] == 0.8
        assert isinstance(fact_dict["last_updated"], str)

    def test_memory_event_json_serialization(self):
        """Test MemoryEvent JSON serialization."""
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test event",
            participants=["Test"]
        )

        json_str = event.model_dump_json()
        assert isinstance(json_str, str)
        assert "event_123" in json_str
        assert "narrative" in json_str

    def test_model_copy_functionality(self):
        """Test Pydantic model copy functionality."""
        original_event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Original event",
            participants=["Test"],
            version=1
        )

        # Test shallow copy
        copied_event = original_event.model_copy()
        assert copied_event.event_id == original_event.event_id
        assert copied_event.description == original_event.description
        assert copied_event is not original_event  # Different object

        # Test copy with updates
        updated_event = original_event.model_copy(update={"description": "Updated event", "version": 2})
        assert updated_event.description == "Updated event"
        assert updated_event.version == 2
        assert updated_event.event_id == original_event.event_id  # Unchanged fields remain the same