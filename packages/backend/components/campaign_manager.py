import sqlite3
from packages.backend.db.init_db import initialize_schema
from packages.shared.db import get_connection, get_db_path


class CampaignManager:
    def __init__(self, db_path: str = None):
        """
        Initialize the CampaignManager.

        Args:
            db_path (str, optional): Path to the SQLite database file. If None, uses the DB_PATH
                environment variable or defaults to 'server_settings.db'.
        """
        self.db_path = db_path or get_db_path()
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

    # --- Campaign Management Methods ---

    def get_campaign(self, server_id: str, campaign_name: str):
        """Retrieve a campaign by server_id and campaign_name."""
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

    def create_campaign(self, server_id: str, campaign_name: str, owner_id: str, state: str = None):
        """Create a new campaign in the Campaigns table."""
        
        if self.get_campaign(server_id, campaign_name):
            raise ValueError(f"A campaign named '{campaign_name}' already exists.")
        
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

    # All player join/end logic is now handled by PlayerManager.
    # Only campaign creation and retrieval remain here.

    def continue_campaign(self, user_id: str, server_id: str):
        """
        Returns a dict with:
            - campaign: campaign info
            - state: state to restore (autosave if newer, else last clean save)
            - source: 'autosave' or 'save'
        """
        return self.get_campaign_to_continue(user_id, server_id)

    def delete_campaign(
        self, server_id: str, campaign_name: str, requester_id: str, is_admin: bool
    ):
        """
        Delete a campaign if the requester is the owner or an admin.
        Raises ValueError or PermissionError if not permitted.
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

    def get_campaign_id(self, campaign_name: str):
        """
        Retrieve campaign_id for a given campaign_name.

        Args:
            campaign_name (str): Unique name for the campaign.

        Returns:
            campaign_id
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT campaign_id FROM Campaigns WHERE campaign_name = ?",
                (campaign_name,),
            )
            row = cur.fetchone()
            return row[0]
        finally:
            conn.close()

    def get_campaign_players(self, campaign_name: str):
        """
        Retrieve all players for a given campaign name.

        Args:
            player_id (str): Unique identifier for the player.

        Returns:
            list of dict: Each dict contains 'character_id', 'name', and 'dnd_beyond_url'.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            campaign_id = self.get_campaign_id(campaign_name)
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM CampaignPlayers WHERE campaign_id = ?",
                (campaign_id,),
            )
            rows = cur.fetchall()
            return [
                {"id": row[0],
                "campaign_id": row[1],
                "player_id": row[2],
                "character_id": row[3],
                "player_status": row[4],
                "joined_at": row[5]
                }
                for row in rows
            ]
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
        print(campaign)
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