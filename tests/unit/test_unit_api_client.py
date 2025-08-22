"""
Unit tests for the thin API client.
Tests error handling, response parsing, and method functionality.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from packages.shared.api_client import ApiClient
from packages.shared.exceptions import (
    CustomException,
)
from packages.shared.models import AddCharacterRequest, ListCharactersRequest


@pytest.mark.asyncio
class TestApiClient:
    """Test suite for ApiClient."""

    @pytest_asyncio.fixture
    async def api_client(self):
        """Create an API client for testing."""
        client = ApiClient(base_url="http://test")
        yield client
        await client.close()

    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.json.return_value = {"success": True}
        return response

    @pytest.fixture
    def mock_error_response(self):
        """Create a mock HTTP error response."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 400
        response.json.return_value = {
            "error": {
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid input",
                "details": {"field": "name"},
            }
        }
        return response

    async def test_successful_response_handling(self, api_client, mock_response):
        """Test successful response handling."""
        with patch.object(api_client.client, "post", return_value=mock_response):
            result = await api_client._handle_response(mock_response)
            assert result == {"success": True}

    async def test_validation_error_handling(self, api_client, mock_error_response):
        """Test validation error handling."""
        with pytest.raises(CustomException) as exc_info:
            await api_client._handle_response(mock_error_response)

        # The error code should be converted to ErrorCode enum
        from packages.shared.errors import ErrorCode

        assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR

    async def test_not_found_error_handling(self, api_client):
        """Test 404 error handling."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 404
        response.json.return_value = {
            "error": {
                "error_code": "CHARACTER_NOT_FOUND",
                "message": "Character not found",
                "details": {},
            }
        }

        with pytest.raises(CustomException):
            await api_client._handle_response(response)

    async def test_permission_denied_error_handling(self, api_client):
        """Test 403 error handling."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 403
        response.json.return_value = {
            "error": {
                "error_code": "PERMISSION_DENIED_ERROR",
                "message": "Access denied",
                "details": {},
            }
        }

        with pytest.raises(CustomException):
            await api_client._handle_response(response)

    async def test_ai_api_error_handling(self, api_client):
        """Test 502 error handling."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 502
        response.json.return_value = {
            "error": {
                "error_code": "AI_API_ERROR",
                "message": "AI service unavailable",
                "details": {},
            }
        }

        with pytest.raises(CustomException):
            await api_client._handle_response(response)

    async def test_unknown_error_handling(self, api_client):
        """Test unknown error handling."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 500
        response.json.return_value = {
            "error": {
                "error_code": "UNKNOWN",
                "message": "Internal server error",
                "details": {},
            }
        }

        with pytest.raises(CustomException):
            await api_client._handle_response(response)

    async def test_malformed_error_response(self, api_client):
        """Test handling of malformed error responses."""
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 400
        response.json.side_effect = ValueError("Invalid JSON")
        response.text = "Invalid JSON response"

        with pytest.raises(CustomException):
            await api_client._handle_response(response)

    async def test_add_character_success(self, api_client):
        """Test successful character addition."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "character_id": 123,
            "name": "Test Character",
            "player_id": "12345",
        }

        with patch.object(api_client.client, "post", return_value=mock_response):
            req = AddCharacterRequest(
                player_id="12345", name="Test Character", character_url=None
            )
            result = await api_client.add_character(req)

            assert result["character_id"] == 123
            assert result["name"] == "Test Character"

    async def test_list_characters_success(self, api_client):
        """Test successful character listing."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "characters": [
                {"character_id": 1, "name": "Character 1", "player_id": "12345"},
                {"character_id": 2, "name": "Character 2", "player_id": "12345"},
            ]
        }

        with patch.object(api_client.client, "post", return_value=mock_response):
            req = ListCharactersRequest(player_id="12345")
            result = await api_client.list_characters(req)

            assert len(result["characters"]) == 2
            assert result["characters"][0]["name"] == "Character 1"

    async def test_context_manager_support(self):
        """Test async context manager support."""
        async with ApiClient(base_url="http://localhost:8000") as client:
            assert client is not None
            assert hasattr(client, "client")

    async def test_connection_pooling_configuration(self, api_client):
        """Test that connection pooling is properly configured."""
        assert api_client.limits.max_connections == 10
        assert api_client.limits.max_keepalive_connections == 5

    async def test_base_url_normalization(self):
        """Test that base URL is properly normalized."""
        client = ApiClient(base_url="http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"
        await client.close()

    async def test_timeout_configuration(self):
        """Test timeout configuration."""
        client = ApiClient(base_url="http://localhost:8000", timeout=30.0)
        assert client.timeout == 30.0
        await client.close()


@pytest.mark.asyncio
class TestApiClientIntegration:
    """Integration tests for API client (requires running backend)."""

    @pytest_asyncio.fixture
    async def api_client(self):
        """Create an API client for integration testing."""
        client = ApiClient(base_url="http://localhost:8000")
        yield client
        await client.close()

    @pytest.mark.skip(reason="Requires running backend server")
    async def test_real_api_connection(self, api_client):
        """Test connection to real API (skipped by default)."""
        # This test would require a running backend server
        # Uncomment and modify as needed for integration testing
        pass
