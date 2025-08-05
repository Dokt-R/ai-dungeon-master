import pytest
import sqlite3
from packages.backend.components.character_manager import CharacterManager
from packages.backend.components.server_settings_manager import ServerSettingsManager
from packages.shared.error_handler import ValidationError, NotFoundError

# Use a shared in-memory SQLite database URI for all connections
SHARED_MEM_URI = "file:memdb1?mode=memory&cache=shared"


@pytest.fixture(autouse=True)
def monkeypatch_sqlite_connect(monkeypatch):
    orig_connect = sqlite3.connect

    def connect_with_uri(db_path, *args, **kwargs):
        if db_path == SHARED_MEM_URI:
            kwargs["uri"] = True
        return orig_connect(db_path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connect_with_uri)


class PatchedServerSettingsManager(ServerSettingsManager):
    def __init__(self, db_path: str = "server_settings.db"):
        self.key = self.load_encryption_key()
        self.db_path = db_path
        if db_path == SHARED_MEM_URI:
            self._conn = sqlite3.connect(db_path, uri=True)
            self._init_db(self._conn)
        elif db_path == ":memory:":
            self._conn = sqlite3.connect(db_path)
            self._init_db(self._conn)
        else:
            self._conn = None
            self._init_db()


@pytest.fixture
def db_and_managers():
    ssm = PatchedServerSettingsManager(db_path=SHARED_MEM_URI)
    cm = CharacterManager(db_path=SHARED_MEM_URI)
    return ssm, cm


@pytest.fixture(autouse=True)
def clear_tables():
    conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
    cur = conn.cursor()
    for table in ["CampaignPlayers", "Characters", "Players", "Campaigns"]:
        try:
            cur.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


class TestCharacterManager:
    def test_add_character_normal(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        conn.commit()
        conn.close()
        char_id = cm.add_character("user1", "Hero", "http://dndbeyond.com/hero")
        assert isinstance(char_id, int)
        # DB state
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT name, dnd_beyond_url FROM Characters WHERE character_id = ?",
            (char_id,),
        )
        row = cur.fetchone()
        assert row == ("Hero", "http://dndbeyond.com/hero")
        conn.close()

    def test_add_character_missing_player(self, db_and_managers):
        ssm, cm = db_and_managers
        with pytest.raises(NotFoundError):
            cm.add_character("user2", "Hero")

    def test_add_character_duplicate_name(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        conn.commit()
        conn.close()
        cm.add_character("user1", "Hero")
        with pytest.raises(ValidationError):
            cm.add_character("user1", "Hero")

    def test_add_character_without_dnd_beyond_url(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        conn.commit()
        conn.close()
        char_id = cm.add_character("user1", "Hero")
        assert isinstance(char_id, int)
        # DB state
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT name, dnd_beyond_url FROM Characters WHERE character_id = ?",
            (char_id,),
        )
        row = cur.fetchone()
        assert row == ("Hero", None)
        conn.close()

    def test_update_character_normal(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player and character
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        cur.execute(
            "INSERT INTO Characters (player_id, name, dnd_beyond_url) VALUES (?, ?, ?)",
            ("user1", "Hero", "url1"),
        )
        char_id = cur.lastrowid
        conn.commit()
        conn.close()
        # Update name and dnd_beyond_url
        result = cm.update_character(char_id, name="Hero2", dnd_beyond_url="url2")
        assert result is True
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT name, dnd_beyond_url FROM Characters WHERE character_id = ?",
            (char_id,),
        )
        row = cur.fetchone()
        assert row == ("Hero2", "url2")
        conn.close()

    def test_update_character_no_fields(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player and character
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        cur.execute(
            "INSERT INTO Characters (player_id, name) VALUES (?, ?)", ("user1", "Hero")
        )
        char_id = cur.lastrowid
        conn.commit()
        conn.close()
        with pytest.raises(ValidationError):
            cm.update_character(char_id)

    def test_update_character_not_found(self, db_and_managers):
        ssm, cm = db_and_managers
        with pytest.raises(NotFoundError):
            cm.update_character(9999, name="NewName")

    def test_update_character_duplicate_name(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player and two characters
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        cur.execute(
            "INSERT INTO Characters (player_id, name) VALUES (?, ?)", ("user1", "Hero")
        )
        char1_id = cur.lastrowid
        cur.execute(
            "INSERT INTO Characters (player_id, name) VALUES (?, ?)", ("user1", "Hero2")
        )
        char2_id = cur.lastrowid
        conn.commit()
        conn.close()
        with pytest.raises(ValidationError):
            cm.update_character(char2_id, name="Hero")

    def test_remove_character_normal(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player and character
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        cur.execute(
            "INSERT INTO Characters (player_id, name) VALUES (?, ?)", ("user1", "Hero")
        )
        char_id = cur.lastrowid
        conn.commit()
        conn.close()
        # Remove character
        result = cm.remove_character(char_id)
        assert result is True
        # DB state
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute("SELECT * FROM Characters WHERE character_id = ?", (char_id,))
        assert cur.fetchone() is None
        conn.close()

    def test_remove_character_not_found(self, db_and_managers):
        ssm, cm = db_and_managers
        result = cm.remove_character(9999)
        assert result is False

    # @pytest.mark.skip(reason="Test logic is wrong and must be fixed.")
    def test_remove_character_sets_campaignplayers_null(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player, character, campaign, and campaignplayer
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice19")
        )
        cur.execute(
            "INSERT INTO Characters (player_id, name) VALUES (?, ?)", ("user1", "Hero")
        )
        char_id = cur.lastrowid
        cur.execute(
            "INSERT INTO Campaigns (server_id, campaign_name, owner_id) VALUES (?, ?, ?)",
            ("server1", "Epic Quest", "owner1"),
        )
        campaign_id = cur.lastrowid
        cur.execute(
            "INSERT INTO CampaignPlayers (campaign_id, player_id, character_id) VALUES (?, ?, ?)",
            (campaign_id, "user1", char_id),
        )
        conn.commit()
        conn.close()
        # Remove character
        cm.remove_character(char_id)

        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM CampaignPLayers WHERE player_id = ?", ("user1",)
        )
        row = cur.fetchone()

        assert row is not None and row[3] is None
        conn.close()

    def test_get_characters_for_player_normal(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player and multiple characters
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        cur.execute(
            "INSERT INTO Characters (player_id, name, dnd_beyond_url) VALUES (?, ?, ?)",
            ("user1", "Hero", "url1"),
        )
        cur.execute(
            "INSERT INTO Characters (player_id, name, dnd_beyond_url) VALUES (?, ?, ?)",
            ("user1", "Hero2", "url2"),
        )
        conn.commit()
        conn.close()
        chars = cm.get_characters_for_player("user1")
        assert isinstance(chars, list)
        assert len(chars) == 2
        names = {c["name"] for c in chars}
        assert "Hero" in names and "Hero2" in names

    def test_get_characters_for_player_no_characters(self, db_and_managers):
        ssm, cm = db_and_managers
        # Create player only
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        conn.commit()
        conn.close()
        chars = cm.get_characters_for_player("user1")
        assert chars == []

    def test_get_characters_for_player_nonexistent_player(self, db_and_managers):
        ssm, cm = db_and_managers
        chars = cm.get_characters_for_player("nonexistent")
        assert chars == []
