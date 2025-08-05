def create_players_table(conn):
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
