import pytest

from packages.shared.errors import ErrorCode
from packages.shared.exceptions import NotFoundError

pytestmark = pytest.mark.asyncio


async def test_set_server_config_success(client, monkeypatch):
    # Patch the ServerSettingsManager to avoid actual DB/crypto
    def mock_store_server_config(server_api):
        assert server_api.server_id == "123"
        assert server_api.api_key.get_secret_value() == "testkey"

    monkeypatch.setattr(
        "packages.backend.components.server_manager.ServerSettingsManager.store_server_config",
        lambda self, server_api: mock_store_server_config(server_api),
    )
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }
    response = await client.put("/servers/123/config", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Server configuration updated successfully."


@pytest.mark.skip(
    reason="Manual test required as the Exception 500 code causes TestClient error"
)
async def test_set_server_config_failure(client, monkeypatch):
    def mock_store_server_config(self, server_api):
        raise Exception("DB error")

    monkeypatch.setattr(
        "packages.backend.components.server_manager.ServerSettingsManager.store_server_config",
        mock_store_server_config,
    )
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }
    response = await client.put("/servers/123/config", json=payload)
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Our team has been notified.",
        }
    }


async def test_set_server_config_validation_error(client):
    payload = {
        "api_key": "",  # Invalid: empty API key
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }
    response = await client.put("/servers/123/config", json=payload)
    # Should now be 422 due to Pydantic Field Validation
    assert response.status_code == 422


async def test_set_server_config_not_found(client, monkeypatch):
    def mock_store_server_config(server_api):
        raise NotFoundError(ErrorCode.EMPTY_API_KEY)

    monkeypatch.setattr(
        "packages.backend.components.server_manager.ServerSettingsManager.store_server_config",
        lambda self, server_api: mock_store_server_config(server_api),
    )
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }
    response = await client.put("/servers/123/config", json=payload)
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"]["error_code"] == "EMPTY_API_KEY"
