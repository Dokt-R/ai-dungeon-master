def create_campaign_players_table(conn):
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
        FOREIGN KEY (character_id) REFERENCES Characters(character_id) ON DELETE SET NULL,
        UNIQUE(campaign_id, player_id)
    )
    """
    )
