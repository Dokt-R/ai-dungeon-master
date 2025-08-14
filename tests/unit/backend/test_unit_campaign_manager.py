from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from packages.backend.components.campaign_manager import CampaignManager
from packages.shared.error_handler import NotFoundError, ValidationError
from packages.shared.models import Campaign, Player


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)

    # Create a fake result object
    fake_result = MagicMock()
    fake_result.scalars.return_value.first.return_value = (
        None  # or a fake Campaign instance
    )

    # Make execute() coroutine return the fake result
    session.execute.return_value = fake_result
    return session


@pytest.fixture
def campaign_manager(mock_session: MagicMock):
    return CampaignManager(session=mock_session)


class BaseTestData:
    server_id = "castle_aaargh"
    campaign_name = "holy_grail_quest"
    owner_id = "king_arthur"
    player_id = "brave_sir_robin"
    campaign_id = 1


@pytest.mark.asyncio
class TestCampaignManager(BaseTestData):
    async def test_create_campaign(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_session.execute.return_value.scalars.return_value.first.return_value = None

        # Act
        campaign = await campaign_manager.create_campaign(
            self.server_id, self.campaign_name, self.owner_id
        )

        # Assert
        assert campaign.campaign_name == self.campaign_name
        assert campaign.server_id == self.server_id
        assert campaign.owner_id == self.owner_id
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_create_campaign_already_exists(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            Campaign(
                campaign_id=self.campaign_id,
                server_id=self.server_id,
                campaign_name=self.campaign_name,
                owner_id=self.owner_id,
            )
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            await campaign_manager.create_campaign(
                self.server_id, self.campaign_name, self.owner_id
            )

    async def test_get_campaign(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        expected_campaign = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            owner_id=self.owner_id,
        )
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            expected_campaign
        )

        # Act
        retrieved = await campaign_manager.get_campaign(
            self.server_id, self.campaign_name
        )

        # Assert
        assert retrieved == expected_campaign

    async def test_delete_campaign_by_owner(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        campaign_to_delete = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            owner_id=self.owner_id,
        )
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            campaign_to_delete
        )

        # Act
        result = await campaign_manager.delete_campaign(
            self.server_id, self.campaign_name, self.owner_id, is_admin=False
        )

        # Assert
        assert result is True
        mock_session.delete.assert_called_once_with(campaign_to_delete)
        mock_session.commit.assert_called_once()

    async def test_delete_campaign_by_admin(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        campaign_to_delete = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            owner_id=self.owner_id,
        )
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            campaign_to_delete
        )

        # Act
        result = await campaign_manager.delete_campaign(
            self.server_id, self.campaign_name, "not_the_owner", is_admin=True
        )

        # Assert
        assert result is True
        mock_session.delete.assert_called_once_with(campaign_to_delete)
        mock_session.commit.assert_called_once()

    async def test_delete_campaign_permission_denied(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        campaign_to_delete = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            owner_id=self.owner_id,
        )
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            campaign_to_delete
        )

        # Act & Assert
        with pytest.raises(PermissionError):
            await campaign_manager.delete_campaign(
                self.server_id, self.campaign_name, "not_the_owner", is_admin=False
            )

    async def test_delete_campaign_not_found(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_session.execute.return_value.scalars.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            await campaign_manager.delete_campaign(
                self.server_id, "nonexistent", self.owner_id, is_admin=False
            )

    async def test_get_campaign_players(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_player = Player(player_id=self.player_id, username="test_user")
        mock_campaign = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            owner_id=self.owner_id,
            players=[mock_player],
        )
        mock_session.get.return_value = mock_campaign

        # Act
        players = await campaign_manager.get_campaign_players(self.campaign_id)

        # Assert
        assert len(players) == 1
        assert players[0].player_id == self.player_id
        mock_session.get.assert_called_once_with(Campaign, self.campaign_id)

    async def test_get_campaign_players_not_found(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_session.get.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            await campaign_manager.get_campaign_players(999)

    async def test_update_campaign_state(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        new_state = '{"progress": "halfway"}'
        mock_campaign = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
            owner_id=self.owner_id,
        )
        mock_session.get.return_value = mock_campaign

        # Act
        updated = await campaign_manager.update_campaign_state(
            self.campaign_id, new_state
        )

        # Assert
        assert updated.state == new_state
        mock_session.get.assert_called_once_with(Campaign, self.campaign_id)
        mock_session.add.assert_called_once_with(mock_campaign)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_campaign)

    async def test_update_campaign_state_not_found(
        self, campaign_manager: CampaignManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_session.get.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            await campaign_manager.update_campaign_state(999, "new_state")
