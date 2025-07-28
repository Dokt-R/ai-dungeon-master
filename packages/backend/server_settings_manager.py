from pydantic import SecretStr
from typing import Dict, Optional
from backend.server_config import ServerConfig
import json
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


class ServerSettingsManager:
    def __init__(self):
        self.storage: Dict[str, ServerConfig] = {}
        self.key = self.load_encryption_key()

    def load_encryption_key(self) -> bytes:
        """Load the encryption key from an environment variable
        or generate a new one."""
        key = os.getenv("ENCRYPTION_KEY")
        if key is None:
            key = Fernet.generate_key()
            os.environ["ENCRYPTION_KEY"] = key.decode()
        return key  # Return the key directly as it is already in bytes

    def encrypt(self, data: str) -> str:
        """Encrypt the data using the Fernet encryption."""
        fernet = Fernet(self.key)
        return fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt the data using the Fernet encryption."""
        fernet = Fernet(self.key)
        return fernet.decrypt(encrypted_data.encode()).decode()

    def store_api_key(self, server_id: str, api_key: str) -> None:
        """Store the API key securely."""
        encrypted_key = self.encrypt(api_key)
        self.storage[server_id] = ServerConfig(
            server_id=server_id, api_key=SecretStr(encrypted_key)
        )

    def retrieve_api_key(self, server_id: str) -> Optional[str]:
        """Retrieve the API key for the given server ID."""
        config = self.storage.get(server_id)
        if config:
            return self.decrypt(config.api_key.get_secret_value())
        return None

    # TODO: This should probably be change to us SQLite later
    def save_to_file(self, filename: str) -> None:
        """Save the storage to a JSON file."""
        with open(filename, "w") as f:
            json.dump(
                {
                    server_id: config.dict()
                    for server_id, config in self.storage.items()
                },
                f,
            )

    def load_from_file(self, filename: str) -> None:
        """Load the storage from a JSON file."""
        if os.path.exists(filename):
            with open(filename, "r") as f:
                data = json.load(f)
                for server_id, config in data.items():
                    self.storage[server_id] = ServerConfig(**config)


# Example usage
if __name__ == "__main__":
    service = ServerSettingsManager()
    service.store_api_key("12345", "my_secret_api_key")
    print(service.retrieve_api_key("12345"))
