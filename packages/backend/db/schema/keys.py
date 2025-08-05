def create_keys_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS Keys (
            server_id TEXT PRIMARY KEY,
            api_key TEXT NOT NULL
        )
        """
    )
