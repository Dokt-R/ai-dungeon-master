"""
Unit tests for the action API endpoints.

Tests cover:
- POST /action endpoint functionality
- Request validation and error handling
- Response formatting and validation
- Integration with FastAPI router
- Correlation ID handling
- Logging integration
"""

import pytest
from fastapi.testclient import TestClient

from packages.backend.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestActionEndpoint:
    """Test the POST /action endpoint."""

    def test_valid_action_request_minimal(self, client):
        """Test POST /action with valid minimal request."""
        request_data = {
            "prompt": "I want to investigate the room",
            "session_id": "session_123",
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "narrative" in data
        assert "session_id" in data
        assert "status" in data
        assert "correlation_id" in data

        # Validate specific values
        assert data["session_id"] == "session_123"
        assert data["status"] == "success"
        assert isinstance(data["correlation_id"], str)
        assert len(data["narrative"]) > 0

    def test_valid_action_request_complete(self, client):
        """Test POST /action with valid complete request."""
        request_data = {
            "prompt": "I attack the goblin with my sword",
            "session_id": "session_456",
            "campaign_context": {"campaign_name": "Test Campaign", "level": 3},
            "user_id": "user_789",
            "metadata": {"source": "discord", "channel_id": "123456789"},
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "narrative" in data
        assert "session_id" in data
        assert "metadata" in data
        assert "processing_time" in data
        assert "status" in data
        assert "correlation_id" in data

        # Validate specific values
        assert data["session_id"] == "session_456"
        assert data["status"] == "success"
        assert "request_metadata" in data["metadata"]
        assert "campaign_context" in data["metadata"]
        assert data["processing_time"] >= 0

    def test_invalid_request_missing_prompt(self, client):
        """Test POST /action with missing prompt field."""
        request_data = {
            "session_id": "session_123"
            # Missing "prompt"
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 422
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        assert "correlation_id" in data["detail"]
        assert (
            "missing" in data["detail"]["error"].lower()
            or "required" in data["detail"]["error"].lower()
        )

    def test_invalid_request_missing_session_id(self, client):
        """Test POST /action with missing session_id field."""
        request_data = {
            "prompt": "I want to investigate"
            # Missing "session_id"
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 422
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        assert "correlation_id" in data["detail"]

    def test_invalid_request_empty_prompt(self, client):
        """Test POST /action with empty prompt."""
        request_data = {"prompt": "", "session_id": "session_123"}

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 422
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]

    def test_invalid_request_prompt_too_long(self, client):
        """Test POST /action with prompt exceeding maximum length."""
        long_prompt = "x" * 2001  # Exceeds 2000 character limit
        request_data = {"prompt": long_prompt, "session_id": "session_123"}

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 422
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]

    def test_invalid_request_invalid_session_id(self, client):
        """Test POST /action with invalid session_id pattern."""
        invalid_session_ids = [
            "session 123",  # Contains space
            "session@123",  # Contains @ symbol
            "session.123",  # Contains dot
            "",  # Empty string
        ]

        for invalid_id in invalid_session_ids:
            request_data = {"prompt": "I want to investigate", "session_id": invalid_id}

            response = client.post("/api/action", json=request_data)

            assert response.status_code == 422
            data = response.json()
            assert "detail" in data
            assert "error" in data["detail"]

    def test_request_with_correlation_id_header(self, client):
        """Test POST /action with custom correlation ID header."""
        custom_correlation_id = "550e8400-e29b-41d4-a716-446655440000"
        request_data = {"prompt": "I want to explore", "session_id": "session_123"}

        response = client.post(
            "/api/action",
            json=request_data,
            headers={"X-Correlation-ID": custom_correlation_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["correlation_id"] == custom_correlation_id

    def test_request_validation_with_campaign_context(self, client):
        """Test POST /action with campaign context validation."""
        request_data = {
            "prompt": "I want to start a campaign",
            "session_id": "session_123",
            "campaign_context": {"campaign_name": "Test Campaign"},
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "campaign_context" in data["metadata"]

    def test_request_validation_with_user_id(self, client):
        """Test POST /action with user_id validation."""
        request_data = {
            "prompt": "I want to join as a player",
            "session_id": "session_123",
            "user_id": "player_456",
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "session_123"

    def test_request_validation_with_metadata(self, client):
        """Test POST /action with metadata validation."""
        request_data = {
            "prompt": "I want to send a message",
            "session_id": "session_123",
            "metadata": {"source": "discord", "channel": "123"},
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "request_metadata" in data["metadata"]

    def test_malformed_json_request(self, client):
        """Test POST /action with malformed JSON."""
        response = client.post(
            "/api/action",
            content="invalid json {",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_request_with_additional_fields(self, client):
        """Test POST /action with additional unexpected fields."""
        request_data = {
            "prompt": "I want to investigate",
            "session_id": "session_123",
            "unexpected_field": "should_be_ignored",
        }

        response = client.post("/api/action", json=request_data)

        # FastAPI should ignore unexpected fields
        assert response.status_code == 200
        data = response.json()
        assert "unexpected_field" not in data


class TestActionEndpointResponseFormats:
    """Test response formatting for the action endpoint."""

    def test_response_format_minimal(self, client):
        """Test minimal response format."""
        request_data = {"prompt": "I look around", "session_id": "session_123"}

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "narrative" in data
        assert "session_id" in data
        assert "status" in data
        assert "correlation_id" in data

        # Optional fields that should be None if not provided
        assert "metadata" in data
        assert "processing_time" in data
        assert "error" in data

    def test_response_format_complete(self, client):
        """Test complete response format with all fields."""
        request_data = {
            "prompt": "I cast a spell",
            "session_id": "session_456",
            "campaign_context": {"spell_level": 3},
            "user_id": "wizard_123",
            "metadata": {"spell_slot": 3},
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # All fields should be present
        assert "narrative" in data
        assert "session_id" in data
        assert "metadata" in data
        assert "processing_time" in data
        assert "status" in data
        assert "correlation_id" in data
        assert "error" in data

        # Validate specific content
        assert data["session_id"] == "session_456"
        assert data["status"] == "success"
        assert isinstance(data["processing_time"], float)
        assert isinstance(data["correlation_id"], str)

    def test_error_response_format(self, client):
        """Test error response format."""
        # Send invalid request to trigger error
        request_data = {
            "prompt": "",  # Invalid: empty prompt
            "session_id": "session_123",
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 422
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        assert "correlation_id" in data["detail"]
        assert "details" in data["detail"]


class TestActionEndpointIntegration:
    """Integration tests for the action endpoint."""

    def test_endpoint_registration(self, client):
        """Test that the action endpoint is properly registered."""
        # Test main endpoint
        response = client.post(
            "/api/action", json={"prompt": "test", "session_id": "session_123"}
        )
        assert response.status_code in [
            200,
            422,
        ]  # 422 for validation error, but endpoint exists

        # Test test endpoint
        response = client.get("/api/action/test")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data

    def test_multiple_requests_same_session(self, client):
        """Test multiple requests with the same session ID."""
        session_id = "session_multi_test"

        for i in range(3):
            request_data = {"prompt": f"I perform action {i}", "session_id": session_id}

            response = client.post("/api/action", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert data["status"] == "success"

    def test_concurrent_session_handling(self, client):
        """Test handling of requests from different sessions."""
        sessions = ["session_1", "session_2", "session_3"]

        for session_id in sessions:
            request_data = {
                "prompt": "I want to test concurrent sessions",
                "session_id": session_id,
            }

            response = client.post("/api/action", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id

    def test_response_time_measurement(self, client):
        """Test that processing time is properly measured."""
        request_data = {
            "prompt": "I want to test response timing",
            "session_id": "session_timing",
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "processing_time" in data
        assert isinstance(data["processing_time"], float)
        assert data["processing_time"] >= 0

    def test_correlation_id_propagation(self, client):
        """Test that correlation IDs are properly propagated."""
        custom_correlation_id = "test-correlation-123"

        request_data = {
            "prompt": "I want to test correlation",
            "session_id": "session_corr",
        }

        response = client.post(
            "/api/action",
            json=request_data,
            headers={"X-Correlation-ID": custom_correlation_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["correlation_id"] == custom_correlation_id


class TestActionEndpointEdgeCases:
    """Test edge cases for the action endpoint."""

    def test_special_characters_in_prompt(self, client):
        """Test prompts with special characters."""
        special_prompts = [
            "I cast 'magic missile' at the target!",
            "I search for hidden doors...",
            "I ask: 'What's the meaning of this?'",
            "I use my potion of healing (+)",
            "I attack with my sword ⚔️",
        ]

        for prompt in special_prompts:
            request_data = {"prompt": prompt, "session_id": "session_special"}

            response = client.post("/api/action", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_unicode_characters_in_prompt(self, client):
        """Test prompts with unicode characters."""
        unicode_prompts = [
            "I speak in Elvish: 'Galu del' (friend hello)",
            "I examine the ancient runes: 'ᚠᛖᚻᚹᛦᛚᚳ'",
            "I cast fireball! 🔥",
            "I find a treasure chest with 💰 inside",
        ]

        for prompt in unicode_prompts:
            request_data = {"prompt": prompt, "session_id": "session_unicode"}

            response = client.post("/api/action", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_large_metadata_handling(self, client):
        """Test handling of large metadata objects."""
        large_metadata = {
            "source": "discord",
            "channel_id": "12345678901234567890",
            "guild_id": "09876543210987654321",
            "user_info": {
                "id": "12345678901234567890",
                "username": "testuser",
                "discriminator": "1234",
                "avatar": "a_very_long_avatar_hash_string_that_goes_on_and_on",
                "roles": ["role1", "role2", "role3", "role4", "role5"],
                "permissions": ["read", "write", "admin", "moderate"],
            },
        }

        request_data = {
            "prompt": "I want to test large metadata",
            "session_id": "session_large_meta",
            "metadata": large_metadata,
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "request_metadata" in data["metadata"]

    def test_boundary_length_prompts(self, client):
        """Test prompts at boundary lengths."""
        # Test minimum length
        request_data = {
            "prompt": "a",  # 1 character
            "session_id": "session_boundary",
        }
        response = client.post("/api/action", json=request_data)
        assert response.status_code == 200

        # Test maximum length
        max_prompt = "a" * 2000
        request_data = {"prompt": max_prompt, "session_id": "session_boundary"}
        response = client.post("/api/action", json=request_data)
        assert response.status_code == 200

    def test_empty_optional_fields(self, client):
        """Test request with explicitly empty optional fields."""
        request_data = {
            "prompt": "I want to test empty fields",
            "session_id": "session_empty",
            "campaign_context": None,
            "user_id": None,
            "metadata": None,
        }

        response = client.post("/api/action", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
