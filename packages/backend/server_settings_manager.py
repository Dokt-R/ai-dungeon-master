from pydantic import SecretStr
from typing import Dict, Optional
from backend.server_config import ServerConfig
import json
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import sqlite3

load_dotenv()  # Load environment variables from .env file


class ServerSettingsManager:
    def __init__(self, db_path: str = "server_settings.db"):
        self.key = self.load_encryption_key()
        self.db_path = db_path
        # For in-memory DB, keep a persistent connection
        if db_path == ":memory:":
            self._conn = sqlite3.connect(db_path)
            self._init_db(self._conn)
        else:
            self._conn = None
            self._init_db()

    def _init_db(self, conn=None):
        """Initialize the SQLite database and ensure the ServerAPIKeys table exists."""
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            close_conn = True
        else:
            close_conn = False
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ServerAPIKeys (
                        server_id TEXT PRIMARY KEY,
                        api_key TEXT NOT NULL
                    )
                    """
                )
        finally:
            if close_conn:
                conn.close()

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
        """Store the API key securely in SQLite."""
        encrypted_key = self.encrypt(api_key)
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO ServerAPIKeys (server_id, api_key)
                    VALUES (?, ?)
                    ON CONFLICT(server_id) DO UPDATE SET api_key=excluded.api_key
                    """,
                    (server_id, encrypted_key),
                )
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def retrieve_api_key(self, server_id: str) -> Optional[str]:
        """Retrieve the API key for the given server ID from SQLite."""
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT api_key FROM ServerAPIKeys WHERE server_id = ?",
                (server_id,),
            )
            row = cur.fetchone()
            if row:
                encrypted_key = row[0]
                return self.decrypt(encrypted_key)
            return None
        finally:
            if self.db_path != ":memory:":
                conn.close()
