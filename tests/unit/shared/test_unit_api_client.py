from unittest.mock import AsyncMock, patch

import httpx
import pytest

from packages.shared.api_client import ApiClient

pytestmark = pytest.mark.asyncio


async def test_get_ai_health():
    """Test get_ai_health method."""
    client = ApiClient("http://localhost:8000")

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "healthy",
        "provider": "openai",
        "model": "gpt-4"
    }

    with patch.object(client.client, 'request', return_value=mock_response) as mock_request:
        result = await client.get_ai_health()

        # Verify the correct endpoint was called
        mock_request.assert_awaited_once_with("GET", "/api/health/ai", headers={})

        # Verify response is returned correctly
        assert result["status"] == "healthy"
        assert result["provider"] == "openai"


async def test_get_observability_health():
    """Test get_observability_health method."""
    client = ApiClient("http://localhost:8000")

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "healthy",
        "provider": "langsmith",
        "project": "ai-dungeon-master"
    }

    with patch.object(client.client, 'request', return_value=mock_response) as mock_request:
        result = await client.get_observability_health()

        mock_request.assert_awaited_once_with("GET", "/api/health/observability", headers={})

        assert result["status"] == "healthy"
        assert result["provider"] == "langsmith"


async def test_get_general_health():
    """Test get_general_health method."""
    client = ApiClient("http://localhost:8000")

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "healthy",
        "service": "ai-dungeon-master-backend",
        "version": "1.0.0"
    }

    with patch.object(client.client, 'request', return_value=mock_response) as mock_request:
        result = await client.get_general_health()

        mock_request.assert_awaited_once_with("GET", "/api/health/general", headers={})

        assert result["status"] == "healthy"
        assert result["service"] == "ai-dungeon-master-backend"


async def test_test_observability_trace():
    """Test test_observability_trace method."""
    client = ApiClient("http://localhost:8000")

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "message": "Test completed",
        "trace_id": "test-123"
    }

    with patch.object(client.client, 'request', return_value=mock_response) as mock_request:
        result = await client.test_observability_trace()

        mock_request.assert_awaited_once_with("POST", "/api/health/observability/test-trace", headers={})

        assert result["status"] == "success"
        assert result["trace_id"] == "test-123"


async def test_health_methods_with_correlation_id():
    """Test that health methods include correlation ID in headers."""
    client = ApiClient("http://localhost:8000")

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "healthy"}

    with patch('packages.shared.api_client.get_correlation_id', return_value='test-cid-123'):
        with patch.object(client.client, 'request', return_value=mock_response) as mock_request:
            await client.get_ai_health()

            # Verify correlation ID is included in headers
            call_args = mock_request.call_args
            headers = call_args.kwargs['headers']
            assert headers['X-Correlation-ID'] == 'test-cid-123'


async def test_health_methods_error_handling():
    """Test error handling in health methods."""
    client = ApiClient("http://localhost:8000")

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": {"error_code": "HEALTH_CHECK_FAILED"}}

    with patch.object(client.client, 'request', return_value=mock_response):
        with pytest.raises(Exception):  # Should raise CustomException
            await client.get_ai_health()


async def test_client_initialization():
    """Test ApiClient initialization."""
    client = ApiClient("http://test-backend:8000", timeout=15.0)

    assert client.base_url == "http://test-backend:8000"
    assert client.timeout == 15.0
    assert client.limits.max_connections == 10


async def test_close_method():
    """Test client close method."""
    client = ApiClient("http://localhost:8000")

    with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_aclose:
        await client.close()
        mock_aclose.assert_awaited_once()


async def test_context_manager():
    """Test async context manager functionality."""
    with patch.object(ApiClient, '__init__', return_value=None):
        client = ApiClient("http://localhost:8000")
        client.client = AsyncMock()
        client.client.aclose = AsyncMock()

        async with client as context_client:
            assert context_client is client

        client.client.aclose.assert_awaited_once()


async def test_sync_context_manager_raises_error():
    """Test that sync context manager raises error."""
    client = ApiClient("http://localhost:8000")

    with pytest.raises(RuntimeError, match="ApiClient is async"):
        with client:
            pass