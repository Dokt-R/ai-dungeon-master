import pytest

pytestmark = pytest.mark.asyncio


class BaseTestData:
    state = "active"
    server_id = "castle_aaargh"
    campaign_name = "holy_grail_quest"
    owner_id = "king_arthur"
    player_id = "brave_sir_robin"
    username = "knight_of_ni"


class TestCampaignManager(BaseTestData):
    async def test_create_and_get_campaign(self, managers, session):
        campaign = await managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        assert campaign.campaign_name == self.campaign_name

        retrieved = await managers.campaign.get_campaign(
            self.server_id, self.campaign_name
        )
        assert retrieved.campaign_id == campaign.campaign_id

    async def test_delete_campaign_by_owner(self, managers, session):
        await managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        result = await managers.campaign.delete_campaign(
            self.server_id, self.campaign_name, self.owner_id, is_admin=False
        )
        assert result is True
        retrieved = await managers.campaign.get_campaign(
            self.server_id, self.campaign_name
        )
        assert retrieved is None

    async def test_delete_campaign_by_admin(self, managers, session):
        await managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        result = await managers.campaign.delete_campaign(
            self.server_id, self.campaign_name, "not_the_owner", is_admin=True
        )
        assert result is True
        retrieved = await managers.campaign.get_campaign(
            self.server_id, self.campaign_name
        )
        assert retrieved is None

    async def test_delete_campaign_permission_denied(self, managers, session):
        await managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        with pytest.raises(PermissionError):
            await managers.campaign.delete_campaign(
                self.server_id,
                self.campaign_name,
                "not_the_owner",
                is_admin=False,
            )

    async def test_get_campaign_players(self, managers, session, insert_player):
        campaign = await managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        campaign_id = campaign.campaign_id
        await insert_player(self.player_id)
        await managers.player.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            character_name="test_char",
        )
        players = await managers.campaign.get_campaign_players(campaign_id)
        assert len(players) == 1
        assert players[0].player_id == self.player_id

    async def test_update_campaign_state(self, managers, session):
        campaign = await managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )
        updated = await managers.campaign.update_campaign_state(
            campaign.campaign_id, '{"progress": "halfway"}'
        )
        assert updated.state == '{"progress": "halfway"}'
