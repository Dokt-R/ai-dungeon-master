def create_campaigns_table(conn):
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
