def create_campaign_autosaves_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS CampaignAutosaves (
            autosave_id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            state TEXT,
            autosave_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES Campaigns(campaign_id)
        )
        """
    )
