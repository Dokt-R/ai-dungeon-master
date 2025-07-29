import pytest
from backend.server_config import SecretStr
from backend.api_key_service import APIKeyService
from backend.server_settings_manager import ServerSettingsManager
from backend.server_config import ServerConfig


@pytest.fixture
def memory_service():
    # Use an in-memory SQLite database for test isolation
    return ServerSettingsManager(db_path=":memory:")


@pytest.fixture
def api_key_service(memory_service):
    return APIKeyService(memory_service)


def test_store_and_retrieve_api_key(api_key_service):
    server_config = ServerConfig(
        server_id="test_server",
        api_key=SecretStr("test_api_key"),  # Use SecretStr for the test
        dm_roll_visibility="public",
        player_roll_mode="manual_physical_total",
        character_sheet_mode="digital_sheet",
    )
    api_key_service.store_api_key(server_config)

    retrieved_key = api_key_service.retrieve_api_key("test_server")
    assert retrieved_key == "test_api_key"


def test_store_empty_api_key(api_key_service):
    server_config = ServerConfig(
        server_id="test_server",
        api_key="",  # Test with an empty API key
        dm_roll_visibility="public",  # Provide required fields
        player_roll_mode="manual_physical_total",
        character_sheet_mode="digital_sheet",
    )

    with pytest.raises(ValueError, match="API key must not be empty."):
        api_key_service.store_api_key(server_config)


def test_retrieve_nonexistent_api_key(api_key_service):
    retrieved_key = api_key_service.retrieve_api_key("nonexistent_server")
    assert retrieved_key is None


def test_store_and_retrieve_encrypted_api_key(api_key_service):
    server_config = ServerConfig(
        server_id="test_server_encrypted",
        api_key=SecretStr("test_encrypted_api_key"),
        # Provide a valid API key for the test
        dm_roll_visibility="public",
        player_roll_mode="manual_physical_total",
        character_sheet_mode="digital_sheet",
    )
    api_key_service.store_api_key(server_config)

    retrieved_key = api_key_service.retrieve_api_key("test_server_encrypted")
    assert retrieved_key == "test_encrypted_api_key"  # Check if the decrypted
    # key matches
