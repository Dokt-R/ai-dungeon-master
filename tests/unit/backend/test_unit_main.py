from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from packages.backend.components.server_manager import ServerSettingsManager
from packages.backend.main import app
from packages.shared.error_handler import NotFoundError
from packages.shared.models import Server


@pytest.fixture
def mock_server_manager():
    return AsyncMock(spec=ServerSettingsManager)


@pytest_asyncio.fixture
async def client(mock_server_manager: AsyncMock):
    app.dependency_overrides[ServerSettingsManager] = lambda: mock_server_manager
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_set_server_config_success(
    client: AsyncClient, mock_server_manager: AsyncMock
):
    # Arrange
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }

    # Act
    response = await client.put("/servers/123/config", json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Server configuration updated successfully."
    mock_server_manager.store_server_config.assert_called_once()
    # You can add more specific assertions on the argument passed if needed
    call_args = mock_server_manager.store_server_config.call_args[0][0]
    assert isinstance(call_args, Server)
    assert call_args.server_id == "123"
    assert call_args.api_key.get_secret_value() == "testkey"


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Something is going on with the mocking. Need to test in real life or keep only integration test"
)
async def test_set_server_config_failure(
    client: AsyncClient, mock_server_manager: AsyncMock
):
    # Arrange
    mock_server_manager.store_server_config.side_effect = Exception("DB error")
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }

    # Act

    response = await client.put("/servers/123/config", json=payload)

    # Assert
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "An unexpected error occurred" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_set_server_config_validation_error(client: AsyncClient):
    # Arrange
    payload = {
        "api_key": "",  # Invalid: empty API key
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }
    # Act
    response = await client.put("/servers/123/config", json=payload)

    # Assert
    assert response.status_code == 400


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Something is going on with the mocking. Need to test in real life or keep only integration test"
)
async def test_set_server_config_not_found(
    client: AsyncClient, mock_server_manager: AsyncMock
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
    response = await client.put("/servers/123/config", json=payload)

    # Assert
    assert response.status_code == 404
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert "Server not found" in response.json()["error"]["message"]
