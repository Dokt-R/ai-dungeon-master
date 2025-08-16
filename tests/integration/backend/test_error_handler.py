import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from packages.shared.errors import ErrorCode

pytestmark = pytest.mark.asyncio


async def test_validation_error_400(client):
    """Test ValidationError (400 status code) by creating a duplicate campaign."""
    # First create a campaign
    create_payload = {
        "server_id": "1234567890",
        "campaign_name": "Test Campaign",
        "owner_id": "owner123",
    }
    response = await client.post("/campaigns/create", json=create_payload)

    # Try to create the same campaign again to trigger ValidationError
    response = await client.post("/campaigns/create", json=create_payload)

    # Since we are triggering ValidationError by using a duplicate campaign we use error below
    error = ErrorCode.DUPLICATE_CAMPAIGN_NAME
    data = response.json()

    assert response.status_code == error.status_code

    # Structural checks
    assert "error" in data
    data = data["error"]

    # Exact error code check
    assert data["error_code"] == error.value

    # Message check
    # assert "already exists" in error["message"]
    assert "Test Campaign" in data["message"]  # ensure campaign name is inserted


async def test_not_found_error_404(client):
    """Test NotFoundError (404 status code) by requesting a non-existent campaign."""
    # Request a non-existent campaign to trigger NotFoundError
    response = await client.get("/campaigns/999999/players")

    error = ErrorCode.CAMPAIGN_NOT_FOUND
    data = response.json()

    assert response.status_code == error.status_code

    # Structural checks
    assert "error" in data
    data = data["error"]

    # Exact error code check
    assert data["error_code"] == error.value


async def test_pydantic_validation_error_422(client):
    """Test Pydantic ValidationError (422 status code) by sending invalid data."""
    # Send invalid data to trigger Pydantic ValidationError
    response = await client.put(
        "/servers/1234567890/config",
        json={
            "api_key": "test-key",
            "dm_roll_visibility": "invalid-value",
            "player_roll_mode": "manual",
            "character_sheet_mode": "manual",
        },
    )

    error = ErrorCode.INVALID_INPUT

    assert response.status_code == error.status_code
    assert "detail" in response.json()
    # Check that the response contains validation error details
    assert len(response.json()["detail"]) > 0


@pytest.mark.skip("AI API is not implemented yet")
async def test_ai_api_error_502(client, monkeypatch):
    """Test AIAPIError (502 status code) by triggering it in a FastAPI context."""
    # To properly test the AIAPIError, we'll add a temporary endpoint to the app
    # that raises this specific exception. This is a common pattern for testing
    # exception handlers in FastAPI.
    from packages.shared.exceptions import AIAPIError

    test_app = FastAPI()

    @test_app.get("/test-ai-error")
    async def _test_ai_error():
        raise AIAPIError(
            "Mock AI service failed",
            error_code="MOCK_AI_FAILURE",
            details={"reason": "Service unavailable"},
        )

    # Make a request to the new test endpoint
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        with pytest.raises(AIAPIError):
            await client.get("/test-ai-error")
