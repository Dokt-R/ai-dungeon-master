import pytest
from backend.api_key_service import APIKeyService
from backend.memory_service import MemoryService
from backend.server_config import ServerConfig


@pytest.fixture
def memory_service():
    return MemoryService()


@pytest.fixture
def api_key_service(memory_service):
    return APIKeyService(memory_service)


def test_store_and_retrieve_api_key(api_key_service):
    server_config = ServerConfig(
        server_id="test_server",
        api_key="test_api_key",  # Provide a valid API key for the test
        dm_roll_visibility="public",
        player_roll_mode="manual_physical_total",
        character_sheet_mode="digital_sheet"
    )
    api_key_service.store_api_key(server_config)

    retrieved_key = api_key_service.retrieve_api_key("test_server")
    assert retrieved_key == "test_api_key"  # Compare with the decrypted value


def test_store_empty_api_key(api_key_service):
    server_config = ServerConfig(
        server_id="test_server",
        api_key="",  # Test with an empty API key
        dm_roll_visibility="public",  # Provide required fields
        player_roll_mode="manual_physical_total",
        character_sheet_mode="digital_sheet"
    )

    with pytest.raises(ValueError, match="API key must not be empty."):
        api_key_service.store_api_key(server_config)


def test_retrieve_nonexistent_api_key(api_key_service):
    retrieved_key = api_key_service.retrieve_api_key("nonexistent_server")
    assert retrieved_key is None
