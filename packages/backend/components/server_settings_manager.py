from typing import Optional
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import sqlite3
from packages.shared.db import get_connection, get_db_path, setup_db_for_manager
from packages.backend.db.init_db import initialize_schema

load_dotenv()  # Load environment variables from .env file


class ServerSettingsManager:
    def __init__(self, db_path: str = None):
        self.key = self.load_encryption_key()
        self.db_path = db_path or get_db_path
        #! Uncomment to try and centralize memory logic
        # self._conn = setup_db_for_manager(self.db_path)
        #! Comment bellow for the centralized memory
        # For in-memory DB, keep a persistent connection
        if self.db_path == ":memory:":
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
        #! HERE

    # --- Campaign Management Methods ---

    def delete_campaign(
        self, server_id: str, campaign_name: str, requester_id: str, is_admin: bool
    ):
        """
        Delete a campaign and all related data if the requester is the owner or an admin.
        Raises ValueError if not permitted or campaign does not exist.
        """
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                # Get campaign info
                cur = conn.cursor()
                cur.execute(
                    "SELECT campaign_id, owner_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?",
                    (server_id, campaign_name),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(
                        f"No campaign named '{campaign_name}' exists on this server."
                    )
                campaign_id, owner_id = row
                if not (is_admin or requester_id == owner_id):
                    raise PermissionError(
                        "Only the campaign owner or a server admin can delete this campaign."
                    )
                # Delete autosaves
                cur.execute(
                    "DELETE FROM CampaignAutosaves WHERE campaign_id = ?",
                    (campaign_id,),
                )
                # Delete campaign players
                cur.execute(
                    "DELETE FROM CampaignPlayers WHERE campaign_id = ?", (campaign_id,)
                )
                # Delete campaign
                cur.execute(
                    "DELETE FROM Campaigns WHERE campaign_id = ?", (campaign_id,)
                )
        finally:
            if self.db_path != ":memory:":
                conn.close()

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
                    INSERT OR IGNORE INTO Campaigns (server_id, campaign_name, owner_id, state)
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

    # --- Autosave Methods ---

    def set_campaign_autosave(self, campaign_id: int, state: str):
        """Store an autosave for a campaign."""
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO CampaignAutosaves (campaign_id, state, autosave_time)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (campaign_id, state),
                )
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def get_latest_campaign_autosave(self, campaign_id: int):
        """Retrieve the latest autosave for a campaign."""
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT state, autosave_time FROM CampaignAutosaves
                WHERE campaign_id = ?
                ORDER BY autosave_time DESC
                LIMIT 1
                """,
                (campaign_id,),
            )
            row = cur.fetchone()
            if row:
                return {"state": row[0], "autosave_time": row[1]}
            return None
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def get_last_active_campaign(self, user_id: str):
        """Get the last active campaign for a user."""
        if self.db_path == ":memory:":
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT last_active_campaign FROM Players WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
            return None
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def get_campaign_to_continue(self, user_id: str, server_id: str):
        """
        Get the campaign and state to continue for a user:
        - If an autosave exists and is newer than last_save, return autosave.
        - Otherwise, return last clean save.
        """
        last_active_campaign = self.get_last_active_campaign(user_id)
        if not last_active_campaign:
            return None
        campaign = self.get_campaign(server_id, last_active_campaign)
        if not campaign:
            return None
        campaign_id = campaign["campaign_id"]
        last_save_time = campaign["last_save"]
        autosave = self.get_latest_campaign_autosave(campaign_id)
        if autosave and autosave["autosave_time"] > last_save_time:
            return {
                "campaign": campaign,
                "state": autosave["state"],
                "source": "autosave",
            }
        else:
            return {
                "campaign": campaign,
                "state": campaign["state"],
                "source": "save",
            }

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
