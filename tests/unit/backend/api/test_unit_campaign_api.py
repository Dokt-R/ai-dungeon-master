from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from packages.backend.components.campaign_manager import CampaignManager
from packages.backend.main import app
from packages.shared.models import Campaign
from packages.shared.routes import ROUTES


# Mock the CampaignManager dependency
@pytest.fixture
def mock_campaign_manager():
    return AsyncMock(spec=CampaignManager)


@pytest_asyncio.fixture
async def client(mock_campaign_manager: AsyncMock):
    app.dependency_overrides[CampaignManager] = lambda: mock_campaign_manager
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides = {}


class BaseTestData:
    server_id = "test_server"
    campaign_name = "test_campaign"
    owner_id = "test_owner"
    player_id = "test_player"
    campaign_id = 123


@pytest.mark.asyncio
class TestCampaignAPI(BaseTestData):
    async def test_create_campaign(
        self, client: AsyncClient, mock_campaign_manager: AsyncMock
    ):
        # Arrange
        mock_campaign = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            owner_id=self.owner_id,
        )
        mock_campaign_manager.create_campaign.return_value = mock_campaign

        # Act
        response = await client.post(
            ROUTES.campaign_create(),
            json={
                "server_id": self.server_id,
                "campaign_name": self.campaign_name,
                "owner_id": self.owner_id,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Campaign created successfully."
        assert data["campaign_id"] == self.campaign_id
        mock_campaign_manager.create_campaign.assert_called_once_with(
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            owner_id=self.owner_id,
        )

    async def test_get_campaign(
        self, client: AsyncClient, mock_campaign_manager: AsyncMock
    ):
        # Arrange
        # Create a mock Campaign object instead of a real one to avoid relationship issues
        mock_campaign = MagicMock()
        mock_campaign.campaign_id = self.campaign_id
        mock_campaign.server_id = self.server_id
        mock_campaign.campaign_name = self.campaign_name
        mock_campaign.owner_id = self.owner_id
        mock_campaign.state = None
        mock_campaign_manager.get_campaign.return_value = mock_campaign

        # Act
        response = await client.get(
            ROUTES.campaign_details(self.server_id, self.campaign_name)
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["campaign_name"] == self.campaign_name
        mock_campaign_manager.get_campaign.assert_called_once_with(
            self.server_id, self.campaign_name
        )

    async def test_delete_campaign(
        self, client: AsyncClient, mock_campaign_manager: AsyncMock
    ):
        # Arrange
        mock_campaign_manager.delete_campaign.return_value = None

        # Act
        response = await client.request(
            "DELETE",
            ROUTES.campaign_delete(),
            json={
                "server_id": self.server_id,
                "campaign_name": self.campaign_name,
                "requester_id": self.owner_id,
                "is_admin": False,
            },
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Campaign deleted successfully."
        mock_campaign_manager.delete_campaign.assert_called_once_with(
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            requester_id=self.owner_id,
            is_admin=False,
        )

    async def test_get_campaign_players(
        self, client: AsyncClient, mock_campaign_manager: AsyncMock
    ):
        # Arrange
        mock_player = MagicMock()
        mock_player.player_id = self.player_id
        mock_player.username = "test_user"
        mock_players = [mock_player]
        mock_campaign_manager.get_campaign_players.return_value = mock_players

        # Act
        response = await client.get(ROUTES.campaign_players(self.campaign_id))

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["player_id"] == self.player_id
        assert data[0]["username"] == "test_user"
        mock_campaign_manager.get_campaign_players.assert_called_once_with(
            self.campaign_id
        )

    async def test_update_campaign_state(
        self, client: AsyncClient, mock_campaign_manager: AsyncMock
    ):
        # Arrange
        new_state = "paused"
        # Create a mock Campaign object instead of a real one to avoid relationship issues
        mock_campaign = MagicMock()
        mock_campaign.campaign_id = self.campaign_id
        mock_campaign.server_id = self.server_id
        mock_campaign.campaign_name = self.campaign_name
        mock_campaign.owner_id = self.owner_id
        mock_campaign.state = new_state
        mock_campaign_manager.update_campaign_state.return_value = mock_campaign

        # Act
        response = await client.put(
            ROUTES.campaign_state_update(self.campaign_id), json={"state": new_state}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == new_state
        mock_campaign_manager.update_campaign_state.assert_called_once_with(
            self.campaign_id, new_state
        )
