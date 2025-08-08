import pytest
from pydantic import SecretStr

from packages.shared.models import Server


def test_store_and_retrieve_api_key(managers):
    config = Server(
        server_id="test_server",
        api_key=SecretStr("test_api_key"),
        dm_roll_visibility="public",
        player_roll_mode="auto",
        character_sheet_mode="digital_sheet",
    )
    managers.settings.store_server_config(config)

    retrieved_key = managers.settings.retrieve_api_key("test_server")
    assert retrieved_key == "test_api_key"


def test_store_empty_api_key(managers):
    config = Server(
        server_id="test_server",
        api_key=SecretStr(""),  # Test with an empty API key
        dm_roll_visibility="public",
        player_roll_mode="auto",
        character_sheet_mode="digital_sheet",
    )

    with pytest.raises(ValueError, match="API key must not be empty."):
        managers.settings.store_server_config(config)


def test_retrieve_nonexistent_api_key(managers):
    retrieved_key = managers.settings.retrieve_api_key("nonexistent_server")
    assert retrieved_key is None


def test_store_and_retrieve_encrypted_api_key(managers):
    config = Server(
        server_id="test_server_encrypted",
        api_key=SecretStr("test_encrypted_api_key"),
        dm_roll_visibility="public",
        player_roll_mode="auto",
        character_sheet_mode="digital_sheet",
    )
    managers.settings.store_server_config(config)

    retrieved_key = managers.settings.retrieve_api_key("test_server_encrypted")
    assert retrieved_key == "test_encrypted_api_key"


def test_get_full_server_config(managers):
    config = Server(
        server_id="test_server_full_config",
        api_key=SecretStr("test_full_api_key"),
        dm_roll_visibility="hidden",
        player_roll_mode="physical",
        character_sheet_mode="physical_sheet",
    )
    managers.settings.store_server_config(config)

    retrieved_config = managers.settings.get_server_config("test_server_full_config")
    assert retrieved_config is not None
    assert retrieved_config.server_id == "test_server_full_config"
    assert retrieved_config.api_key.get_secret_value() == "test_full_api_key"
    assert retrieved_config.dm_roll_visibility == "hidden"
    assert retrieved_config.player_roll_mode == "physical"
    assert retrieved_config.character_sheet_mode == "physical_sheet"
