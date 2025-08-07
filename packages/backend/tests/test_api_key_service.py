import pytest
from packages.backend.components.server_config import ServerConfig, SecretStr


def test_store_and_retrieve_api_key(managers):
    server_config = ServerConfig(
        server_id="test_server",
        api_key=SecretStr("test_api_key"),  # Use SecretStr for the test
        dm_roll_visibility="public",
        player_roll_mode="auto",
        character_sheet_mode="digital_sheet",
    )
    managers.settings.store_api_key(server_config)

    retrieved_key = managers.settings.retrieve_api_key("test_server")
    assert retrieved_key == "test_api_key"


def test_store_empty_api_key(managers):
    server_config = ServerConfig(
        server_id="test_server",
        api_key="",  # Test with an empty API key
        dm_roll_visibility="public",  # Provide required fields
        player_roll_mode="auto",
        character_sheet_mode="digital_sheet",
    )

    with pytest.raises(ValueError, match="API key must not be empty."):
        managers.settings.store_api_key(server_config)


def test_retrieve_nonexistent_api_key(managers):
    retrieved_key = managers.settings.retrieve_api_key("nonexistent_server")
    assert retrieved_key is None


def test_store_and_retrieve_encrypted_api_key(managers):
    server_config = ServerConfig(
        server_id="test_server_encrypted",
        api_key=SecretStr("test_encrypted_api_key"),
        # Provide a valid API key for the test
        dm_roll_visibility="public",
        player_roll_mode="auto",
        character_sheet_mode="digital_sheet",
    )
    managers.settings.store_api_key(server_config)

    retrieved_key = managers.settings.retrieve_api_key("test_server_encrypted")
    assert retrieved_key == "test_encrypted_api_key"
