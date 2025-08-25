import httpx
import pytest

from packages.shared.api_client import ApiClient
from packages.shared.models import ListCharactersRequest


# Test the real ApiClient in isolation
@pytest.mark.asyncio
@pytest.mark.skip(reason="Need feedback for proper integration testing")
async def test_api_client_list_characters_real():
    """Integration test for ApiClient against real/test API"""
    client = ApiClient("http://test-api:8000")
    req = ListCharactersRequest(player_id="123")

    response = await client.list_characters(req)
    assert isinstance(response, dict)
    assert "characters" in response


# Test ApiClient error handling
@pytest.mark.skip(reason="Need feedback for proper integration testing")
@pytest.mark.asyncio
async def test_api_client_handles_network_errors():
    client = ApiClient("http://nonexistent:8000")
    with pytest.raises(httpx.ConnectError):
        await client.list_characters(player_id="123")
