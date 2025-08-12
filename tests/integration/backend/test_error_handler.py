import pytest
from fastapi import HTTPException
from packages.backend.main import app
from packages.shared.error_handler import NotFoundError, ValidationError
from packages.shared.models import ServerConfigModel
from pydantic import ValidationError as PydanticValidationError


def test_validation_error_400(client):
    """Test ValidationError (400 status code) by creating a duplicate campaign."""
    # First create a campaign
    create_payload = {
        "server_id": "1234567890",
        "campaign_name": "Test Campaign",
        "owner_id": "owner123"
    }
    response = client.post("/campaigns/new", json=create_payload)
    print(f"First request status: {response.status_code}")
    print(f"First request response: {response.json()}")
    
    # Try to create the same campaign again to trigger ValidationError
    response = client.post("/campaigns/new", json=create_payload)
    print(f"Second request status: {response.status_code}")
    print(f"Second request response: {response.json()}")
    
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "already exists" in response.json()["error"]["message"]


def test_not_found_error_404(client):
    """Test NotFoundError (404 status code) by requesting a non-existent campaign."""
    # Request a non-existent campaign to trigger NotFoundError
    response = client.get("/campaigns/999999/players")
    
    assert response.status_code == 404
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert "not found" in response.json()["error"]["message"]


def test_pydantic_validation_error_422(client):
    """Test Pydantic ValidationError (422 status code) by sending invalid data."""
    # Send invalid data to trigger Pydantic ValidationError
    response = client.put(
        "/servers/1234567890/config",
        json={"api_key": "test-key", "dm_roll_visibility": "invalid-value", "player_roll_mode": "manual", "character_sheet_mode": "manual"}
    )
    
    assert response.status_code == 422
    assert "detail" in response.json()
    # Check that the response contains validation error details
    assert len(response.json()["detail"]) > 0
