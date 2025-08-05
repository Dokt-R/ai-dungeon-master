import sqlite3
from packages.shared.db import get_connection, get_db_path, setup_db_for_manager
from packages.backend.db.init_db import initialize_schema
from packages.shared.error_handler import ValidationError, NotFoundError


class CharacterManager:
    """
    Manages character creation, updates, removal, and retrieval for players.

    Handles character uniqueness, association with players, and database operations.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize the CharacterManager.

        Args:
            db_path (str, optional): Path to the SQLite database file. Defaults to 'server_settings.db'.
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

    def add_character(self, player_id: str, name: str, dnd_beyond_url: str = None):
        """
        Add a new character for a player.

        Args:
            player_id (str): Unique identifier for the player.
            name (str): Name of the character (must be unique for the player).
            dnd_beyond_url (str, optional): D&D Beyond URL for the character.

        Returns:
            int: The character_id of the newly created character.

        Raises:
            NotFoundError: If the player does not exist.
            ValidationError: If a character with the same name already exists for the player.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            # Ensure player exists
            cur.execute(
                "SELECT user_id FROM Players WHERE user_id = ?",
                (player_id,),
            )
            if not cur.fetchone():
                raise NotFoundError(f"Player with id '{player_id}' does not exist.")
            # Insert character
            try:
                cur.execute(
                    "INSERT INTO Characters (player_id, name, dnd_beyond_url) VALUES (?, ?, ?)",
                    (player_id, name, dnd_beyond_url),
                )
            except sqlite3.IntegrityError:
                raise ValidationError(
                    f"Character with name '{name}' already exists for player '{player_id}'."
                )
            character_id = cur.lastrowid
            conn.commit()
            return character_id
        finally:
            conn.close()

    def update_character(
        self, character_id: int, name: str = None, dnd_beyond_url: str = None
    ):
        """
        Update character data by character_id.

        At least one of `name` or `dnd_beyond_url` must be provided.
        Ensures character name uniqueness for the player.

        Args:
            character_id (int): Unique identifier for the character.
            name (str, optional): New name for the character.
            dnd_beyond_url (str, optional): New D&D Beyond URL for the character.

        Returns:
            bool: True if the character was updated successfully.

        Raises:
            NotFoundError: If the character does not exist.
            ValidationError: If no update fields are provided or if the new name would violate uniqueness.
        """
        if name is None and dnd_beyond_url is None:
            raise ValidationError(
                "At least one of name or dnd_beyond_url must be provided."
            )
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            # Check if character exists
            cur.execute(
                "SELECT player_id, name FROM Characters WHERE character_id = ?",
                (character_id,),
            )
            row = cur.fetchone()
            if not row:
                raise NotFoundError(
                    f"Character with id '{character_id}' does not exist."
                )
            player_id = row[0]
            updates = []
            params = []
            if name is not None:
                # Check for uniqueness
                cur.execute(
                    "SELECT character_id FROM Characters WHERE player_id = ? AND name = ? AND character_id != ?",
                    (player_id, name, character_id),
                )
                if cur.fetchone():
                    raise ValidationError(
                        f"Character with name '{name}' already exists for player '{player_id}'."
                    )
                updates.append("name = ?")
                params.append(name)
            if dnd_beyond_url is not None:
                updates.append("dnd_beyond_url = ?")
                params.append(dnd_beyond_url)
            params.append(character_id)
            cur.execute(
                f"UPDATE Characters SET {', '.join(updates)} WHERE character_id = ?",
                params,
            )
            if cur.rowcount == 0:
                raise ValidationError(
                    f"Character with id '{character_id}' not updated. It may not exist or no changes were provided."
                )
            conn.commit()
            return True
        finally:
            conn.close()

    def remove_character(self, character_id: int):
        """
        Remove a character by character_id.

        Also sets character_id to NULL in CampaignPlayers for any affected rows.

        Args:
            character_id (int): Unique identifier for the character.

        Returns:
            bool: True if a character was deleted, False otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()

            # Delete character
            cur.execute(
                "DELETE FROM Characters WHERE character_id = ?",
                (character_id,),
            )
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        finally:
            conn.close()

    def get_characters_for_player(self, player_id: str):
        """
        Retrieve all characters for a given player.

        Args:
            player_id (str): Unique identifier for the player.

        Returns:
            list of dict: Each dict contains 'character_id', 'name', and 'dnd_beyond_url'.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT character_id, name, dnd_beyond_url FROM Characters WHERE player_id = ?",
                (player_id,),
            )
            rows = cur.fetchall()
            return [
                {"character_id": row[0], "name": row[1], "dnd_beyond_url": row[2]}
                for row in rows
            ]
        finally:
            conn.close()
