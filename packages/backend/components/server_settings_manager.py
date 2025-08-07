from typing import Optional
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import sqlite3
from packages.shared.db import get_connection, get_db_path, setup_db_for_manager
from packages.backend.db.init_db import initialize_schema
from packages.shared.models import ServerConfig


load_dotenv()  # Load environment variables from .env file


class ServerSettingsManager:
    def __init__(self, db_path: str = None, persistent_conn=None):
        self.key = self.load_encryption_key()
        self.db_path = db_path or get_db_path()
        #! Uncomment to try and centralize memory logic
        # self._conn = setup_db_for_manager(self.db_path)
        #! Comment bellow for the centralized memory
        # For in-memory DB, keep a persistent connection
        if db_path:
            self._conn = get_connection(db_path)
            self._init_db(self._conn)
        else:
            self._conn = None
            self._init_db()

    def _init_db(self, conn=None):
        """Initialize the SQLite database and ensure that all tables exists."""
        if conn is None:
            with get_connection(self.db_path) as conn:
                initialize_schema(conn)
        else:
            initialize_schema(conn)

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

    def store_api_key(self, server_config: ServerConfig) -> None:
        """Store the API key securely in SQLite."""
        if not server_config.api_key.get_secret_value():
            raise ValueError("API key must not be empty.")
        server_id = server_config.server_id
        api_key = server_config.api_key.get_secret_value()
        print(api_key)
        encrypted_key = self.encrypt(api_key)
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO Keys (server_id, api_key)
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
                "SELECT api_key FROM Keys WHERE server_id = ?",
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
