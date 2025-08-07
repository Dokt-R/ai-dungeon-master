import pytest
from packages.shared.error_handler import ValidationError, NotFoundError


class BaseTestData:
    state = "active"
    server_id = "castle_aaargh"
    campaign_name = "holy_grail_quest"
    owner_id = "king_arthur"
    player_id = "brave_sir_robin"
    username = "knight_of_ni"
    character_name = "tim_the_enchanter"
    character_name2 = "black_knight"
    url = "http://dndbeyond.com/tim_the_enchanter"
    url2 = "http://dndbeyond.com/black_knight"


class TestJoinCampaign(BaseTestData):
    def test_join_campaign_normal(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
            dnd_beyond_url=self.url,
        )
        assert result["campaign_name"] == self.campaign_name
        assert result["player_id"] == self.player_id
        assert result["status"] == "joined"
        assert result["character_id"] is not None
        # DB state assertions
        player = managers.player.get_player_status(self.player_id)
        assert player is not None
        character = managers.character.get_characters_for_player(self.player_id)
        assert character is not None

        campaign_players = managers.campaign.get_campaign_players(self.campaign_name)

        assert campaign_players is not None
        assert campaign_players[0]["player_status"] == "joined"

    def test_join_campaign_existing_player_and_character(
        self, managers, conn, insert_player
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        # Pre-create player and character
        insert_player(self.player_id)
        managers.character.add_character(self.player_id, self.character_name, self.url)
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            character_name=self.character_name,
        )
        assert result["character_id"] is not None
        assert result["player_id"] == self.player_id
        assert result["status"] == "joined"

        campaign_players = managers.campaign.get_campaign_players(self.campaign_name)
        assert campaign_players is not None

    # Expected to join and use the one available character
    def test_join_campaign_one_character_null_input(
        self, managers, conn, insert_player
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        insert_player(self.player_id)
        managers.character.add_character(self.player_id, self.character_name, self.url)
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        assert result["character_id"] is not None
        assert result["player_id"] == self.player_id
        assert result["status"] == "joined"
        campaign_players = managers.campaign.get_campaign_players(self.campaign_name)
        assert campaign_players is not None

    # Expected to join by specifying name
    def test_join_campaign_two_characters(self, managers, conn, insert_player):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        insert_player(self.player_id)
        managers.character.add_character(self.player_id, self.character_name, self.url)
        character_2 = managers.character.add_character(
            self.player_id, self.character_name2, self.url2
        )
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            character_name=self.character_name2,
        )
        assert result["character_id"] == character_2

    # Expected to fail with ValidationError
    def test_join_campaign_two_characters_no_name(self, managers, conn, insert_player):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        # Pre-create player and character
        insert_player(self.player_id)
        managers.character.add_character(self.player_id, self.character_name, self.url)
        managers.character.add_character(
            self.player_id, self.character_name2, self.url2
        )
        with pytest.raises(ValidationError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=self.campaign_name,
            )

    def test_join_campaign_no_character_null_input(self, managers, conn, insert_player):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        # Pre-create player and character
        insert_player(self.player_id)
        # managers.character.add_character(self.player_id, self.character_name, "url")
        with pytest.raises(NotFoundError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=self.campaign_name,
            )

    def test_join_campaign_no_campaign_specified_and_no_last_active(
        self, managers, conn
    ):
        with pytest.raises(NotFoundError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=None,
                username=self.username,
                character_name=self.character_name,
            )

    def test_join_campaign_campaign_not_found(self, managers, conn):
        with pytest.raises(NotFoundError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name="Nonexistent",
                username=self.username,
                character_name=self.character_name,
            )

    def test_join_campaign_already_joined(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
        )
        with pytest.raises(ValidationError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=self.campaign_name,
                username=self.username,
            )

    def test_join_campaign_creates_character_if_not_exists(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
            dnd_beyond_url=self.url,
        )
        character = managers.character.get_characters_for_player(self.player_id)

        assert character is not None and character[0]["dnd_beyond_url"] == self.url

    def test_join_campaign_with_last_active_campaign(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        managers.campaign.create_campaign(
            self.server_id, "Side Quest", self.owner_id, self.state
        )
        # Join Epic Quest
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
        )

        # Now join Side Quest
        managers.player.end_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name="Side Quest",
            username=self.username,
        )

        # End and auto join last_active_campaign
        managers.player.end_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name="Side Quest",
        )
        last_join = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            username=self.username,
        )

        assert last_join["campaign_name"] == "Side Quest"

        # Now join with campaign_name=None (should use last_active_campaign and fail as already joined)
        with pytest.raises(ValidationError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=None,
                username=self.username,
            )


class TestEndCampaign(BaseTestData):
    def test_end_campaign_normal(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
        )
        result = managers.player.end_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        assert result["campaign_name"] == self.campaign_name
        assert result["player_id"] == self.player_id
        assert result["player_status"] == "cmd"
        # DB state: player_status should be 'cmd'
        cur = conn.cursor()
        cur.execute(
            """
            SELECT player_status FROM CampaignPlayers
            WHERE player_id = ? AND campaign_id = (SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?)
        """,
            (self.player_id, self.server_id, self.campaign_name),
        )
        row = cur.fetchone()
        assert row is not None and row[0] == "cmd"

    def test_end_campaign_no_campaign_specified_uses_last_active(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
        )
        result = managers.player.end_campaign(
            player_id=self.player_id, server_id=self.server_id, campaign_name=None
        )
        assert result["campaign_name"] == self.campaign_name
        assert result["player_id"] == self.player_id
        assert result["player_status"] == "cmd"

    def test_end_campaign_campaign_not_found(self, managers, conn):
        with pytest.raises(NotFoundError):
            managers.player.end_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name="Nonexistent",
            )

    def test_end_campaign_no_last_active(self, managers, conn):
        with pytest.raises(ValidationError):
            managers.player.end_campaign(
                player_id=self.player_id, server_id=self.server_id, campaign_name=None
            )

    def test_end_campaign_player_never_joined(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        # Player never joined, should not raise, but also not update any status
        result = managers.player.end_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        assert result["campaign_name"] == self.campaign_name
        assert result["player_id"] == self.player_id
        assert result["player_status"] == "cmd"
        # There should be no CampaignPlayers row for this player/campaign
        cur = conn.cursor()
        cur.execute(
            """
            SELECT player_status FROM CampaignPlayers
            WHERE player_id = ? AND campaign_id = (SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?)
        """,
            (self.player_id, self.server_id, self.campaign_name),
        )
        row = cur.fetchone()
        assert row is None


class TestLeaveCampaign(BaseTestData):
    def test_leave_campaign_normal(self, managers, conn, select_player):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
        )
        result = managers.player.leave_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        assert result["campaign_name"] == self.campaign_name
        assert result["player_id"] == self.player_id
        assert result["status"] == "left"
        # DB state: player should be removed from CampaignPlayers
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM CampaignPlayers
            WHERE player_id = ? AND campaign_id = (SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?)
        """,
            (self.player_id, self.server_id, self.campaign_name),
        )
        assert cur.fetchone() is None
        # last_active_campaign should be NULL
        player = managers.player.get_player_status(self.player_id)
        assert player["last_active_campaign"] is None

    def test_leave_campaign_no_campaign_specified_uses_last_active(
        self, managers, conn
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
        )
        result = managers.player.leave_campaign(
            player_id=self.player_id, server_id=self.server_id, campaign_name=None
        )
        assert result["campaign_name"] == self.campaign_name
        assert result["player_id"] == self.player_id
        assert result["status"] == "left"

    def test_leave_campaign_campaign_not_found(self, managers, conn):
        with pytest.raises(NotFoundError):
            managers.player.leave_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name="Nonexistent",
            )

    def test_leave_campaign_no_last_active(self, managers, conn):
        with pytest.raises(ValidationError):
            managers.player.leave_campaign(
                player_id=self.player_id, server_id=self.server_id, campaign_name=None
            )

    def test_leave_campaign_player_never_joined(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        # Player never joined, should not raise, but also not update
        result = managers.player.leave_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        assert result["campaign_name"] == self.campaign_name
        assert result["player_id"] == self.player_id
        assert result["status"] == "left"
        # There should be no CampaignPlayers row for this player/campaign
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM CampaignPlayers
            WHERE player_id = ? AND campaign_id = (SELECT campaign_id FROM Campaigns WHERE server_id = ? AND campaign_name = ?)
        """,
            (self.player_id, self.server_id, self.campaign_name),
        )
        assert cur.fetchone() is None


class TestGetPlayerStatus(BaseTestData):
    def test_get_player_status_normal(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
            dnd_beyond_url=self.url,
        )
        status = managers.player.get_player_status(self.player_id)
        assert status["player_id"] == self.player_id
        assert status["username"] == self.username
        assert status["last_active_campaign"] is not None
        assert len(status["campaigns"]) == 1
        assert status["campaigns"][0]["campaign_name"] == self.campaign_name
        assert status["campaigns"][0]["player_status"] == "joined"
        assert len(status["characters"]) == 1
        assert status["characters"][0]["name"] == self.character_name
        assert status["characters"][0]["dnd_beyond_url"] == self.url

    def test_get_player_status_no_campaigns_or_characters(
        self, managers, conn, insert_player
    ):
        insert_player(self.player_id, self.username)
        status = managers.player.get_player_status(self.player_id)
        assert status["player_id"] == self.player_id
        assert status["username"] == self.username
        assert status["last_active_campaign"] is None
        assert status["campaigns"] == []
        assert status["characters"] == []

    def test_get_player_status_not_found(self, managers, conn):
        with pytest.raises(NotFoundError):
            managers.player.get_player_status("nonexistent")

    def test_get_player_status_multiple_campaigns_and_characters(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        managers.campaign.create_campaign(
            self.server_id, "Side Quest", self.owner_id, self.state
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
            dnd_beyond_url=self.url,
        )
        managers.player.end_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name="Side Quest",
            username=self.username,
            character_name="Sir Test 2",
            dnd_beyond_url="http://dndbeyond.com/char/2",
        )
        status = managers.player.get_player_status(self.player_id)
        assert status["player_id"] == self.player_id
        assert status["username"] == self.username
        assert len(status["campaigns"]) == 2
        campaign_names = {c["campaign_name"] for c in status["campaigns"]}
        assert self.campaign_name in campaign_names
        assert "Side Quest" in campaign_names
        char_names = {c["name"] for c in status["characters"]}
        assert self.character_name in char_names
        assert "Sir Test 2" in char_names
