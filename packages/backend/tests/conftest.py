import pytest
import sqlite3
from collections import namedtuple
from packages.backend.components.campaign_manager import CampaignManager
from packages.backend.components.character_manager import CharacterManager
from packages.backend.components.player_manager import PlayerManager
from packages.backend.components.server_settings_manager import ServerSettingsManager

# Shared in-memory SQLite DB (accessible across connections)
SHARED_MEM_URI = "file:memdb1?mode=memory&cache=shared"


# Fixture to initialize manager instances using shared in-memory DB
Managers = namedtuple("Managers", ["settings", "character", "player", "campaign"])


@pytest.fixture
def managers():
    ssm = ServerSettingsManager(db_path=SHARED_MEM_URI)
    cm = CharacterManager(db_path=SHARED_MEM_URI)
    pm = PlayerManager(db_path=SHARED_MEM_URI)
    cmpm = CampaignManager(db_path=SHARED_MEM_URI)
    return Managers(ssm, cm, pm, cmpm)


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
    def _insert(user_id: str = "user-id-1", username: str = "Alice"):
        conn.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)",
            (user_id, username),
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

# Fixture to fetch a player row by user_id
@pytest.fixture
def select_player(conn):
    def _select_player(user_id: str = "user-id-1"):
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM Players WHERE user_id = ?",
            (user_id,),
        )
        return cur.fetchone()

    return _select_player