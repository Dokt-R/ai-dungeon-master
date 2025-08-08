import os
from typing import Optional

from cryptography.fernet import Fernet
from pydantic import SecretStr
from dotenv import load_dotenv
from sqlmodel import Session, select
from fastapi import Depends

from packages.shared.db import get_session
from packages.shared.models import Server

load_dotenv()


class ServerSettingsManager:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session
        self.key = self._load_encryption_key()

    def store_server_config(self, config: Server) -> None:
        """Store or update the server configuration, including the encrypted API key."""
        if not config.api_key.get_secret_value():
            raise ValueError("API key must not be empty.")

        encrypted_key = self._encrypt(config.api_key.get_secret_value())

        db_config = self.session.get(Server, config.server_id)
        if not db_config:
            db_config = Server(server_id=config.server_id)

        db_config.dm_roll_visibility = config.dm_roll_visibility
        db_config.player_roll_mode = config.player_roll_mode
        db_config.character_sheet_mode = config.character_sheet_mode
        db_config.api_key = encrypted_key

        self.session.add(db_config)
        self.session.commit()

    def retrieve_api_key(self, server_id: str) -> Optional[str]:
        """Retrieve and decrypt the API key for the given server ID."""
        config = self.session.get(Server, server_id)
        if config and config.api_key:
            return self._decrypt(config.api_key)
        return None

    def get_server_config(self, server_id: str) -> Optional[Server]:
        """Retrieve the full server configuration for the given server ID."""
        config = self.session.get(Server, server_id)
        if config and config.api_key:
            decrypted_key = self._decrypt(config.api_key)
            config.api_key = SecretStr(decrypted_key)
        return config

    # --- Internal logic ---

    def _load_encryption_key(self) -> bytes:
        """
        Load the encryption key from an environment variable.
        If not found, generate a new one and save it to the .env file for persistence.
        !!! For production environment secrets should be managed by a dedicated system. !!!
        """
        key = os.getenv("ENCRYPTION_KEY")
        if key:
            return key.encode()

        print("ENCRYPTION_KEY not found. Generating a new key...")
        new_key = Fernet.generate_key()
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
        with open(env_path, "a") as f:
            f.write(f"\nENCRYPTION_KEY={new_key.decode()}\n")
        print(f"A new ENCRYPTION_KEY has been generated and saved to {env_path}")
        os.environ["ENCRYPTION_KEY"] = new_key.decode()
        return new_key

    def _encrypt(self, data: str) -> str:
        """Encrypt the data using the Fernet encryption."""
        fernet = Fernet(self.key)
        return fernet.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt the data using the Fernet encryption."""
        fernet = Fernet(self.key)
        return fernet.decrypt(encrypted_data.encode()).decode()
