import pytest
import sqlite3
from packages.backend.components.player_manager import PlayerManager
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
    pm = PlayerManager(db_path=SHARED_MEM_URI)
    return ssm, pm


@pytest.fixture(autouse=True)
def setup_schema():
    conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Players (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            last_active_campaign TEXT,
            FOREIGN KEY (last_active_campaign) REFERENCES Campaigns(campaign_name)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Campaigns (
            campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id TEXT NOT NULL,
            campaign_name TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            state TEXT,
            last_save TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(server_id, campaign_name)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Characters (
            character_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL,
            name TEXT NOT NULL,
            dnd_beyond_url TEXT,
            FOREIGN KEY (player_id) REFERENCES Players(user_id),
            UNIQUE(player_id, name)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS CampaignPlayers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            character_id INTEGER,
            player_status TEXT CHECK(player_status IN ('joined', 'cmd')) NOT NULL DEFAULT 'joined',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES Campaigns(campaign_id),
            FOREIGN KEY (player_id) REFERENCES Players(user_id),
            FOREIGN KEY (character_id) REFERENCES Characters(character_id),
            UNIQUE(campaign_id, player_id)
        )
    """)
    conn.commit()
    conn.close()


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


class TestPlayerManager:
    def test_join_campaign_normal(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        result = pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
            character_name="Sir Test",
            dnd_beyond_url="http://dndbeyond.com/char/1",
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["status"] == "joined"
        assert result["character_id"] is not None
        # DB state assertions
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute("SELECT * FROM Players WHERE user_id = ?", ("user1",))
        assert cur.fetchone() is not None
        cur.execute(
            "SELECT * FROM Characters WHERE player_id = ? AND name = ?",
            ("user1", "Sir Test"),
        )
        assert cur.fetchone() is not None
        cur.execute(
            "SELECT * FROM CampaignPlayers WHERE player_id = ? AND player_status = 'joined'",
            ("user1",),
        )
        assert cur.fetchone() is not None
        conn.close()

    def test_join_campaign_existing_player_and_character(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        # Pre-create player and character
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        cur.execute(
            "INSERT INTO Characters (player_id, name, dnd_beyond_url) VALUES (?, ?, ?)",
            ("user1", "Sir Test", "url"),
        )
        conn.commit()
        conn.close()
        result = pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
            character_name="Sir Test",
        )
        assert result["character_id"] is not None

    def test_join_campaign_no_campaign_specified_and_no_last_active(
        self, db_and_managers
    ):
        ssm, pm = db_and_managers
        with pytest.raises(ValidationError):
            pm.join_campaign(
                player_id="user1",
                server_id="server1",
                campaign_name=None,
                username="Alice",
            )

    def test_join_campaign_campaign_not_found(self, db_and_managers):
        ssm, pm = db_and_managers
        with pytest.raises(NotFoundError):
            pm.join_campaign(
                player_id="user1",
                server_id="server1",
                campaign_name="Nonexistent",
                username="Alice",
            )

    def test_join_campaign_already_joined(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        with pytest.raises(ValidationError):
            pm.join_campaign(
                player_id="user1",
                server_id="server1",
                campaign_name="Epic Quest",
                username="Alice",
            )

    def test_join_campaign_creates_character_if_not_exists(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        result = pm.join_campaign(
            player_id="user2",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Bob",
            character_name="NewChar",
            dnd_beyond_url="http://dndbeyond.com/char/2",
        )
        assert result["character_id"] is not None
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT dnd_beyond_url FROM Characters WHERE player_id = ? AND name = ?",
            ("user2", "NewChar"),
        )
        row = cur.fetchone()
        assert row is not None and row[0] == "http://dndbeyond.com/char/2"
        conn.close()

    def test_join_campaign_with_last_active_campaign(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        ssm.create_campaign("server1", "Side Quest", "owner1", state="active")
        # Join Epic Quest
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        # Now join Side Quest
        pm.end_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Side Quest",
            username="Alice",
        )
        # Now join with campaign_name=None (should use last_active_campaign)
        with pytest.raises(ValidationError):
            pm.join_campaign(
                player_id="user1",
                server_id="server1",
                campaign_name=None,
                username="Alice",
            )

    def test_end_campaign_normal(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        result = pm.end_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["player_status"] == "cmd"
        # DB state: player_status should be 'cmd'
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT player_status FROM CampaignPlayers
            WHERE player_id = ? AND campaign_id = (SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?)
        """,
            ("user1", "server1", "Epic Quest"),
        )
        row = cur.fetchone()
        assert row is not None and row[0] == "cmd"
        conn.close()

    def test_end_campaign_no_campaign_specified_uses_last_active(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        result = pm.end_campaign(
            player_id="user1", server_id="server1", campaign_name=None
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["player_status"] == "cmd"

    def test_end_campaign_campaign_not_found(self, db_and_managers):
        ssm, pm = db_and_managers
        with pytest.raises(NotFoundError):
            pm.end_campaign(
                player_id="user1", server_id="server1", campaign_name="Nonexistent"
            )

    def test_end_campaign_no_last_active(self, db_and_managers):
        ssm, pm = db_and_managers
        with pytest.raises(ValidationError):
            pm.end_campaign(player_id="user1", server_id="server1", campaign_name=None)

    def test_end_campaign_player_never_joined(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        # Player never joined, should not raise, but also not update any status
        result = pm.end_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["player_status"] == "cmd"
        # There should be no CampaignPlayers row for this player/campaign
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT player_status FROM CampaignPlayers
            WHERE player_id = ? AND campaign_id = (SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?)
        """,
            ("user1", "server1", "Epic Quest"),
        )
        row = cur.fetchone()
        assert row is None
        conn.close()

    def test_leave_campaign_normal(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        result = pm.leave_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["status"] == "left"
        # DB state: player should be removed from CampaignPlayers
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM CampaignPlayers
            WHERE player_id = ? AND campaign_id = (SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?)
        """,
            ("user1", "server1", "Epic Quest"),
        )
        assert cur.fetchone() is None
        # last_active_campaign should be NULL
        cur.execute(
            "SELECT last_active_campaign FROM Players WHERE user_id = ?", ("user1",)
        )
        assert cur.fetchone()[0] is None
        conn.close()

    def test_leave_campaign_no_campaign_specified_uses_last_active(
        self, db_and_managers
    ):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        result = pm.leave_campaign(
            player_id="user1", server_id="server1", campaign_name=None
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["status"] == "left"

    def test_leave_campaign_campaign_not_found(self, db_and_managers):
        ssm, pm = db_and_managers
        with pytest.raises(NotFoundError):
            pm.leave_campaign(
                player_id="user1", server_id="server1", campaign_name="Nonexistent"
            )

    def test_leave_campaign_no_last_active(self, db_and_managers):
        ssm, pm = db_and_managers
        with pytest.raises(ValidationError):
            pm.leave_campaign(
                player_id="user1", server_id="server1", campaign_name=None
            )

    def test_leave_campaign_player_never_joined(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        # Player never joined, should not raise, but also not update
        result = pm.leave_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["status"] == "left"
        # There should be no CampaignPlayers row for this player/campaign
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM CampaignPlayers
            WHERE player_id = ? AND campaign_id = (SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?)
        """,
            ("user1", "server1", "Epic Quest"),
        )
        assert cur.fetchone() is None
        conn.close()

    def test_get_player_status_normal(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
            character_name="Sir Test",
            dnd_beyond_url="http://dndbeyond.com/char/1",
        )
        status = pm.get_player_status("user1")
        assert status["player_id"] == "user1"
        assert status["username"] == "Alice"
        assert status["last_active_campaign"] is not None
        assert len(status["campaigns"]) == 1
        assert status["campaigns"][0]["campaign_name"] == "Epic Quest"
        assert status["campaigns"][0]["player_status"] == "joined"
        assert len(status["characters"]) == 1
        assert status["characters"][0]["name"] == "Sir Test"
        assert (
            status["characters"][0]["dnd_beyond_url"] == "http://dndbeyond.com/char/1"
        )

    def test_get_player_status_no_campaigns_or_characters(self, db_and_managers):
        ssm, pm = db_and_managers
        # Create player only
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username) VALUES (?, ?)", ("user1", "Alice")
        )
        conn.commit()
        conn.close()
        status = pm.get_player_status("user1")
        assert status["player_id"] == "user1"
        assert status["username"] == "Alice"
        assert status["last_active_campaign"] is None
        assert status["campaigns"] == []
        assert status["characters"] == []

    def test_get_player_status_not_found(self, db_and_managers):
        ssm, pm = db_and_managers
        with pytest.raises(NotFoundError):
            pm.get_player_status("nonexistent")

    def test_get_player_status_multiple_campaigns_and_characters(self, db_and_managers):
        ssm, pm = db_and_managers
        ssm.create_campaign("server1", "Epic Quest", "owner1", state="active")
        ssm.create_campaign("server1", "Side Quest", "owner1", state="active")
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
            character_name="Sir Test",
            dnd_beyond_url="http://dndbeyond.com/char/1",
        )
        pm.end_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        pm.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Side Quest",
            username="Alice",
            character_name="Sir Test 2",
            dnd_beyond_url="http://dndbeyond.com/char/2",
        )
        status = pm.get_player_status("user1")
        assert status["player_id"] == "user1"
        assert status["username"] == "Alice"
        assert len(status["campaigns"]) == 2
        campaign_names = {c["campaign_name"] for c in status["campaigns"]}
        assert "Epic Quest" in campaign_names
        assert "Side Quest" in campaign_names
        char_names = {c["name"] for c in status["characters"]}
        assert "Sir Test" in char_names
        assert "Sir Test 2" in char_names
