from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from packages.backend.components.player_manager import PlayerManager
from packages.backend.main import app
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import NotFoundError


@pytest.fixture
def mock_player_manager():
    return MagicMock(spec=PlayerManager)


@pytest.fixture
def client(mock_player_manager: MagicMock):
    app.dependency_overrides[PlayerManager] = lambda: mock_player_manager
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {}


class BaseTestData:
    server_id = "castle_aaargh"
    campaign_name = "holy_grail_quest"
    owner_id = "king_arthur"
    player_id = "brave_sir_robin"
    username = "knight_of_ni"
    character_name = "tim_the_enchanter"


class TestPlayersCreate(BaseTestData):
    def test_create_player_success(
        self, client: TestClient, mock_player_manager: MagicMock
    ):
        # Arrange
        mock_player_manager.create_player.return_value = {
            "player_id": self.player_id,
            "username": self.username,
        }

        # Act
        resp = client.post(
            "/players/create",
            json={"player_id": self.player_id, "username": self.username},
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_id"] == self.player_id
        assert data["username"] == self.username
        mock_player_manager.create_player.assert_called_once_with(
            player_id=self.player_id, username=self.username
        )


class TestPlayersJoinCampaign(BaseTestData):
    def test_join_campaign_success(
        self, client: TestClient, mock_player_manager: MagicMock
    ):
        # Arrange
        mock_player_manager.join_campaign.return_value = {
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_id": 1,
            "status": "joined",
        }
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "character_name": self.character_name,
        }

        # Act
        resp = client.post("/players/join_campaign", json=payload)

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Campaign joined successfully."
        assert data["result"]["player_id"] == self.player_id
        mock_player_manager.join_campaign.assert_called_once()

    def test_join_campaign_nonexistent_campaign(
        self, client: TestClient, mock_player_manager: MagicMock
    ):
        # Arrange
        error = ErrorCode.PLAYER_NOT_FOUND
        mock_player_manager.join_campaign.side_effect = NotFoundError(error)
        payload = {
            "server_id": self.server_id,
            "campaign_name": "DoesNotExist",
            "player_id": self.player_id,
            "character_name": self.character_name,
        }

        # Act
        resp = client.post("/players/join_campaign", json=payload)

        # Assert
        assert resp.status_code == error.status_code


class TestPlayersEndCampaign(BaseTestData):
    def test_end_campaign_success(
        self, client: TestClient, mock_player_manager: MagicMock
    ):
        # Arrange
        mock_player_manager.end_campaign.return_value = {"narrative": "The end."}
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }

        # Act
        resp = client.post("/players/end_campaign", json=payload)

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Campaign exited successfully."
        assert data["narrative"] == "The end."
        mock_player_manager.end_campaign.assert_called_once_with(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )


class TestPlayersRemoveCampaign(BaseTestData):
    def test_remove_campaign_success(
        self, client: TestClient, mock_player_manager: MagicMock
    ):
        # Arrange
        mock_player_manager.remove_campaign.return_value = {
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
            "status": "left",
        }
        payload = {
            "server_id": self.server_id,
            "campaign_name": self.campaign_name,
            "player_id": self.player_id,
        }

        # Act
        resp = client.post("/players/remove_campaign", json=payload)

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Left campaign successfully."
        assert data["result"]["status"] == "left"
        mock_player_manager.remove_campaign.assert_called_once_with(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )


class TestGetPlayer(BaseTestData):
    def test_get_player_status_success(
        self, client: TestClient, mock_player_manager: MagicMock
    ):
        # Arrange
        mock_player_manager.get_player.return_value = {
            "player_id": self.player_id,
            "username": self.username,
            "campaigns": [],
            "characters": [],
        }

        # Act
        resp = client.get(f"/players/status/{self.player_id}")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_id"] == self.player_id
        mock_player_manager.get_player.assert_called_once_with(self.player_id)

    def test_get_player_status_not_found(
        self, client: TestClient, mock_player_manager: MagicMock
    ):
        # Arrange
        error = ErrorCode.PLAYER_NOT_FOUND
        mock_player_manager.get_player.side_effect = NotFoundError(error)

        # Act
        resp = client.get("/players/status/nonexistent")

        # Assert
        assert resp.status_code == error.status_code
