import pytest
from sqlmodel import select
from packages.shared.error_handler import ValidationError, NotFoundError
from packages.shared.models import Campaign, Player, Character, CampaignPlayerLink


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
    def test_join_campaign_normal(self, managers, session):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            username=self.username,
            campaign_name=self.campaign_name,
            character_name=self.character_name,
        )
        
        player = session.get(Player, result.player_id)
        campaign = session.get(Campaign, result.campaign_id)

        assert campaign.campaign_name == self.campaign_name

        assert player.user_id == self.player_id
        assert player.player_status == "joined"

        assert player.characters[0].character_id is not None
        assert player.characters[0].name == self.character_name
        assert player.campaigns[0].campaign_name == self.campaign_name

    def test_join_campaign_existing_player_and_character(
        self, managers, session, insert_player
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        insert_player(self.player_id)
        character = managers.character.add_character(
            self.player_id, self.character_name, self.url
        )
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            character_name=self.character_name,
        )

        player = session.get(Player, result.player_id)

        assert player.characters[0].character_id == character.character_id
        assert player.user_id == self.player_id
        assert player.player_status == "joined"

    def test_join_campaign_one_character_null_input(
        self, managers, session, insert_player
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        insert_player(self.player_id)
        managers.character.add_character(self.player_id, self.character_name, self.url)
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        player = session.get(Player, result.player_id)

        assert player.characters[0].character_id is not None
        assert player.user_id == self.player_id
        assert player.player_status == "joined"

    def test_join_campaign_two_characters(self, managers, session, insert_player):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        insert_player(self.player_id)
        managers.character.add_character(self.player_id, self.character_name, self.url)
        joined_character = managers.character.add_character(
            self.player_id, self.character_name2, self.url2
        )
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            character_name=self.character_name2,
        )
        player = session.get(Player, result.player_id)

        assert player.characters[1].character_id == joined_character.character_id

    def test_join_campaign_two_characters_no_name(
        self, managers, session, insert_player
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
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

    def test_join_campaign_no_character_null_input(
        self, managers, session, insert_player
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        insert_player(self.player_id)
        with pytest.raises(NotFoundError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=self.campaign_name,
            )

    def test_join_campaign_no_campaign_specified_and_no_last_active(
        self, managers, session
    ):
        with pytest.raises(NotFoundError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=None,
                username=self.username,
                character_name=self.character_name,
            )

    def test_join_campaign_campaign_not_found(self, managers, session):
        with pytest.raises(NotFoundError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name="Nonexistent",
                username=self.username,
                character_name=self.character_name,
            )

    def test_join_campaign_already_joined(self, managers, session):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
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

    def test_join_campaign_creates_character_if_not_exists(self, managers, session):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
            character_url=self.url,
        )

        player = session.get(Player, result.player_id)

        assert player.characters is not None
        assert player.characters[0].character_url == self.url

    def test_join_campaign_with_last_active_campaign(self, managers, session):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        managers.campaign.create_campaign(self.server_id, "Side Quest", self.owner_id)
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
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
        )
        managers.player.end_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name="Side Quest",
        )
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            username=self.username,
        )

        campaign = session.get(Campaign, result.campaign_id)

        assert campaign.campaign_name == "Side Quest"
        # Expects to raise error as player already joined the campaign
        with pytest.raises(ValidationError):
            managers.player.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=None,
                username=self.username,
            )

    def test_join_different_campaign_with_without_end(self, managers, session):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        managers.campaign.create_campaign(self.server_id, "Side Quest", self.owner_id)
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
        )
        # Join a different campaign without initiating /campaign end command
        result = managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name="Side Quest",
            username=self.username,
        )

        campaign = session.get(Campaign, result.campaign_id)
        player = session.get(Player, result.player_id)
        
        assert campaign.campaign_name == "Side Quest"
        assert player.last_active_campaign == "Side Quest"
        assert player.player_status == "joined"



class TestEndCampaign(BaseTestData):
    def test_end_campaign_normal(self, managers, session):
        campaign = managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
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

        link = session.exec(
            select(CampaignPlayerLink)
            .where(CampaignPlayerLink.player_id == self.player_id)
            .where(CampaignPlayerLink.campaign_id == campaign.campaign_id)
        ).first()
        assert link is not None and link.player_status == "cmd"

    def test_end_campaign_no_campaign_specified_uses_last_active(
        self, managers, session
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
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

    def test_end_campaign_campaign_not_found(self, managers, session):
        with pytest.raises(NotFoundError):
            managers.player.end_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name="Nonexistent",
            )

    def test_end_campaign_no_last_active(self, managers, session):
        with pytest.raises(ValidationError):
            managers.player.end_campaign(
                player_id=self.player_id, server_id=self.server_id, campaign_name=None
            )

    def test_end_campaign_player_never_joined(self, managers, session):
        campaign = managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        result = managers.player.end_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        assert result["campaign_name"] == self.campaign_name
        assert result["player_id"] == self.player_id
        assert result["player_status"] == "cmd"

        link = session.exec(
            select(CampaignPlayerLink)
            .where(CampaignPlayerLink.player_id == self.player_id)
            .where(CampaignPlayerLink.campaign_id == campaign.campaign_id)
        ).first()
        assert link is None


class TestLeaveCampaign(BaseTestData):
    def test_leave_campaign_normal(self, managers, session):
        campaign = managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
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
        assert result is True
        link = session.exec(
            select(CampaignPlayerLink)
            .where(CampaignPlayerLink.player_id == self.player_id)
            .where(CampaignPlayerLink.campaign_id == campaign.campaign_id)
        ).first()
        assert link is None
        player = session.get(Player, self.player_id)
        assert player.last_active_campaign is None

    def test_leave_campaign_no_campaign_specified_uses_last_active(
        self, managers, session
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
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
        assert result is True

    def test_leave_campaign_campaign_not_found(self, managers, session):
        with pytest.raises(NotFoundError):
            managers.player.leave_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name="Nonexistent",
            )

    def test_leave_campaign_no_last_active(self, managers, session):
        with pytest.raises(NotFoundError):
            managers.player.leave_campaign(
                player_id=self.player_id, server_id=self.server_id, campaign_name=None
            )

    def test_leave_campaign_player_never_joined(self, managers, session):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        result = managers.player.leave_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        assert result is False


class TestGetPlayerStatus(BaseTestData):
    def test_get_player_status_normal(self, managers, session):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
        )
        status = managers.player.get_player_status(self.player_id)
        assert status["player_id"] == self.player_id
        assert status["username"] == self.username
        assert status["last_active_campaign"] is not None
        assert len(status["campaigns"]) == 1
        assert status["campaigns"][0]["campaign_name"] == self.campaign_name
        assert status["campaigns"][0]["player_status"] == "joined"
        assert len(status["characters"]) == 1
        assert status["characters"][0].name == self.character_name
        assert status["characters"][0].character_url == self.url

    def test_get_player_status_no_campaigns_or_characters(
        self, managers, session, insert_player
    ):
        insert_player(self.player_id, self.username)
        status = managers.player.get_player_status(self.player_id)
        assert status["player_id"] == self.player_id
        assert status["username"] == self.username
        assert status["last_active_campaign"] is None
        assert status["campaigns"] == []
        assert status["characters"] == []

    def test_get_player_status_not_found(self, managers, session):
        with pytest.raises(NotFoundError):
            managers.player.get_player_status("nonexistent")

    def test_get_player_status_multiple_campaigns_and_characters(
        self, managers, session
    ):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        managers.campaign.create_campaign(self.server_id, "Side Quest", self.owner_id)
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            username=self.username,
            character_name=self.character_name,
        )
        managers.player.leave_campaign(
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
        )
        status = managers.player.get_player_status(self.player_id)
        assert status["player_id"] == self.player_id
        assert status["username"] == self.username
        assert len(status["campaigns"]) == 1
        assert status["campaigns"][0]["campaign_name"] == "Side Quest"
        assert len(status["characters"]) == 2
        char_names = {c.name for c in status["characters"]}
        assert self.character_name in char_names
        assert "Sir Test 2" in char_names
