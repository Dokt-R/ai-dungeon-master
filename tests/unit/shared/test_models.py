"""
Unit tests for shared Pydantic models.

Tests cover:
- ActionRequest and ActionResponse model validation
- Field constraints and validation rules
- Error message formatting
- Edge cases and boundary conditions
"""

import pytest
from pydantic import ValidationError

from packages.shared.models import ActionRequest, ActionResponse


class TestActionRequest:
    """Test the ActionRequest model."""

    def test_valid_action_request_minimal(self):
        """Test creating a valid ActionRequest with minimal required fields."""
        request = ActionRequest(
            prompt="I want to investigate the room", session_id="session_123"
        )

        assert request.prompt == "I want to investigate the room"
        assert request.session_id == "session_123"
        assert request.campaign_context is None
        assert request.user_id is None
        assert request.metadata is None

    def test_valid_action_request_complete(self):
        """Test creating a valid ActionRequest with all fields."""
        campaign_context = {"campaign_name": "Test Campaign", "level": 3}
        metadata = {"source": "discord", "channel": "123"}

        request = ActionRequest(
            prompt="I attack the goblin with my sword",
            session_id="session_456",
            campaign_context=campaign_context,
            user_id="user_789",
            metadata=metadata,
        )

        assert request.prompt == "I attack the goblin with my sword"
        assert request.session_id == "session_456"
        assert request.campaign_context == campaign_context
        assert request.user_id == "user_789"
        assert request.metadata == metadata

    def test_prompt_validation_min_length(self):
        """Test prompt minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ActionRequest(prompt="", session_id="session_123")

        error = exc_info.value.errors()[0]
        assert error["loc"] == ("prompt",)
        assert "min_length" in error["ctx"]

    def test_prompt_validation_max_length(self):
        """Test prompt maximum length validation."""
        long_prompt = "x" * 2001  # Exceeds 2000 character limit

        with pytest.raises(ValidationError) as exc_info:
            ActionRequest(prompt=long_prompt, session_id="session_123")

        error = exc_info.value.errors()[0]
        assert error["loc"] == ("prompt",)
        assert "max_length" in error["ctx"]

    def test_session_id_validation_pattern(self):
        """Test session_id pattern validation."""
        invalid_session_ids = [
            "session 123",  # space not allowed
            "session@123",  # @ not allowed
            "session.123",  # . not allowed
            "",  # empty not allowed
        ]

        for invalid_id in invalid_session_ids:
            with pytest.raises(ValidationError):
                ActionRequest(prompt="test prompt", session_id=invalid_id)

    def test_session_id_validation_valid_patterns(self):
        """Test that valid session_id patterns are accepted."""
        valid_session_ids = [
            "session_123",
            "session-456",
            "session789",
            "my_session_id",
            "session-id-with-dashes",
            "session_id_with_underscores",
            "SESSION123",
            "123session",
        ]

        for valid_id in valid_session_ids:
            request = ActionRequest(prompt="test prompt", session_id=valid_id)
            assert request.session_id == valid_id

    def test_user_id_validation_pattern(self):
        """Test user_id pattern validation."""
        # Should work with valid pattern
        request = ActionRequest(
            prompt="test prompt", session_id="session_123", user_id="user_456"
        )
        assert request.user_id == "user_456"

        # Should fail with invalid pattern
        with pytest.raises(ValidationError):
            ActionRequest(
                prompt="test prompt",
                session_id="session_123",
                user_id="user@456",  # @ not allowed
            )

    def test_user_id_validation_max_length(self):
        """Test user_id maximum length validation."""
        long_user_id = "x" * 129  # Exceeds 128 character limit

        with pytest.raises(ValidationError):
            ActionRequest(
                prompt="test prompt", session_id="session_123", user_id=long_user_id
            )

    def test_campaign_context_validation(self):
        """Test campaign_context validation."""
        # Should work with dict
        context = {"name": "Test Campaign", "level": 5}
        request = ActionRequest(
            prompt="test prompt", session_id="session_123", campaign_context=context
        )
        assert request.campaign_context == context

        # Should work with None
        request = ActionRequest(
            prompt="test prompt", session_id="session_123", campaign_context=None
        )
        assert request.campaign_context is None

    def test_metadata_validation(self):
        """Test metadata validation."""
        # Should work with dict
        meta = {"source": "discord", "channel_id": "123456"}
        request = ActionRequest(
            prompt="test prompt", session_id="session_123", metadata=meta
        )
        assert request.metadata == meta

        # Should work with None
        request = ActionRequest(
            prompt="test prompt", session_id="session_123", metadata=None
        )
        assert request.metadata is None


class TestActionResponse:
    """Test the ActionResponse model."""

    def test_valid_action_response_minimal(self):
        """Test creating a valid ActionResponse with minimal required fields."""
        response = ActionResponse(
            narrative="The DM responds with a narrative continuation",
            session_id="session_123",
        )

        assert response.narrative == "The DM responds with a narrative continuation"
        assert response.session_id == "session_123"
        assert response.metadata is None
        assert response.processing_time is None
        assert response.status == "success"
        assert response.correlation_id is None
        assert response.error is None

    def test_valid_action_response_complete(self):
        """Test creating a valid ActionResponse with all fields."""
        metadata = {"model": "gpt-5-nano", "tokens": 150}
        error = {"code": "RATE_LIMIT", "message": "Too many requests"}

        response = ActionResponse(
            narrative="You discover a hidden treasure chest!",
            session_id="session_456",
            metadata=metadata,
            processing_time=2.5,
            status="partial",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
            error=error,
        )

        assert response.narrative == "You discover a hidden treasure chest!"
        assert response.session_id == "session_456"
        assert response.metadata == metadata
        assert response.processing_time == 2.5
        assert response.status == "partial"
        assert response.correlation_id == "550e8400-e29b-41d4-a716-446655440000"
        assert response.error == error

    def test_narrative_validation_min_length(self):
        """Test narrative minimum length validation."""
        with pytest.raises(ValidationError):
            ActionResponse(narrative="", session_id="session_123")

    def test_narrative_validation_max_length(self):
        """Test narrative maximum length validation."""
        long_narrative = "x" * 4001  # Exceeds 4000 character limit

        with pytest.raises(ValidationError) as exc_info:
            ActionResponse(narrative=long_narrative, session_id="session_123")

        error = exc_info.value.errors()[0]
        assert error["loc"] == ("narrative",)

    def test_processing_time_validation_positive(self):
        """Test processing_time positive value validation."""
        with pytest.raises(ValidationError):
            ActionResponse(
                narrative="test narrative", session_id="session_123", processing_time=-1
            )

    def test_processing_time_validation_max_value(self):
        """Test processing_time maximum value validation."""
        with pytest.raises(ValidationError):
            ActionResponse(
                narrative="test narrative",
                session_id="session_123",
                processing_time=301,  # Exceeds 300 second limit
            )

    def test_status_default_value(self):
        """Test that status defaults to 'success'."""
        response = ActionResponse(narrative="test narrative", session_id="session_123")
        assert response.status == "success"

    def test_session_id_required(self):
        """Test that session_id is required."""
        with pytest.raises(ValidationError):
            ActionResponse(narrative="test narrative")

    def test_optional_fields(self):
        """Test that all optional fields can be None."""
        response = ActionResponse(
            narrative="test narrative",
            session_id="session_123",
            metadata=None,
            processing_time=None,
            correlation_id=None,
            error=None,
        )

        assert response.metadata is None
        assert response.processing_time is None
        assert response.correlation_id is None
        assert response.error is None


class TestModelIntegration:
    """Test integration between ActionRequest and ActionResponse models."""

    def test_request_response_session_id_consistency(self):
        """Test that session_id flows consistently from request to response."""
        request = ActionRequest(
            prompt="I want to explore the dungeon", session_id="dungeon_session_001"
        )

        # Simulate processing
        response = ActionResponse(
            narrative="You enter the dark dungeon, hearing echoes in the distance.",
            session_id=request.session_id,  # Use same session_id
        )

        assert request.session_id == response.session_id

    def test_request_metadata_preservation(self):
        """Test that request metadata can be preserved in response."""
        request_metadata = {"source": "discord", "user": "player123"}
        campaign_context = {"campaign": "Lost Mines", "level": 2}

        request = ActionRequest(
            prompt="I search for hidden doors",
            session_id="session_001",
            campaign_context=campaign_context,
            user_id="player123",
            metadata=request_metadata,
        )

        # Response should be able to reference request data
        response = ActionResponse(
            narrative="You carefully search the walls and find a secret door!",
            session_id=request.session_id,
            metadata={
                "request_metadata": request.metadata,
                "campaign_context": request.campaign_context,
                "processed_by": "ai_dm_system",
            },
        )

        assert response.metadata["request_metadata"] == request_metadata
        assert response.metadata["campaign_context"] == campaign_context

    def test_error_response_format(self):
        """Test error response format consistency."""
        error_info = {
            "code": "AI_SERVICE_UNAVAILABLE",
            "message": "AI service is temporarily unavailable",
            "retry_after": 60,
        }

        response = ActionResponse(
            narrative="The DM seems distracted and doesn't respond clearly.",
            session_id="session_001",
            status="error",
            error=error_info,
        )

        assert response.status == "error"
        assert response.error == error_info
        assert "code" in response.error
        assert "message" in response.error


class TestModelValidationEdgeCases:
    """Test edge cases and boundary conditions for model validation."""

    def test_prompt_with_special_characters(self):
        """Test prompt validation with special characters."""
        special_prompts = [
            "I want to investigate the room!",
            "I attack the goblin with my sword...",
            "I ask: 'What's the meaning of this?'",
            "I cast 'magic missile' at the target",
            "I use my potion of healing (+)",
        ]

        for prompt in special_prompts:
            request = ActionRequest(prompt=prompt, session_id="session_123")
            assert request.prompt == prompt

    def test_session_id_boundary_lengths(self):
        """Test session_id validation at boundary lengths."""
        # Test minimum length (1 character)
        request = ActionRequest(prompt="test", session_id="a")
        assert request.session_id == "a"

        # Test maximum length (128 characters)
        max_length_id = "a" * 128
        request = ActionRequest(prompt="test", session_id=max_length_id)
        assert request.session_id == max_length_id

        # Test over maximum length
        over_length_id = "a" * 129
        with pytest.raises(ValidationError):
            ActionRequest(prompt="test", session_id=over_length_id)

    def test_narrative_boundary_lengths(self):
        """Test narrative validation at boundary lengths."""
        # Test minimum length (1 character)
        response = ActionResponse(narrative="a", session_id="session_123")
        assert response.narrative == "a"

        # Test maximum length (4000 characters)
        max_length_narrative = "a" * 4000
        response = ActionResponse(
            narrative=max_length_narrative, session_id="session_123"
        )
        assert response.narrative == max_length_narrative

        # Test over maximum length
        over_length_narrative = "a" * 4001
        with pytest.raises(ValidationError):
            ActionResponse(narrative=over_length_narrative, session_id="session_123")

    def test_processing_time_precision(self):
        """Test processing_time with decimal precision."""
        test_times = [0.001, 0.1, 1.5, 10.75, 299.999]

        for time_value in test_times:
            response = ActionResponse(
                narrative="test narrative",
                session_id="session_123",
                processing_time=time_value,
            )
            assert response.processing_time == time_value
