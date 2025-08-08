import pytest
from packages.shared.models import Player


class BaseTestData:
    state = "active"
    server_id = "castle_aaargh"
    campaign_name = "holy_grail_quest"
    owner_id = "king_arthur"
    player_id = "brave_sir_robin"
    username = "knight_of_ni"


class TestCampaignManager(BaseTestData):
    def test_create_and_get_campaign(self, managers, session):
        campaign = managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        assert campaign.campaign_name == self.campaign_name

        retrieved = managers.campaign.get_campaign(self.server_id, self.campaign_name)
        assert retrieved.campaign_id == campaign.campaign_id

    def test_delete_campaign(self, managers, session):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        result = managers.campaign.delete_campaign(
            self.server_id, self.campaign_name, self.owner_id, is_admin=False
        )
        assert result is True
        retrieved = managers.campaign.get_campaign(self.server_id, self.campaign_name)
        assert retrieved is None

    def test_get_campaign_players(self, managers, session, insert_player):
        campaign = managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        insert_player(self.player_id)
        managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            character_name="test_char",
        )
        players = managers.campaign.get_campaign_players(campaign.campaign_id)
        assert len(players) == 1
        assert players[0].player_id == self.player_id

    def test_update_campaign_state(self, managers, session):
        campaign = managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        updated = managers.campaign.update_campaign_state(
            campaign.campaign_id, '{"progress": "halfway"}'
        )
        assert updated.state == '{"progress": "halfway"}'
