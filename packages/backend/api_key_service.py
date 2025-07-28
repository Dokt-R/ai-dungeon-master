from typing import Optional
from packages.backend.server_config import ServerConfig
from .memory_service import (
    MemoryService  # Assuming MemoryService is defined in memory_service.py
)


class APIKeyService:
    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service

    def store_api_key(self, server_config: ServerConfig) -> None:
        """Store the API key for a specific server."""
        if not server_config.api_key.get_secret_value():
            raise ValueError("API key must not be empty.")
        """Store the API key for a specific server."""
        self.memory_service.save(
            server_config.server_id,
            server_config.api_key.get_secret_value()
        )

    def retrieve_api_key(self, server_id: str) -> Optional[str]:
        """Retrieve the API key for a specific server."""
        return self.memory_service.get(server_id)
    