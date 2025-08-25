from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.bot.cogs import campaign_cog
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import CustomException, ValidationError
from tests.utils.factories import HttpMockFactory, InteractionFactory, MockInteraction
from tests.utils.mock_api_client import MockApiClient


@pytest.fixture
def bot():
    return MagicMock()


@pytest.fixture
def cog(bot):
    return campaign_cog.CampaignCog(bot)


@pytest.mark.asyncio
async def test_campaign_new_http_error(cog):
    """Test campaign new command when HTTP request fails."""
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_exception_override("create_campaign", CustomException())

    interaction = InteractionFactory.admin_interaction()
    campaign_name = "test_campaign"

    with pytest.raises(ValidationError) as excinfo:
        await cog._handle_campaign_new(interaction, campaign_name)
    assert ErrorCode.UNKNOWN.player_message in str(excinfo.value)


@pytest.mark.asyncio
async def test_campaign_join_http_error(cog):
    """Test campaign join command when HTTP request fails."""
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_exception_override("join_campaign", CustomException())

    interaction = MockInteraction()
    interaction.user.id = 789
    campaign_name = "existing_campaign"

    with pytest.raises(ValidationError) as excinfo:
        await cog._handle_campaign_join(interaction, campaign_name)
    assert ErrorCode.UNKNOWN.player_message in str(excinfo.value)


@pytest.mark.asyncio
async def test_campaign_continue_http_error(cog):
    """Test campaign continue command when HTTP request fails."""
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_exception_override("continue_campaign", CustomException())

    interaction = MockInteraction()
    interaction.user.id = 1113
    interaction.guild.id = 2224

    with pytest.raises(ValidationError) as excinfo:
        await cog._handle_campaign_continue(interaction)
    assert ErrorCode.UNKNOWN.player_message in str(excinfo.value)


@pytest.mark.asyncio
async def test_campaign_end_http_error(cog):
    """Test campaign end command when HTTP request fails."""
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_exception_override("end_campaign", CustomException())

    interaction = MockInteraction()
    interaction.user.id = 2002
    interaction.guild.id = 3002

    with pytest.raises(ValidationError) as excinfo:
        await cog._handle_campaign_end(interaction)
    assert ErrorCode.UNKNOWN.player_message in str(excinfo.value)


@pytest.mark.asyncio
async def test_campaign_info_http_error(cog):
    """Test campaign info command when HTTP request fails."""
    interaction = AsyncMock()
    campaign_name = "info_test"
    interaction.guild.id = "server123"

    with patch("httpx.AsyncClient.get", side_effect=CustomException()):
        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_info(interaction, campaign_name)
        assert ErrorCode.UNKNOWN.player_message in str(excinfo.value)


@pytest.mark.asyncio
async def test_campaign_info_404_error(cog):
    """Test campaign info command when campaign is not found."""
    interaction = InteractionFactory.admin_interaction()
    campaign_name = "nonexistent_campaign"
    interaction.guild.id = "server123"

    with HttpMockFactory.mock_not_found():
        await cog._handle_campaign_info(interaction, campaign_name)

    interaction.response.send_message.assert_called_once()
    message = interaction.response.send_message.call_args[0][0]
    assert "not found" in message.lower()


@pytest.mark.asyncio
async def test_campaign_delete_http_error(cog):
    """Test campaign delete command when HTTP request fails."""
    interaction = InteractionFactory.admin_interaction()
    campaign_name = "delete_me"

    with patch("httpx.AsyncClient.request", side_effect=CustomException()):
        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "are you sure" in interaction.response.send_message.call_args[0][0].lower()
        )
