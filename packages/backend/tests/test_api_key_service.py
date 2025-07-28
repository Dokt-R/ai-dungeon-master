import pytest
from pydantic import SecretStr
from packages.backend.api_key_service import APIKeyService
from packages.backend.server_config import ServerConfig
# from packages.backend.memory_service import MemoryService


class MockMemoryService:
    def __init__(self):
        self.store = {}

    def save(self, server_id, api_key):
        self.store[server_id] = api_key

    def get(self, server_id):
        return self.store.get(server_id)


def test_store_api_key():
    memory_service = MockMemoryService()
    api_key_service = APIKeyService(memory_service)
    server_config = ServerConfig(
        server_id="123",
        api_key=SecretStr("my_secret_key"),
        dm_roll_visibility="public",
        player_roll_mode="manual_physical_total",
        character_sheet_mode="digital_sheet"
    )

    api_key_service.store_api_key(server_config)
    assert memory_service.get("123") == "my_secret_key"


def test_store_empty_api_key():
    memory_service = MockMemoryService()
    api_key_service = APIKeyService(memory_service)
    server_config = ServerConfig(
        server_id="123",
        api_key=SecretStr(""),
        dm_roll_visibility="public",
        player_roll_mode="manual_physical_total",
        character_sheet_mode="digital_sheet"
    )

    with pytest.raises(ValueError, match="API key must not be empty."):
        api_key_service.store_api_key(server_config)


def test_retrieve_api_key():
    memory_service = MockMemoryService()
    api_key_service = APIKeyService(memory_service)
    server_config = ServerConfig(
        server_id="123",
        api_key=SecretStr("my_secret_key"),
        dm_roll_visibility="public",
        player_roll_mode="manual_physical_total",
        character_sheet_mode="digital_sheet"
    )

    api_key_service.store_api_key(server_config)
    retrieved_key = api_key_service.retrieve_api_key("123")
    assert retrieved_key == "my_secret_key"

