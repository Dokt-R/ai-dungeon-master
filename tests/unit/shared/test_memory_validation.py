"""
Unit tests for memory validation module.

Tests cover:
- Memory validator initialization and configuration
- Event validation business rules
- Fact validation business rules
- Request validation for CRUD operations
- Edge cases and error conditions
- Validation result structure
"""

from datetime import datetime, timedelta

from packages.shared.memory_validation import (
    MemoryValidator,
    ValidationResult,
    memory_validator,
)
from packages.shared.models import (
    CreateMemoryEventRequest,
    CreateMemoryFactRequest,
    MemoryEvent,
    MemoryFact,
    MemoryQueryRequest,
)


class TestMemoryValidatorInitialization:
    """Test MemoryValidator initialization and configuration."""

    def test_validator_initialization(self):
        """Test that validator initializes with correct default values."""
        validator = MemoryValidator()

        assert validator._max_description_length == 1000
        assert validator._max_subject_length == 200
        assert validator._max_participants == 20
        assert validator._max_tags == 10
        assert validator._max_related_events == 50
        assert validator._min_confidence_threshold == 0.1

        assert "narrative" in validator._valid_event_types
        assert "combat" in validator._valid_event_types
        assert "npc" in validator._valid_fact_types
        assert "location" in validator._valid_fact_types

    def test_global_validator_instance(self):
        """Test that global memory_validator instance is available."""
        assert memory_validator is not None
        assert isinstance(memory_validator, MemoryValidator)


class TestMemoryEventValidation:
    """Test memory event validation logic."""

    def test_valid_event_validation(self):
        """Test validation of a valid memory event."""
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="The party discovers an ancient artifact",
            participants=["Eldrin", "Lyra", "Throg"],
        )

        result = memory_validator.validate_memory_event(event)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_invalid_event_type(self):
        """Test validation with invalid event type."""
        # This test expects Pydantic validation to fail, but since we're testing
        # the custom validation logic, we need to test the business rule validation
        # that should catch this case. The Pydantic validation happens at model creation.

        # Create a valid event first, then test the validation logic
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="narrative",  # Valid type for model creation
            description="Test description",
            participants=["Test"],
        )

        # Manually set invalid type to test validation logic
        event.event_type = "invalid_type"  # type: ignore

        result = memory_validator.validate_memory_event(event)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("invalid event type" in error.lower() for error in result.errors)

    def test_empty_participants(self):
        """Test validation with empty participants list."""
        # This test expects Pydantic validation to fail, but since we're testing
        # the custom validation logic, we need to test the business rule validation
        # that should catch this case. The Pydantic validation happens at model creation.

        # Create a valid event first, then test the validation logic
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test description",
            participants=["Test"],  # Valid for model creation
        )

        # Manually set empty participants to test validation logic
        event.participants = []  # type: ignore

        result = memory_validator.validate_memory_event(event)

        assert result.is_valid is False
        assert any(
            "at least one participant" in error.lower() for error in result.errors
        )

    def test_combat_event_with_single_participant(self):
        """Test business rule: combat events should have multiple participants."""
        # Create event with valid data first, then modify to test the business rule
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="combat",
            description="A solo fight against a powerful dragon that the hero must defeat and overcome with great difficulty",  # Make description longer
            participants=[
                "SoloHero"
            ],  # Start with invalid participants to trigger the rule
        )

        result = memory_validator.validate_memory_event(event)

        assert result.is_valid is False
        # Check if the combat participant rule is in any of the errors
        combat_rule_found = any(
            "Combat events should have at least 2 participants" in error
            for error in result.errors
        )
        if not combat_rule_found:
            print(f"DEBUG: Expected error not found. All errors: {result.errors}")
        assert combat_rule_found

    def test_exploration_event_without_location(self):
        """Test business rule: exploration events should have location."""
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="exploration",
            description="Exploring somewhere in search of hidden treasures and ancient artifacts",  # Make description longer
            participants=["Explorer"],
        )

        result = memory_validator.validate_memory_event(event)

        assert result.is_valid is False
        # Check if the exploration location rule is in any of the errors
        exploration_rule_found = any(
            "Exploration events should specify a location" in error
            for error in result.errors
        )
        if not exploration_rule_found:
            print(f"DEBUG: Expected error not found. All errors: {result.errors}")
        assert exploration_rule_found

    def test_event_description_too_short(self):
        """Test business rule: event descriptions should be descriptive."""
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Hi",  # Too short
            participants=["Test"],
        )

        result = memory_validator.validate_memory_event(event)

        assert result.is_valid is False
        assert any("should be more descriptive" in error for error in result.errors)

    def test_future_timestamp_warning(self):
        """Test warning for future timestamp."""
        future_time = datetime.utcnow() + timedelta(hours=2)
        event = MemoryEvent(
            event_id="event_123",
            timestamp=future_time,
            event_type="narrative",
            description="This is a future event that will happen in a couple of hours from now",  # Make description longer
            participants=["Test"],
        )

        result = memory_validator.validate_memory_event(event)

        assert result.is_valid is True  # Should still be valid
        assert len(result.warnings) > 0
        assert any("future" in warning.lower() for warning in result.warnings)

    def test_reserved_participant_names(self):
        """Test validation with reserved participant names."""
        event = MemoryEvent(
            event_id="event_123",
            timestamp=datetime.utcnow(),
            event_type="narrative",
            description="Test description",
            participants=["System", "Admin"],  # Reserved words
        )

        result = memory_validator.validate_memory_event(event)

        assert result.is_valid is False
        assert any("reserved" in error.lower() for error in result.errors)


class TestMemoryFactValidation:
    """Test memory fact validation logic."""

    def test_valid_fact_validation(self):
        """Test validation of a valid memory fact."""
        fact = MemoryFact(
            fact_id="fact_123",
            fact_type="npc",
            subject="Eldrin the Warrior",
            description="A skilled fighter with a mysterious past who has a relationship with the party",  # Include relationship keyword
            confidence=0.85,
            source="player_background",
        )

        result = memory_validator.validate_memory_fact(fact)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_fact_type(self):
        """Test validation with invalid fact type."""
        # This test expects Pydantic validation to fail, but since we're testing
        # the custom validation logic, we need to test the business rule validation
        # that should catch this case. The Pydantic validation happens at model creation.

        # Create a valid fact first, then test the validation logic
        fact = MemoryFact(
            fact_id="fact_123",
            fact_type="npc",  # Valid type for model creation
            subject="Test Subject",
            description="Test description",
            confidence=0.5,
            source="test",
        )

        # Manually set invalid type to test validation logic
        fact.fact_type = "invalid_type"  # type: ignore

        result = memory_validator.validate_memory_fact(fact)

        assert result.is_valid is False
        assert any("invalid fact type" in error.lower() for error in result.errors)

    def test_low_confidence_warning(self):
        """Test warning for low confidence facts."""
        fact = MemoryFact(
            fact_id="fact_123",
            fact_type="npc",
            subject="Unknown Person",
            description="Maybe this person exists and has a relationship with someone in the party",  # Include relationship keyword
            confidence=0.05,  # Below threshold
            source="rumor",
        )

        result = memory_validator.validate_memory_fact(fact)

        assert result.is_valid is True  # Should still be valid
        assert len(result.warnings) > 0
        assert any("confidence" in warning.lower() for warning in result.warnings)

    def test_npc_fact_without_relationship_info(self):
        """Test business rule: NPC facts should mention relationship."""
        fact = MemoryFact(
            fact_id="fact_123",
            fact_type="npc",
            subject="Random Merchant",
            description="Sells goods in the market",  # No relationship info
            confidence=0.7,
            source="observation",
        )

        result = memory_validator.validate_memory_fact(fact)

        assert result.is_valid is False
        assert any("relationship information" in error for error in result.errors)

    def test_quest_fact_without_objective_info(self):
        """Test business rule: quest facts should mention objectives."""
        fact = MemoryFact(
            fact_id="fact_123",
            fact_type="quest",
            subject="Mysterious Quest",
            description="Something mysterious happened",  # No objective info
            confidence=0.8,
            source="rumor",
        )

        result = memory_validator.validate_memory_fact(fact)

        assert result.is_valid is False
        assert any("objectives" in error.lower() for error in result.errors)

    def test_high_confidence_fact_without_source(self):
        """Test business rule: high confidence facts need source."""
        fact = MemoryFact(
            fact_id="fact_123",
            fact_type="location",
            subject="Ancient Temple",
            description="A temple with detailed historical records and ancient artifacts",  # Make sure description is long enough
            confidence=0.95,  # High confidence
            source="",  # Empty source
        )

        result = memory_validator.validate_memory_fact(fact)

        assert result.is_valid is False
        # Check if the high confidence source rule is in any of the errors
        high_confidence_rule_found = any(
            "High confidence facts must have a source" in error
            for error in result.errors
        )
        if not high_confidence_rule_found:
            print(f"DEBUG: Expected error not found. All errors: {result.errors}")
        assert high_confidence_rule_found


class TestCRUDRequestValidation:
    """Test validation of CRUD request models."""

    def test_valid_create_event_request(self):
        """Test validation of valid create event request."""
        request = CreateMemoryEventRequest(
            event_type="narrative",
            description="The party rests at the inn",
            participants=["Eldrin", "Lyra"],
        )

        result = memory_validator.validate_create_event_request(request)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_create_event_request_empty_description(self):
        """Test validation with empty description."""
        # This test expects Pydantic validation to fail, but since we're testing
        # the custom validation logic, we need to test the business rule validation
        # that should catch this case. The Pydantic validation happens at model creation.

        # Create a valid request first, then test the validation logic
        request = CreateMemoryEventRequest(
            event_type="narrative",
            description="Valid description",  # Valid for model creation
            participants=["Test"],
        )

        # Manually set empty description to test validation logic
        request.description = ""  # type: ignore

        result = memory_validator.validate_create_event_request(request)

        assert result.is_valid is False
        assert any("empty" in error.lower() for error in result.errors)

    def test_valid_create_fact_request(self):
        """Test validation of valid create fact request."""
        request = CreateMemoryFactRequest(
            fact_type="npc",
            subject="Tavern Owner",
            description="Friendly tavern owner who knows local gossip",
            confidence=0.75,
            source="conversation",
        )

        result = memory_validator.validate_create_fact_request(request)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_create_fact_request_low_confidence(self):
        """Test validation with confidence below minimum."""
        request = CreateMemoryFactRequest(
            fact_type="npc",
            subject="Test NPC",
            description="Test description",
            confidence=0.05,  # Below minimum
            source="test",
        )

        result = memory_validator.validate_create_fact_request(request)

        assert result.is_valid is True  # Should still be valid, but with warning
        assert len(result.warnings) > 0


class TestQueryRequestValidation:
    """Test validation of query request models."""

    def test_valid_query_request(self):
        """Test validation of valid query request."""
        request = MemoryQueryRequest(
            query_type="events", filters={"event_type": "combat"}, limit=50
        )

        result = memory_validator.validate_query_request(request)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_query_type(self):
        """Test validation with invalid query type."""
        # This test expects Pydantic validation to fail, but since we're testing
        # the custom validation logic, we need to test the business rule validation
        # that should catch this case. The Pydantic validation happens at model creation.

        # Create a valid request first, then test the validation logic
        request = MemoryQueryRequest(
            query_type="events"
        )  # Valid type for model creation

        # Manually set invalid type to test validation logic
        request.query_type = "invalid_type"  # type: ignore

        result = memory_validator.validate_query_request(request)

        assert result.is_valid is False
        assert any("query type" in error.lower() for error in result.errors)

    def test_invalid_limit_values(self):
        """Test validation with invalid limit values."""
        # Test negative limit - create valid request first, then test validation logic
        request = MemoryQueryRequest(
            query_type="events", limit=50
        )  # Valid for model creation
        request.limit = -1  # type: ignore

        result = memory_validator.validate_query_request(request)
        assert result.is_valid is False

        # Test limit too high - create valid request first, then test validation logic
        request = MemoryQueryRequest(
            query_type="events", limit=50
        )  # Valid for model creation
        request.limit = 2000  # Above maximum  # type: ignore

        result = memory_validator.validate_query_request(request)
        assert result.is_valid is False

    def test_invalid_filter_keys(self):
        """Test validation with invalid filter keys."""
        request = MemoryQueryRequest(
            query_type="events", filters={"invalid_filter": "value"}
        )

        result = memory_validator.validate_query_request(request)

        assert result.is_valid is False
        assert any("unknown filter" in error.lower() for error in result.errors)


class TestValidationResult:
    """Test ValidationResult structure and behavior."""

    def test_valid_result_creation(self):
        """Test creating a valid validation result."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Minor issue"],
            suggestions=["Consider improvement"],
        )

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert len(result.suggestions) == 1

    def test_invalid_result_creation(self):
        """Test creating an invalid validation result."""
        result = ValidationResult(
            is_valid=False,
            errors=["Critical error", "Another error"],
            warnings=[],
            suggestions=[],
        )

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 0

    def test_result_default_values(self):
        """Test that ValidationResult uses default empty lists."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.suggestions == []


class TestParticipantValidation:
    """Test participant name validation."""

    def test_valid_participants(self):
        """Test validation of valid participant names."""
        participants = ["Eldrin", "Lyra_Mage", "Throg-123"]
        errors = memory_validator._validate_participants(participants)

        assert len(errors) == 0

    def test_empty_participants(self):
        """Test validation with empty participant names."""
        participants = ["", "ValidName", "   "]
        errors = memory_validator._validate_participants(participants)

        assert len(errors) > 0
        assert any("empty" in error.lower() for error in errors)

    def test_reserved_participant_names(self):
        """Test validation with reserved participant names."""
        participants = ["System", "Admin", "NULL"]
        errors = memory_validator._validate_participants(participants)

        assert len(errors) > 0
        assert any("reserved" in error.lower() for error in errors)

    def test_duplicate_participants(self):
        """Test validation with duplicate participant names."""
        participants = [
            "Eldrin",
            "eldrin",
            "Lyra",
            "ELDRIN",
        ]  # Case-insensitive duplicates
        errors = memory_validator._validate_participants(participants)

        assert len(errors) > 0
        assert any("duplicate" in error.lower() for error in errors)

    def test_long_participant_names(self):
        """Test validation with excessively long participant names."""
        participants = [
            f"VeryLongNameThatExceedsTheOneHundredCharacterLimitAndShouldFailValidationBecauseItIsMuchLongerThanExpected_{i}"
            for i in range(3)
        ]
        errors = memory_validator._validate_participants(participants)

        assert len(errors) > 0
        assert any("exceeds" in error.lower() for error in errors)


class TestTagValidation:
    """Test tag validation logic."""

    def test_valid_tags(self):
        """Test validation of valid tags."""
        tags = ["warrior", "mysterious", "quest-giver", "npc_123"]
        errors = memory_validator._validate_tags(tags)

        assert len(errors) == 0

    def test_empty_tags(self):
        """Test validation with empty tags."""
        tags = ["", "valid", "   "]
        errors = memory_validator._validate_tags(tags)

        assert len(errors) > 0

    def test_reserved_tags(self):
        """Test validation with reserved tag names."""
        tags = ["system", "admin", "null"]
        errors = memory_validator._validate_tags(tags)

        assert len(errors) > 0

    def test_duplicate_tags(self):
        """Test validation with duplicate tags."""
        tags = ["warrior", "WARRIOR", "mage", "warrior"]
        errors = memory_validator._validate_tags(tags)

        assert len(errors) > 0

    def test_long_tags(self):
        """Test validation with tags that are too long."""
        tags = [
            f"this_is_a_very_long_tag_name_that_exceeds_the_fifty_character_limit_{i}"
            for i in range(3)
        ]
        errors = memory_validator._validate_tags(tags)

        assert len(errors) > 0


class TestMetadataValidation:
    """Test metadata validation logic."""

    def test_valid_metadata(self):
        """Test validation of valid metadata."""
        metadata = {
            "weather": "stormy",
            "difficulty": "hard",
            "rounds": 5,
            "participants": ["hero1", "villain1"],
        }
        errors = memory_validator._validate_metadata(metadata)

        assert len(errors) == 0

    def test_nested_metadata_too_deep(self):
        """Test validation with deeply nested metadata."""
        # Create deeply nested structure
        metadata = {"level1": {"level2": {"level3": {"level4": "deep_value"}}}}
        errors = memory_validator._validate_metadata(metadata)

        assert len(errors) > 0
        assert any("nesting depth" in error.lower() for error in errors)

    def test_large_metadata(self):
        """Test validation with metadata that's too large."""
        large_data = "x" * 5001  # Over 5KB limit
        metadata = {"large_field": large_data}
        errors = memory_validator._validate_metadata(metadata)

        assert len(errors) > 0
        assert any("size" in error.lower() for error in errors)


class TestBusinessRuleValidation:
    """Test business rule validation logic."""

    def test_event_business_rules(self):
        """Test event-specific business rule validation."""
        # Test all event business rules
        errors = memory_validator._validate_event_business_rules(
            MemoryEvent(
                event_id="test",
                timestamp=datetime.utcnow(),
                event_type="combat",
                description="Epic battle",
                participants=["Hero"],
            )
        )

        assert len(errors) > 0  # Should have combat participant rule violation

    def test_fact_business_rules(self):
        """Test fact-specific business rule validation."""
        # Test NPC fact without relationship info
        errors = memory_validator._validate_fact_business_rules(
            MemoryFact(
                fact_id="test",
                fact_type="npc",
                subject="Test NPC",
                description="Just a person selling goods",  # No relationship info
                confidence=0.7,
                source="observation",
            )
        )

        assert len(errors) > 0  # Should have relationship rule violation


class TestIDFormatValidation:
    """Test ID format validation."""

    def test_valid_id_formats(self):
        """Test validation of valid ID formats."""
        valid_ids = [
            "event_123",
            "fact_abc_def",
            "memory_123_456",
            "test-123",
            "my_memory_1",
        ]

        for valid_id in valid_ids:
            assert memory_validator._is_valid_id_format(valid_id) is True

    def test_invalid_id_formats(self):
        """Test validation of invalid ID formats."""
        invalid_ids = [
            "event 123",  # Space
            "event@123",  # Special character
            "event.123",  # Dot
            "",  # Empty
            "event#123",  # Hash
            "event$123",  # Dollar sign
            "event%123",  # Percent
        ]

        for invalid_id in invalid_ids:
            assert memory_validator._is_valid_id_format(invalid_id) is False

        # Test valid ID that starts with number
        assert memory_validator._is_valid_id_format("123event") is True
