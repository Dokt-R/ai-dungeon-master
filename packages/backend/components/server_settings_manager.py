from typing import Optional
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import sqlite3

load_dotenv()  # Load environment variables from .env file


class ServerSettingsManager:
    def __init__(self, db_path: str = None):
        import os

        if db_path is None:
            db_path = os.environ.get("DB_PATH", "server_settings.db")
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
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS Players (
                        user_id TEXT PRIMARY KEY,
                        username TEXT,
                        last_active_campaign TEXT,
                        FOREIGN KEY (last_active_campaign) REFERENCES Campaigns(campaign_name)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS Characters (
                        character_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        player_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        dnd_beyond_url TEXT,
                        FOREIGN KEY (player_id) REFERENCES Players(user_id),
                        UNIQUE(player_id, name)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS Campaigns (
                        campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        server_id TEXT NOT NULL,
                        campaign_name TEXT NOT NULL,
                        owner_id TEXT NOT NULL,
                        state TEXT,
                        last_save TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(server_id, campaign_name)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS CampaignPlayers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        campaign_id INTEGER NOT NULL,
                        player_id TEXT NOT NULL,
                        character_id INTEGER,
                        player_status TEXT CHECK(player_status IN ('joined', 'cmd')) NOT NULL DEFAULT 'joined',
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (campaign_id) REFERENCES Campaigns(campaign_id),
                        FOREIGN KEY (player_id) REFERENCES Players(user_id),
                        FOREIGN KEY (character_id) REFERENCES Characters(character_id),
                        UNIQUE(campaign_id, player_id)
                    )
                    """
                )
        finally:
            if close_conn:
                conn.close()

    # --- Campaign Management Methods ---

    def create_campaign(
        self, server_id: str, campaign_name: str, owner_id: str, state: str = None
    ):
        """Create a new campaign in the Campaigns table."""
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO Campaigns (server_id, campaign_name, owner_id, state)
                    VALUES (?, ?, ?, ?)
                    """,
                    (server_id, campaign_name, owner_id, state),
                )
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def get_campaign(self, server_id: str, campaign_name: str):
        """Retrieve a campaign by server_id and campaign_name."""
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT campaign_id, server_id, campaign_name, owner_id, state, last_save FROM Campaigns WHERE server_id = ? AND campaign_name = ?",
                (server_id, campaign_name),
            )
            row = cur.fetchone()
            if row:
                return {
                    "campaign_id": row[0],
                    "server_id": row[1],
                    "campaign_name": row[2],
                    "owner_id": row[3],
                    "state": row[4],
                    "last_save": row[5],
                }
            return None
        finally:
            if self.db_path != ":memory:":
                conn.close()

    # All player join/end/status logic is now handled by PlayerManager.

    def get_campaign_players(self, campaign_id: int):
        """Get all players in a campaign."""
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT player_id, character_name, joined_at FROM CampaignPlayers WHERE campaign_id = ?",
                (campaign_id,),
            )
            return cur.fetchall()
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def update_campaign_state(self, campaign_id: int, state: str):
        """Update the state and last_save of a campaign."""
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE Campaigns SET state = ?, last_save = CURRENT_TIMESTAMP WHERE campaign_id = ?
                    """,
                    (state, campaign_id),
                )
        finally:
            if self.db_path != ":memory:":
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
