from fastapi.testclient import TestClient
from packages.backend.main import app

client = TestClient(app)


def test_set_server_config_success(monkeypatch):
    # Patch the ServerSettingsManager to avoid actual DB/crypto
    def mock_store_server_config(server_api):
        assert server_api.server_id == "123"
        assert server_api.api_key.get_secret_value() == "testkey"

    app.dependency_overrides = {}
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
    response = client.put("/servers/123/config", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Server configuration updated successfully."


def test_set_server_config_failure(monkeypatch):
    def mock_store_server_config(server_api):
        raise Exception("DB error")

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
    response = client.put("/servers/123/config", json=payload)
    assert response.status_code == 500
    assert "DB error" in response.json()["detail"]


def test_set_server_config_validation_error():
    payload = {
        "api_key": "",  # Invalid: empty API key
        "dm_roll_visibility": "public",
        "player_roll_mode": "auto",
        "character_sheet_mode": "digital_sheet",
    }
    response = client.put("/servers/123/config", json=payload)
    # Should now be 400 due to ValidationError
    assert response.status_code == 400
    assert "API key is required" in response.text


def test_set_server_config_not_found(monkeypatch):
    def mock_store_server_config(server_api):
        from packages.shared.error_handler import NotFoundError

        raise NotFoundError("Server not found")

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
    response = client.put("/servers/123/config", json=payload)
    assert response.status_code == 404
    assert "Server not found" in response.text
