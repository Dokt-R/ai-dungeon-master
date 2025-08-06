import sqlite3
from packages.shared.db import get_connection, get_db_path
from packages.backend.db.init_db import initialize_schema
from packages.shared.error_handler import ValidationError, NotFoundError
from packages.backend.components.campaign_manager import CampaignManager


class PlayerManager:
    """
    Manages player participation, campaign membership, and character associations.

    Handles player joining, leaving, and ending campaigns, as well as retrieving player status.
    Interacts with the database to enforce campaign membership rules and maintain player state.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize the PlayerManager.

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

    def join_campaign(
        self,
        player_id: str,
        server_id: str,
        username: str = None,
        campaign_name: str = None,
        character_name: str = None,
        dnd_beyond_url: str = None,
    ):
        """
        Join a campaign as a player, optionally associating a character.

        If `campaign_name` is None, uses the player's last active campaign.
        Enforces that a player can only be 'joined' to one campaign per server at a time.
        Updates the player's last active campaign on join.

        Args:
            player_id (str): Unique identifier for the player.
            server_id (str): Unique identifier for the server.
            campaign_name (str, optional): Name of the campaign to join. If None, uses last active campaign.
            username (str, optional): Username of the player (used if creating a new player).
            character_name (str, optional): Name of the character to associate with the campaign.
            dnd_beyond_url (str, optional): D&D Beyond URL for the character.

        Returns:
            dict: Information about the joined campaign, player, and character.

        Raises:
            NotFoundError: If the specified campaign or last active campaign does not exist.
            ValidationError: If no campaign is specified and no last active campaign is found,
                or if the player is already joined to an active campaign on this server.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            # Ensure player exists
            cur.execute(
                "SELECT user_id, last_active_campaign FROM Players WHERE user_id = ?",
                (player_id,),
            )
            player_row = cur.fetchone()

            if not player_row:
                cur.execute(
                    "INSERT INTO Players (user_id, username) VALUES (?, ?)",
                    (player_id, username),
                )
                last_active_campaign = None
            else:
                last_active_campaign = player_row[1]

            # Determine campaign to join
            if campaign_name:
                cur.execute(
                    "SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?",
                    (server_id, campaign_name),
                )
                campaign_row = cur.fetchone()
                if not campaign_row:
                    raise NotFoundError(
                        f"Campaign '{campaign_name}' does not exist on server '{server_id}'"
                    )
                campaign_id = campaign_row[0]
            else:
                # Use last_active_campaign
                if not last_active_campaign:
                    raise NotFoundError(
                        "No campaign specified and no last active campaign found for player."
                    )
                campaign_id = last_active_campaign
                cur.execute(
                    "SELECT campaign_name FROM Campaigns WHERE campaign_id = ? AND server_id = ?",
                    (campaign_id, server_id),
                )
                row = cur.fetchone()
                if not row:
                    raise NotFoundError(
                        f"Last active campaign (ID: {campaign_id}) not found on server '{server_id}'."
                    )
                campaign_name = row[0]

            # Enforce only one joined campaign per player
            #! Could later be refactored to auto update last campaign to unjoined and new to join
            cur.execute(
                """
                SELECT cp.id FROM CampaignPlayers cp
                JOIN Campaigns c ON cp.campaign_id = c.campaign_id
                WHERE cp.player_id = ? AND cp.player_status = 'joined' AND c.server_id = ?
                """,
                (player_id, server_id),
            )
            if cur.fetchone():
                raise ValidationError(
                    "Player is already joined to an active campaign on this server."
                )

            # Ensure character exists if provided
            character_id = None
            if character_name:
                cur.execute(
                    "SELECT character_id FROM Characters WHERE player_id = ? AND name = ?",
                    (player_id, character_name),
                )
                char_row = cur.fetchone()
                if char_row:
                    character_id = char_row[0]
                else:
                    cur.execute(
                        "INSERT INTO Characters (player_id, name, dnd_beyond_url) VALUES (?, ?, ?)",
                        (player_id, character_name, dnd_beyond_url),
                    )
                    character_id = cur.lastrowid
            else: # If a player has a character and its not provided auto use that character
                cur.execute(
                    "SELECT character_id FROM Characters WHERE player_id = ?",
                    (player_id,),
                )
                char_row = cur.fetchall()
                
                # Enforce the player to select character if he has multiple
                if len(char_row) > 1:
                    raise ValidationError(
                        "Player has multiple characters. Please specify which character should join the campaign"
                    )
                
                if not char_row:
                    raise NotFoundError(
                        "Player does not have any characters created. Specify character name or create a character before joining"
                    )
                
                character_id = char_row[0][0]

            # Add player to campaign
            cur.execute(
                """
                INSERT INTO CampaignPlayers (campaign_id, player_id, character_id, player_status)
                VALUES (?, ?, ?, 'joined')
                ON CONFLICT(campaign_id, player_id) DO UPDATE SET character_id=excluded.character_id, player_status='joined'
                """,
                (campaign_id, player_id, character_id),
            )

            # Update last_active_campaign
            cur.execute(
                "UPDATE Players SET last_active_campaign = ? WHERE user_id = ?",
                (campaign_id, player_id),
            )

            conn.commit()
            return {
                "campaign_name": campaign_name,
                "player_id": player_id,
                "character_id": character_id,
                "status": "joined",
            }
        finally:
            conn.close()

    def continue_campaign(
        self,
        player_id: str,
    ):
        """
        Continue the last active campaign as a player.

        Args:
            player_id (str): Unique identifier for the player.
            server_id (str): Unique identifier for the server.
            campaign_name (str, optional): Name of the campaign to join. If None, uses last active campaign.
            username (str, optional): Username of the player (used if creating a new player).
            character_name (str, optional): Name of the character to associate with the campaign.
            dnd_beyond_url (str, optional): D&D Beyond URL for the character.

        Returns:
            dict: Information about the joined campaign, player, and character.

        Raises:
            NotFoundError: If the specified campaign or last active campaign does not exist.
            ValidationError: If no campaign is specified and no last active campaign is found,
                or if the player is already joined to an active campaign on this server.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            # Ensure player exists
            cur.execute(
                "SELECT last_active_campaign FROM Players WHERE user_id = ?",
                (player_id,),
            )
            last_campaign_row = cur.fetchone()
            if not last_campaign_row:
                raise ValidationError(
                    "No last active campaign found for player. Please join an active campaign by using /campaign join command"
                )
            else:
                last_active_campaign = last_campaign_row[1]

            cur.execute(
                "SELECT campaign_name FROM Campaigns WHERE campaign_id = ?",
                (last_active_campaign),
            )
            row = cur.fetchone()
            if not row:
                raise NotFoundError(
                    f"Last active campaign (ID: {last_active_campaign}) not found on server'."
                )
            campaign_name = row[0]

            # Fetch character
            character_id = None

            cur.execute(
                """
                SELECT c.character_id FROM Characters c
                INNER JOIN players p ON p.user_id=c.player_id
                WHERE p.player_id = ? AND p.last_active_campaign = ?
                """,
                (player_id, last_active_campaign),
            )

            char_row = cur.fetchone()
            if not char_row:
                raise NotFoundError(
                    f"No active characters inside the campaign {last_active_campaign}. Please create a character and then join the campaign via the /campaign join command'."
                )
            character_id = char_row[0]

            # Add player to campaign
            cur.execute(
                """
                INSERT INTO CampaignPlayers (campaign_id, player_id, character_id, player_status)
                VALUES (?, ?, ?, 'joined')
                ON CONFLICT(campaign_id, player_id) DO UPDATE SET character_id=excluded.character_id, player_status='joined'
                """,
                (last_active_campaign, player_id, character_id),
            )

            conn.commit()
            return {
                "campaign_name": campaign_name,
                "player_id": player_id,
                "character_id": character_id,
                "status": "joined",
            }
        finally:
            conn.close()

    def end_campaign(self, player_id: str, server_id: str, campaign_name: str = None):
        """
        End a campaign for a player by setting their status to 'cmd' (command state).
        Also autosaves the current campaign state.

        If `campaign_name` is None, uses the player's last active campaign.

        Args:
            player_id (str): Unique identifier for the player.
            server_id (str): Unique identifier for the server.
            campaign_name (str, optional): Name of the campaign to end. If None, uses last active campaign.

        Returns:
            dict: Information about the ended campaign and player status.

        Raises:
            NotFoundError: If the specified campaign or last active campaign does not exist.
            ValidationError: If no campaign is specified and no last active campaign is found.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            # Determine campaign to end
            if campaign_name:
                cur.execute(
                    "SELECT campaign_id, state FROM Campaigns WHERE server_id = ? AND campaign_name = ?",
                    (server_id, campaign_name),
                )
                campaign_row = cur.fetchone()
                if not campaign_row:
                    raise NotFoundError(
                        f"Campaign '{campaign_name}' does not exist on server '{server_id}'"
                    )
                campaign_id = campaign_row[0]
                campaign_state = campaign_row[1]
            else:
                cur.execute(
                    "SELECT last_active_campaign FROM Players WHERE user_id = ?",
                    (player_id,),
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    raise ValidationError(
                        "No campaign specified and no last active campaign found for player."
                    )
                campaign_id = row[0]
                cur.execute(
                    "SELECT campaign_name, state FROM Campaigns WHERE campaign_id = ? AND server_id = ?",
                    (campaign_id, server_id),
                )
                name_row = cur.fetchone()
                if not name_row:
                    raise NotFoundError(
                        f"Last active campaign (ID: {campaign_id}) not found on server '{server_id}'."
                    )
                campaign_name = name_row[0]
                campaign_state = name_row[1]

            # AUTOSAVE: Store the current campaign state as an autosave
            cm = CampaignManager(db_path=self.db_path)
            cm.set_campaign_autosave(
                int(campaign_id), campaign_state if campaign_state is not None else ""
            )

            # Set player_status to 'cmd'
            cur.execute(
                """
                UPDATE CampaignPlayers
                SET player_status = 'cmd'
                WHERE campaign_id = ? AND player_id = ?
                """,
                (campaign_id, player_id),
            )
            conn.commit()

            # Placeholder: Update only the allowed sections of the story file per the develop-story workflow
            # (This should be implemented in a dedicated service or as a separate step.)

            return {
                "campaign_name": campaign_name,
                "player_id": player_id,
                "player_status": "cmd",
                "autosave": True,
            }
        finally:
            conn.close()

    def leave_campaign(self, player_id: str, server_id: str, campaign_name: str = None):
        """
        Remove a player from a campaign (deletes from CampaignPlayers).

        If `campaign_name` is None, uses the player's last active campaign.
        If the player leaves their last active campaign, clears last_active_campaign.

        Args:
            player_id (str): Unique identifier for the player.
            server_id (str): Unique identifier for the server.
            campaign_name (str, optional): Name of the campaign to leave. If None, uses last active campaign.

        Returns:
            dict: Information about the campaign left and player.

        Raises:
            NotFoundError: If the specified campaign or last active campaign does not exist.
            ValidationError: If no campaign is specified and no last active campaign is found.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            # Determine campaign to leave
            if campaign_name:
                cur.execute(
                    "SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?",
                    (server_id, campaign_name),
                )
                campaign_row = cur.fetchone()
                if not campaign_row:
                    raise NotFoundError(
                        f"Campaign '{campaign_name}' does not exist on server '{server_id}'"
                    )
                campaign_id = campaign_row[0]
            else:
                cur.execute(
                    "SELECT last_active_campaign FROM Players WHERE user_id = ?",
                    (player_id,),
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    raise ValidationError(
                        "No campaign specified and no last active campaign found for player."
                    )
                campaign_id = row[0]
                cur.execute(
                    "SELECT campaign_name FROM Campaigns WHERE campaign_id = ? AND server_id = ?",
                    (campaign_id, server_id),
                )
                name_row = cur.fetchone()
                if not name_row:
                    raise NotFoundError(
                        f"Last active campaign (ID: {campaign_id}) not found on server '{server_id}'."
                    )
                campaign_name = name_row[0]

            # Delete player from campaign
            cur.execute(
                "DELETE FROM CampaignPlayers WHERE campaign_id = ? AND player_id = ?",
                (campaign_id, player_id),
            )
            # Optionally, clear last_active_campaign if it matches
            cur.execute(
                "SELECT last_active_campaign FROM Players WHERE user_id = ?",
                (player_id,),
            )
            row = cur.fetchone()
            if row and str(row[0]) == str(campaign_id):
                cur.execute(
                    "UPDATE Players SET last_active_campaign = NULL WHERE user_id = ?",
                    (player_id,),
                )
            conn.commit()
            return {
                "campaign_name": campaign_name,
                "player_id": player_id,
                "status": "left",
            }
        finally:
            conn.close()

    def get_player_status(self, player_id: str):
        """
        Retrieve a summary of the player's campaigns, characters, and current status.

        Args:
            player_id (str): Unique identifier for the player.

        Returns:
            dict: Player information, including username, last active campaign, list of campaigns
                (with status), and all characters.

        Raises:
            NotFoundError: If the player does not exist.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            # Get player info
            cur.execute(
                "SELECT username, last_active_campaign FROM Players WHERE user_id = ?",
                (player_id,),
            )
            player_row = cur.fetchone()
            if not player_row:
                raise NotFoundError(f"Player with ID '{player_id}' not found.")
            username, last_active_campaign = player_row

            # Get campaigns player is/was in
            cur.execute(
                """
                SELECT c.campaign_name, cp.player_status
                FROM CampaignPlayers cp
                JOIN Campaigns c ON cp.campaign_id = c.campaign_id
                WHERE cp.player_id = ?
                """,
                (player_id,),
            )
            campaigns = [
                {"campaign_name": row[0], "player_status": row[1]}
                for row in cur.fetchall()
            ]

            # Get all characters for player
            cur.execute(
                "SELECT character_id, name, dnd_beyond_url FROM Characters WHERE player_id = ?",
                (player_id,),
            )
            characters = [
                {"character_id": row[0], "name": row[1], "dnd_beyond_url": row[2]}
                for row in cur.fetchall()
            ]

            return {
                "player_id": player_id,
                "username": username,
                "last_active_campaign": last_active_campaign,
                "campaigns": campaigns,
                "characters": characters,
            }
        finally:
            conn.close()
