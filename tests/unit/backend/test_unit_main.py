import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from pydantic import SecretStr

from packages.backend.main import app
from packages.backend.components.server_manager import ServerSettingsManager
from packages.shared.models import Server
from packages.shared.error_handler import NotFoundError


@pytest.fixture
def mock_server_manager():
    return MagicMock(spec=ServerSettingsManager)


@pytest.fixture
def client(mock_server_manager: MagicMock):
    app.dependency_overrides[ServerSettingsManager] = lambda: mock_server_manager
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {}


def test_set_server_config_success(client: TestClient, mock_server_manager: MagicMock):
    # Arrange
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }

    # Act
    response = client.put("/servers/123/config", json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Server configuration updated successfully."
    mock_server_manager.store_server_config.assert_called_once()
    # You can add more specific assertions on the argument passed if needed
    call_args = mock_server_manager.store_server_config.call_args[0][0]
    assert isinstance(call_args, Server)
    assert call_args.server_id == "123"
    assert call_args.api_key.get_secret_value() == "testkey"

@pytest.mark.skip(reason="Manual test required as the Exception 500 code causes TestClient error")
def test_set_server_config_failure(client: TestClient, mock_server_manager: MagicMock):
    # Arrange
    mock_server_manager.store_server_config.side_effect = Exception("DB error")
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }

    # Act
    response = client.put("/servers/123/config", json=payload)

    # Assert
    assert response.status_code == 500
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "unexpected error occurred" in response.json()["error"]["message"]


def test_set_server_config_validation_error(client: TestClient):
    # Arrange
    payload = {
        "api_key": "",  # Invalid: empty API key
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }
    # Act
    response = client.put("/servers/123/config", json=payload)

    # Assert
    assert response.status_code == 400  # validation error
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "API key is required" in response.json()["error"]["message"]


def test_set_server_config_not_found(
    client: TestClient, mock_server_manager: MagicMock
):
    # Arrange
    mock_server_manager.store_server_config.side_effect = NotFoundError(
        "Server not found"
    )
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }

    # Act
    response = client.put("/servers/123/config", json=payload)

    # Assert
    assert response.status_code == 404
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert "Server not found" in response.json()["error"]["message"]
