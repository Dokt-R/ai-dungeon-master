from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from packages.backend.components.player_manager import PlayerManager
from packages.shared.error_handler import NotFoundError, ValidationError
from packages.shared.models import Campaign, CampaignPlayerLink, Character, Player


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def player_manager(mock_session: MagicMock):
    return PlayerManager(session=mock_session)


class BaseTestData:
    server_id = "castle_aaargh"
    campaign_name = "holy_grail_quest"
    owner_id = "king_arthur"
    player_id = "brave_sir_robin"
    username = "knight_of_ni"
    character_name = "tim_the_enchanter"
    character_url = "http://dndbeyond.com/tim_the_enchanter"
    campaign_id = 1
    character_id = 1


@pytest.mark.asyncio
class TestJoinCampaign(BaseTestData):
    async def test_join_campaign_normal(
        self, player_manager: PlayerManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_player = Player(player_id=self.player_id, username=self.username)
        mock_campaign = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        mock_character = Character(
            character_id=self.character_id,
            name=self.character_name,
            player_id=self.player_id,
        )

        mock_session.get.return_value = mock_player
        mock_session.execute.side_effect = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_campaign))
                )
            ),  # find campaign
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=None))
                )
            ),  # check if joined
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_character))
                )
            ),  # find character
        ]
        mock_session.merge.return_value = CampaignPlayerLink(
            campaign_id=self.campaign_id, player_id=self.player_id
        )

        # Act
        result = await player_manager.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            username=self.username,
            campaign_name=self.campaign_name,
            character_name=self.character_name,
        )

        # Assert
        assert result["campaign_name"] == self.campaign_name
        assert result["player_id"] == self.player_id
        assert result["status"] == "joined"
        mock_session.commit.assert_called_once()

    async def test_join_campaign_no_character_one_exists(
        self, player_manager: PlayerManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_player = Player(player_id=self.player_id, username=self.username)
        mock_campaign = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        mock_character = Character(
            character_id=self.character_id,
            name=self.character_name,
            player_id=self.player_id,
        )

        mock_session.get.return_value = mock_player
        mock_session.execute.side_effect = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_campaign))
                )
            ),  # find campaign
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=None))
                )
            ),  # check if joined
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[mock_character]))
                )
            ),  # find characters
        ]

        # Act
        result = await player_manager.join_campaign(
            player_id=self.player_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )

        # Assert
        assert result["character_id"] == self.character_id
        mock_session.commit.assert_called_once()

    async def test_join_campaign_no_character_multiple_exist(
        self, player_manager: PlayerManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_player = Player(player_id=self.player_id, username=self.username)
        mock_campaign = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        mock_session.get.return_value = mock_player
        mock_session.execute.side_effect = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_campaign))
                )
            ),  # find campaign
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=None))
                )
            ),  # check if joined
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(
                        all=MagicMock(return_value=[MagicMock(), MagicMock()])
                    )
                )
            ),  # find characters
        ]

        # Act & Assert
        with pytest.raises(ValidationError):
            await player_manager.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=self.campaign_name,
            )

    async def test_join_campaign_already_joined(
        self, player_manager: PlayerManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_player = Player(
            player_id=self.player_id,
            username=self.username,
            last_active_campaign=self.campaign_name,
            player_status="joined",
        )
        mock_campaign = Campaign(
            campaign_id=self.campaign_id,
            server_id=self.server_id,
            campaign_name=self.campaign_name,
        )
        mock_session.get.return_value = mock_player
        mock_session.execute.side_effect = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_campaign))
                )
            ),  # find campaign
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=MagicMock()))
                )
            ),  # check if joined -> yes
        ]

        # Act & Assert
        with pytest.raises(ValidationError):
            await player_manager.join_campaign(
                player_id=self.player_id,
                server_id=self.server_id,
                campaign_name=self.campaign_name,
            )


@pytest.mark.asyncio
class TestEndCampaign(BaseTestData):
    async def test_end_campaign_normal(
        self, player_manager: PlayerManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_player = Player(player_id=self.player_id, player_status="joined")
        mock_campaign = Campaign(campaign_id=self.campaign_id)
        mock_link = CampaignPlayerLink()

        mock_session.get.return_value = mock_player
        mock_session.execute.side_effect = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_campaign))
                )
            ),
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_link))
                )
            ),
        ]

        # Act
        result = await player_manager.end_campaign(
            self.player_id, self.server_id, self.campaign_name
        )

        # Assert
        assert result["player_status"] == "cmd"
        mock_session.add.assert_called_once_with(mock_player)
        mock_session.commit.assert_called_once()

    async def test_end_campaign_no_campaign_uses_last_active(
        self, player_manager: PlayerManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_player = Player(
            player_id=self.player_id,
            last_active_campaign=self.campaign_name,
            player_status="joined",
        )
        mock_campaign = Campaign(campaign_id=self.campaign_id)
        mock_link = CampaignPlayerLink()

        mock_session.get.return_value = mock_player
        mock_session.execute.side_effect = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_campaign))
                )
            ),
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_link))
                )
            ),
        ]

        # Act
        await player_manager.end_campaign(self.player_id, self.server_id)

        # Assert
        assert mock_player.player_status == "cmd"
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
class TestRemoveCampaign(BaseTestData):
    async def test_remove_campaign_normal(
        self, player_manager: PlayerManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_player = Player(player_id=self.player_id)
        mock_campaign = Campaign(
            campaign_id=self.campaign_id, campaign_name=self.campaign_name
        )
        mock_link = CampaignPlayerLink()

        mock_session.get.return_value = mock_player
        mock_session.execute.side_effect = [
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_campaign))
                )
            ),
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=mock_link))
                )
            ),
        ]

        # Act
        result = await player_manager.remove_campaign(
            self.player_id, self.server_id, self.campaign_name
        )

        # Assert
        assert result["status"] == "left"
        mock_session.delete.assert_called_once_with(mock_link)
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
class TestGetPlayerStatus(BaseTestData):
    async def test_get_player_status_normal(
        self, player_manager: PlayerManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_player = Player(
            player_id=self.player_id,
            username=self.username,
            campaigns=[],
            characters=[],
        )
        mock_session.get.return_value = mock_player

        # Act
        result = await player_manager.get_player(self.player_id)

        # Assert
        assert result["player_id"] == self.player_id
        assert result["username"] == self.username

    async def test_get_player_status_not_found(
        self, player_manager: PlayerManager, mock_session: AsyncMock
    ):
        # Arrange
        mock_session.get.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            await player_manager.get_player("nonexistent")
