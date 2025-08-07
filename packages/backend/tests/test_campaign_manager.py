import sqlite3
import pytest

SHARED_MEM_URI = "file:memdb1?mode=memory&cache=shared"


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


class TestAutosave(BaseTestData):
    def test_set_and_get_autosave(self, managers, conn):
        # Create campaign
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        campaign = managers.campaign.get_campaign(self.server_id, self.campaign_name)
        print(campaign)
        campaign_id = campaign["campaign_id"]
        # Set autosave
        managers.campaign.set_campaign_autosave(campaign_id, '{"progress": 1}')
        autosave = managers.campaign.get_latest_campaign_autosave(campaign_id)
        assert autosave is not None
        assert autosave["state"] == '{"progress": 1}'

    def test_continue_campaign_none_if_no_last_active(self, managers, conn):
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, self.owner_id, self.state
        )
        result = managers.campaign.continue_campaign(self.player_id, self.server_id)
        assert result is None

    @pytest.mark.skip(reason="Test logic is wrong and must be fixed.")
    def test_continue_campaign_returns_autosave_if_newer(
        self, monkeypatch, managers, conn
    ):
        # Create player and campaign
        managers.campaign.create_campaign(
            self.server_id, self.campaign_name, "owner1", state='{"progress": 1}'
        )
        campaign = managers.campaign.get_campaign(self.server_id, self.campaign_name)
        campaign_id = campaign["campaign_id"]
        # Set player last_active_campaign
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username, last_active_campaign) VALUES (?, ?, ?)",
            ("user1", "Alice", self.campaign_name),
        )
        conn.commit()
        conn.close()
        # Set autosave with a newer timestamp
        managers.campaign.set_campaign_autosave(campaign_id, '{"progress": 2}')

        # Monkeypatch last_save to be older
        def fake_get_campaign(server_id, campaign_name):
            c = campaign.copy()
            c["last_save"] = "2000-01-01 00:00:00"
            return c

        monkeypatch.setattr(managers.campaign, "get_campaign", fake_get_campaign)

        result = managers.campaign.continue_campaign("user1", self.server_id)
        assert result["source"] == "autosave"
        assert result["state"] == '{"progress": 2}'

    @pytest.mark.skip(reason="Test logic is wrong and must be fixed.")
    def test_continue_campaign_returns_save_if_no_autosave(
        self, monkeypatch, managers, conn
    ):
        # Create player and campaign
        managers.campaign.create_campaign(
            "server1", "TestCampaign", "owner1", state='{"progress": 1}'
        )
        campaign = managers.campaign.get_campaign("server1", "TestCampaign")
        # Set player last_active_campaign
        conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Players (user_id, username, last_active_campaign) VALUES (?, ?, ?)",
            ("user1", "Alice", "TestCampaign"),
        )
        conn.commit()
        conn.close()

        # No autosave set
        def fake_get_campaign(server_id, campaign_name):
            c = campaign.copy()
            c["last_save"] = "2100-01-01 00:00:00"
            return c

        monkeypatch.setattr(managers.campaign, "get_campaign", fake_get_campaign)
        result = managers.campaign.continue_campaign("user1", "server1")
        assert result["source"] == "save"
        assert result["state"] == '{"progress": 1}'
