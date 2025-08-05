def create_characters_table(conn):
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
