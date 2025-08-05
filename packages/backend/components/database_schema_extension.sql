-- SQL command to extend the SQLite schema for server-to-API-key mapping
CREATE TABLE Keys (
    server_id TEXT PRIMARY KEY,
    api_key TEXT NOT NULL
);