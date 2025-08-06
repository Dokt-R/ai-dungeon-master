import pytest
import sqlite3
from packages.backend.components.character_manager import CharacterManager
from packages.backend.components.server_settings_manager import ServerSettingsManager
from packages.shared.error_handler import ValidationError, NotFoundError

# Shared in-memory SQLite DB (accessible across connections)
SHARED_MEM_URI = "file:memdb1?mode=memory&cache=shared"
USER_ID_1 = "user-id-1"


# Fixture to initialize manager instances using shared in-memory DB
@pytest.fixture
def managers():
    ssm = ServerSettingsManager(db_path=SHARED_MEM_URI)
    cm = CharacterManager(db_path=SHARED_MEM_URI)
    return ssm, cm


# Connection fixture with row access via keys (dict-style)
@pytest.fixture
def conn():
    connection = sqlite3.connect(SHARED_MEM_URI, uri=True)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()


# Automatically clear relevant tables before each test run
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


# Patch sqlite3.connect to ensure `uri=True` is applied when using shared memory
@pytest.fixture(autouse=True)
def monkeypatch_sqlite_connect(monkeypatch):
    orig_connect = sqlite3.connect

    def connect_with_uri(db_path, *args, **kwargs):
        if db_path == SHARED_MEM_URI:
            kwargs["uri"] = True
        return orig_connect(db_path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connect_with_uri)


# Fixture to insert a predefined player for use in tests
@pytest.fixture
def insert_player(conn):
    def _insert():
        conn.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)",
            (USER_ID_1, "Alice"),
        )
        conn.commit()

    return _insert


# Fixture to fetch a character row by ID
@pytest.fixture
def select_character(conn):
    def _select_char(char_id):
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM Characters WHERE character_id = ?",
            (char_id,),
        )
        return cur.fetchone()

    return _select_char


class TestAddCharacter:
    def test_add_character_normal(
        self, managers, conn, insert_player, select_character
    ):
        ssm, cm = managers
        insert_player()
        char_id = cm.add_character(USER_ID_1, "Hero", "http://dndbeyond.com/hero")
        assert isinstance(char_id, int)
        row = select_character(char_id)
        assert row["name"] == "Hero"
        assert row["dnd_beyond_url"] == "http://dndbeyond.com/hero"

    def test_add_character_missing_player(self, managers):
        ssm, cm = managers
        with pytest.raises(NotFoundError):
            cm.add_character("user-id-2", "Hero")

    def test_add_character_duplicate_name(self, managers, conn, insert_player):
        ssm, cm = managers
        insert_player()
        cm.add_character(USER_ID_1, "Hero")
        with pytest.raises(ValidationError):
            cm.add_character(USER_ID_1, "Hero")

    def test_add_character_without_dnd_beyond_url(
        self, managers, conn, insert_player, select_character
    ):
        ssm, cm = managers
        insert_player()
        char_id = cm.add_character(USER_ID_1, "Hero")
        assert isinstance(char_id, int)
        row = select_character(char_id)
        assert row["name"] == "Hero"
        assert row["dnd_beyond_url"] is None


class TestUpdateCharacter:
    def test_update_character_normal(
        self, managers, conn, insert_player, select_character
    ):
        ssm, cm = managers
        insert_player()
        char_id = cm.add_character(USER_ID_1, "Hero", "url1")
        result = cm.update_character(char_id, name="Hero2", dnd_beyond_url="url2")
        assert result is True
        row = select_character(char_id)
        assert row["name"] == "Hero2"
        assert row["dnd_beyond_url"] == "url2"

    def test_update_character_no_fields(self, managers, conn, insert_player):
        ssm, cm = managers
        insert_player()
        char_id = cm.add_character(USER_ID_1, "Hero")
        with pytest.raises(ValidationError):
            cm.update_character(char_id)

    def test_update_character_not_found(self, managers):
        ssm, cm = managers
        with pytest.raises(NotFoundError):
            cm.update_character(9999, name="NewName")

    def test_update_character_duplicate_name(self, managers, conn, insert_player):
        ssm, cm = managers
        insert_player()
        cm.add_character(USER_ID_1, "Hero")
        char2_id = cm.add_character(USER_ID_1, "Hero2")
        with pytest.raises(ValidationError):
            cm.update_character(char2_id, name="Hero")


class TestRemoveCharacter:
    def test_remove_character_normal(
        self, managers, conn, insert_player, select_character
    ):
        ssm, cm = managers
        insert_player()
        char_id = cm.add_character(USER_ID_1, "Hero")
        result = cm.remove_character(char_id)
        assert result is True
        row = select_character(char_id)
        assert row is None

    def test_remove_character_not_found(self, managers):
        ssm, cm = managers
        result = cm.remove_character(9999)
        assert result is False

    def test_remove_character_sets_campaignplayers_null(
        self, managers, conn, insert_player, select_character
    ):
        ssm, cm = managers
        insert_player()
        char_id = cm.add_character(USER_ID_1, "Hero")

        # Simulate a campaign with a character assigned to player
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Campaigns (server_id, campaign_name, owner_id) VALUES (?, ?, ?)",
            ("server1", "Epic Quest", "owner1"),
        )
        campaign_id = cur.lastrowid
        cur.execute(
            "INSERT INTO CampaignPlayers (campaign_id, player_id, character_id) VALUES (?, ?, ?)",
            (campaign_id, USER_ID_1, char_id),
        )
        conn.commit()

        # Deleting the character should set character_id to NULL in CampaignPlayers
        cm.remove_character(char_id)

        cur = conn.cursor()
        cur.execute("SELECT * FROM CampaignPLayers WHERE player_id = ?", (USER_ID_1,))
        row = cur.fetchone()

        assert row is not None and row[3] is None


class TestGetCharactersForPlayer:
    def test_get_characters_for_player_normal(
        self, managers, conn, insert_player, select_character
    ):
        ssm, cm = managers
        # Create player and multiple characters
        insert_player()
        cm.add_character(USER_ID_1, "Hero", "url1")
        cm.add_character(USER_ID_1, "Hero2", "url2")
        chars = cm.get_characters_for_player(USER_ID_1)
        assert isinstance(chars, list)
        assert len(chars) == 2
        names = {c["name"] for c in chars}
        assert "Hero" in names and "Hero2" in names

    def test_get_characters_for_player_no_characters(
        self, managers, conn, insert_player
    ):
        ssm, cm = managers
        insert_player()
        chars = cm.get_characters_for_player(USER_ID_1)
        assert chars == []

    def test_get_characters_for_player_nonexistent_player(self, managers):
        ssm, cm = managers
        chars = cm.get_characters_for_player("nonexistent")
        assert chars == []
