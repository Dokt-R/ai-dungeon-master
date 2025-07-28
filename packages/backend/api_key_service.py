from typing import Optional
from backend.server_config import ServerConfig
from backend.server_settings_manager import ServerSettingsManager
from cryptography.fernet import Fernet

# Generate a key for encryption and decryption
# In a real application, this key should be securely stored and managed
key = Fernet.generate_key()
cipher_suite = Fernet(key)


class APIKeyService:
    def __init__(self, memory_service: ServerSettingsManager):
        self.memory_service = memory_service

    def store_api_key(self, server_config: ServerConfig) -> None:
        """Store the API key for a specific server."""
        if not server_config.api_key.get_secret_value():
            raise ValueError("API key must not be empty.")
        """Store the API key for a specific server."""
        # The API key validation is handled by Pydantic's SecretStr
        encrypted_api_key = self.encrypt_api_key(
            server_config.api_key.get_secret_value()  # This remains unchanged
        )
        self.memory_service.store_api_key(server_config.server_id, encrypted_api_key)

    def retrieve_api_key(self, server_id: str) -> Optional[str]:
        """Retrieve the API key for a specific server."""
        encrypted_api_key = self.memory_service.retrieve_api_key(server_id)
        if encrypted_api_key:
            return self.decrypt_api_key(encrypted_api_key)
        return None

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt the API key before storing it."""
        encrypted_api_key = cipher_suite.encrypt(api_key.encode())
        return encrypted_api_key.decode()  # Return as string

    def decrypt_api_key(self, encrypted_api_key: str) -> str:
        """Decrypt the API key when retrieving it."""
        decrypted_api_key = cipher_suite.decrypt(encrypted_api_key.encode())
        return decrypted_api_key.decode()  # Return as string
