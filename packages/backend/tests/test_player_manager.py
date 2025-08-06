import pytest
from packages.shared.error_handler import ValidationError, NotFoundError


class TestJoinCampaign:
    def test_join_campaign_normal(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        result = managers.player.join_campaign(
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

    def test_join_campaign_existing_player_and_character(
        self, managers, conn, insert_player
    ):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        # Pre-create player and character
        cur = conn.cursor()
        insert_player()
        cur.execute(
            "INSERT INTO Characters (player_id, name, dnd_beyond_url) VALUES (?, ?, ?)",
            ("user1", "Sir Test", "url"),
        )
        conn.commit()
        result = managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
            character_name="Sir Test",
        )
        assert result["character_id"] is not None

    def test_join_campaign_no_campaign_specified_and_no_last_active(
        self, managers, conn
    ):
        with pytest.raises(ValidationError):
            managers.player.join_campaign(
                player_id="user1",
                server_id="server1",
                campaign_name=None,
                username="Alice",
            )

    def test_join_campaign_campaign_not_found(self, managers, conn):
        with pytest.raises(NotFoundError):
            managers.player.join_campaign(
                player_id="user1",
                server_id="server1",
                campaign_name="Nonexistent",
                username="Alice",
            )

    def test_join_campaign_already_joined(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        with pytest.raises(ValidationError):
            managers.player.join_campaign(
                player_id="user1",
                server_id="server1",
                campaign_name="Epic Quest",
                username="Alice",
            )

    def test_join_campaign_creates_character_if_not_exists(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        result = managers.player.join_campaign(
            player_id="user2",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Bob",
            character_name="NewChar",
            dnd_beyond_url="http://dndbeyond.com/char/2",
        )
        assert result["character_id"] is not None
        cur = conn.cursor()
        cur.execute(
            "SELECT dnd_beyond_url FROM Characters WHERE player_id = ? AND name = ?",
            ("user2", "NewChar"),
        )
        row = cur.fetchone()
        assert row is not None and row[0] == "http://dndbeyond.com/char/2"

    def test_join_campaign_with_last_active_campaign(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        managers.settings.create_campaign(
            "server1", "Side Quest", "owner1", state="active"
        )
        # Join Epic Quest
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        # Now join Side Quest
        managers.player.end_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Side Quest",
            username="Alice",
        )
        # Now join with campaign_name=None (should use last_active_campaign)
        with pytest.raises(ValidationError):
            managers.player.join_campaign(
                player_id="user1",
                server_id="server1",
                campaign_name=None,
                username="Alice",
            )


class TestEndCampaign:
    def test_end_campaign_normal(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        result = managers.player.end_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["player_status"] == "cmd"
        # DB state: player_status should be 'cmd'
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

    def test_end_campaign_no_campaign_specified_uses_last_active(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        result = managers.player.end_campaign(
            player_id="user1", server_id="server1", campaign_name=None
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["player_status"] == "cmd"

    def test_end_campaign_campaign_not_found(self, managers, conn):
        with pytest.raises(NotFoundError):
            managers.player.end_campaign(
                player_id="user1", server_id="server1", campaign_name="Nonexistent"
            )

    def test_end_campaign_no_last_active(self, managers, conn):
        with pytest.raises(ValidationError):
            managers.player.end_campaign(
                player_id="user1", server_id="server1", campaign_name=None
            )

    def test_end_campaign_player_never_joined(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        # Player never joined, should not raise, but also not update any status
        result = managers.player.end_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["player_status"] == "cmd"
        # There should be no CampaignPlayers row for this player/campaign
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


class TestLeaveCampaign:
    def test_leave_campaign_normal(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        result = managers.player.leave_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["status"] == "left"
        # DB state: player should be removed from CampaignPlayers
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

    def test_leave_campaign_no_campaign_specified_uses_last_active(
        self, managers, conn
    ):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
        )
        result = managers.player.leave_campaign(
            player_id="user1", server_id="server1", campaign_name=None
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["status"] == "left"

    def test_leave_campaign_campaign_not_found(self, managers, conn):
        with pytest.raises(NotFoundError):
            managers.player.leave_campaign(
                player_id="user1", server_id="server1", campaign_name="Nonexistent"
            )

    def test_leave_campaign_no_last_active(self, managers, conn):
        with pytest.raises(ValidationError):
            managers.player.leave_campaign(
                player_id="user1", server_id="server1", campaign_name=None
            )

    def test_leave_campaign_player_never_joined(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        # Player never joined, should not raise, but also not update
        result = managers.player.leave_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        assert result["campaign_name"] == "Epic Quest"
        assert result["player_id"] == "user1"
        assert result["status"] == "left"
        # There should be no CampaignPlayers row for this player/campaign
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM CampaignPlayers
            WHERE player_id = ? AND campaign_id = (SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?)
        """,
            ("user1", "server1", "Epic Quest"),
        )
        assert cur.fetchone() is None


class TestGetPlayerStatus:
    def test_get_player_status_normal(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
            character_name="Sir Test",
            dnd_beyond_url="http://dndbeyond.com/char/1",
        )
        status = managers.player.get_player_status("user1")
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

    def test_get_player_status_no_campaigns_or_characters(
        self, managers, conn, insert_player
    ):
        insert_player("user1")
        status = managers.player.get_player_status("user1")
        assert status["player_id"] == "user1"
        assert status["username"] == "Alice"
        assert status["last_active_campaign"] is None
        assert status["campaigns"] == []
        assert status["characters"] == []

    def test_get_player_status_not_found(self, managers, conn):
        with pytest.raises(NotFoundError):
            managers.player.get_player_status("nonexistent")

    def test_get_player_status_multiple_campaigns_and_characters(self, managers, conn):
        managers.settings.create_campaign(
            "server1", "Epic Quest", "owner1", state="active"
        )
        managers.settings.create_campaign(
            "server1", "Side Quest", "owner1", state="active"
        )
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Epic Quest",
            username="Alice",
            character_name="Sir Test",
            dnd_beyond_url="http://dndbeyond.com/char/1",
        )
        managers.player.end_campaign(
            player_id="user1", server_id="server1", campaign_name="Epic Quest"
        )
        managers.player.join_campaign(
            player_id="user1",
            server_id="server1",
            campaign_name="Side Quest",
            username="Alice",
            character_name="Sir Test 2",
            dnd_beyond_url="http://dndbeyond.com/char/2",
        )
        status = managers.player.get_player_status("user1")
        assert status["player_id"] == "user1"
        assert status["username"] == "Alice"
        assert len(status["campaigns"]) == 2
        campaign_names = {c["campaign_name"] for c in status["campaigns"]}
        assert "Epic Quest" in campaign_names
        assert "Side Quest" in campaign_names
        char_names = {c["name"] for c in status["characters"]}
        assert "Sir Test" in char_names
        assert "Sir Test 2" in char_names
