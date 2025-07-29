from typing import Optional
from packages.shared.models import ServerConfig
from packages.backend.components.server_settings import ServerSettingsManager


class APIKeyService:
    def __init__(self, memory_service: ServerSettingsManager):
        self.memory_service = memory_service

    def store_api_key(self, server_config: ServerConfig) -> None:
        """Store the API key for a specific server."""
        if not server_config.api_key.get_secret_value():
            raise ValueError("API key must not be empty.")
        """Store the API key for a specific server."""
        # The API key validation is handled by Pydantic's SecretStr
        self.memory_service.store_api_key(
            server_config.server_id, server_config.api_key.get_secret_value()
        )

    def retrieve_api_key(self, server_id: str) -> Optional[str]:
        """Retrieve the API key for a specific server."""
        return self.memory_service.retrieve_api_key(server_id)
