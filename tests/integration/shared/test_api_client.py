import httpx
import pytest

from packages.shared.api_client import ApiClient


# Test the real ApiClient in isolation
@pytest.mark.asyncio
async def test_api_client_list_characters_real():
    """Integration test for ApiClient against real/test API"""
    client = ApiClient("http://test-api:8000")
    response = await client.list_characters(user_id="123")
    assert isinstance(response, dict)
    assert "characters" in response

# Test ApiClient error handling
@pytest.mark.asyncio  
async def test_api_client_handles_network_errors():
    client = ApiClient("http://nonexistent:8000")
    with pytest.raises(httpx.ConnectError):
        await client.list_characters(user_id="123")