import sqlite3


class PlayerManager:
    def __init__(self, db_path: str = "server_settings.db"):
        self.db_path = db_path

    def join_campaign(
        self,
        player_id: str,
        server_id: str,
        campaign_name: str = None,
        username: str = None,
        character_name: str = None,
        dnd_beyond_url: str = None,
    ):
        """
        Join a campaign. If campaign_name is None, use last_active_campaign.
        Enforces only one 'joined' campaign per player at a time.
        Updates last_active_campaign on join.
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
                    raise ValueError(
                        f"Campaign '{campaign_name}' does not exist on server '{server_id}'"
                    )
                campaign_id = campaign_row[0]
            else:
                # Use last_active_campaign
                if not last_active_campaign:
                    raise ValueError(
                        "No campaign specified and no last active campaign found for player."
                    )
                campaign_id = last_active_campaign
                cur.execute(
                    "SELECT campaign_name FROM Campaigns WHERE campaign_id = ? AND server_id = ?",
                    (campaign_id, server_id),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Last active campaign not found on this server.")
                campaign_name = row[0]

            # Enforce only one joined campaign per player
            cur.execute(
                """
                SELECT cp.id FROM CampaignPlayers cp
                JOIN Campaigns c ON cp.campaign_id = c.campaign_id
                WHERE cp.player_id = ? AND cp.player_status = 'joined' AND c.server_id = ?
                """,
                (player_id, server_id),
            )
            if cur.fetchone():
                raise ValueError(
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

    def end_campaign(self, player_id: str, server_id: str, campaign_name: str = None):
        """
        End a campaign for a player (set status to 'cmd').
        If campaign_name is None, use last_active_campaign.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            # Determine campaign to end
            if campaign_name:
                cur.execute(
                    "SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?",
                    (server_id, campaign_name),
                )
                campaign_row = cur.fetchone()
                if not campaign_row:
                    raise ValueError(
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
                    raise ValueError(
                        "No campaign specified and no last active campaign found for player."
                    )
                campaign_id = row[0]
                cur.execute(
                    "SELECT campaign_name FROM Campaigns WHERE campaign_id = ? AND server_id = ?",
                    (campaign_id, server_id),
                )
                name_row = cur.fetchone()
                if not name_row:
                    raise ValueError("Last active campaign not found on this server.")
                campaign_name = name_row[0]

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
            return {
                "campaign_name": campaign_name,
                "player_id": player_id,
                "player_status": "cmd",
            }
        finally:
            conn.close()
