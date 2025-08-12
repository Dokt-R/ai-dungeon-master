import pytest


class BaseTestData:
    server_id = "test_server"
    campaign_name = "test_campaign"
    owner_id = "test_owner"
    player_id = "test_player"


class TestCampaignAPI(BaseTestData):
    def test_create_campaign(self, client):
        response = client.post(
            "/campaigns/new",
            json={
                "server_id": self.server_id,
                "campaign_name": self.campaign_name,
                "owner_id": self.owner_id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Campaign created successfully."
        assert "campaign_id" in data

    def test_get_campaign(self, client):
        # First, create a campaign to retrieve
        client.post(
            "/campaigns/new",
            json={
                "server_id": self.server_id,
                "campaign_name": "get_test",
                "owner_id": self.owner_id,
            },
        )

        response = client.get(f"/campaigns/{self.server_id}/get_test")
        assert response.status_code == 200
        data = response.json()
        assert data["campaign_name"] == "get_test"

    def test_delete_campaign(self, client):
        # First, create a campaign to delete
        client.post(
            "/campaigns/new",
            json={
                "server_id": self.server_id,
                "campaign_name": "delete_test",
                "owner_id": self.owner_id,
            },
        )

        response = client.request(
            "DELETE",
            "/campaigns/delete",
            json={
                "server_id": self.server_id,
                "campaign_name": "delete_test",
                "requester_id": self.owner_id,
                "is_admin": False,
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Campaign deleted successfully."

    def test_get_campaign_players(self, client, insert_player):
        # Create campaign
        create_response = client.post(
            "/campaigns/new",
            json={
                "server_id": self.server_id,
                "campaign_name": "players_test",
                "owner_id": self.owner_id,
            },
        )
        campaign_id = create_response.json()["campaign_id"]

        # Create player and have them join the campaign
        insert_player(self.player_id)
        client.post(
            "/players/join_campaign",
            json={
                "server_id": self.server_id,
                "campaign_name": "players_test",
                "player_id": self.player_id,
                "character_name": "test_char",
            },
        )

        response = client.get(f"/campaigns/{campaign_id}/players")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["player_id"] == self.player_id

    def test_update_campaign_state(self, client):
        # Create campaign
        create_response = client.post(
            "/campaigns/new",
            json={
                "server_id": self.server_id,
                "campaign_name": "state_test",
                "owner_id": self.owner_id,
            },
        )
        campaign_id = create_response.json()["campaign_id"]

        response = client.put(
            f"/campaigns/{campaign_id}/state", json={"state": "paused"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "paused"
