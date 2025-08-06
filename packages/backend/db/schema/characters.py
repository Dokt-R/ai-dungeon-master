def create_characters_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS Characters (
            character_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL,
            name TEXT NOT NULL,
            dnd_beyond_url TEXT,
            campaign_id INTEGER,
            FOREIGN KEY (player_id) REFERENCES Players(user_id),
            FOREIGN KEY (campaign_id) REFERENCES Campaigns(campaign_id),
            UNIQUE(player_id, name)
        )
        """
    )
