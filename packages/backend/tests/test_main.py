import pytest
from fastapi.testclient import TestClient
from packages.backend.main import app

client = TestClient(app)


def test_set_server_config_success(monkeypatch):
    # Patch the APIKeyService to avoid actual DB/crypto
    def mock_store_api_key(server_config):
        assert server_config.server_id == "123"
        assert server_config.api_key.get_secret_value() == "testkey"

    app.dependency_overrides = {}
    monkeypatch.setattr(
        "packages.backend.api_key_service.APIKeyService.store_api_key",
        lambda self, server_config: mock_store_api_key(server_config),
    )
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "public",
        "character_sheet_mode": "digital_sheet",
    }
    response = client.put("/servers/123/config", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Server configuration updated successfully."


def test_set_server_config_failure(monkeypatch):
    def mock_store_api_key(server_config):
        raise Exception("DB error")

    monkeypatch.setattr(
        "packages.backend.api_key_service.APIKeyService.store_api_key",
        lambda self, server_config: mock_store_api_key(server_config),
    )
    payload = {
        "api_key": "testkey",
        "dm_roll_visibility": "public",
        "player_roll_mode": "public",
        "character_sheet_mode": "digital_sheet",
    }
    response = client.put("/servers/123/config", json=payload)
    assert response.status_code == 500
    assert "Failed to update server config" in response.json()["detail"]
