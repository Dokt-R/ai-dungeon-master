from unittest.mock import MagicMock, patch

import pytest

from packages.bot.cogs import campaign_cog
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import CustomException
from tests.utils.factories import InteractionFactory
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
    cog.api_client.set_exception_override(
        "create_campaign", CustomException(ErrorCode.UNKNOWN)
    )

    interaction = InteractionFactory.admin_interaction()
    campaign_name = "test_campaign"

    await cog.new.callback(cog, interaction, campaign_name)
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.UNKNOWN.player_message in args[0]
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_campaign_join_http_error(cog):
    """Test campaign join command when HTTP request fails."""
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_exception_override(
        "join_campaign", CustomException(ErrorCode.UNKNOWN)
    )

    interaction = InteractionFactory.regular_interaction()
    campaign_name = "existing_campaign"

    await cog.join.callback(cog, interaction, campaign_name)
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.UNKNOWN.player_message in args[0]
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_campaign_continue_http_error(cog):
    """Test campaign continue command when HTTP request fails."""
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_exception_override(
        "continue_campaign", CustomException(ErrorCode.UNKNOWN)
    )

    interaction = InteractionFactory.regular_interaction()

    await cog.continue_.callback(cog, interaction)
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.UNKNOWN.player_message in args[0]
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_campaign_end_http_error(cog):
    """Test campaign end command when HTTP request fails."""
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_exception_override(
        "end_campaign", CustomException(ErrorCode.UNKNOWN)
    )

    interaction = InteractionFactory.regular_interaction()

    await cog.end.callback(cog, interaction)
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.UNKNOWN.player_message in args[0]
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_campaign_info_http_error(cog):
    """Test campaign info command when HTTP request fails."""
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_exception_override(
        "get_campaign_details", CustomException(ErrorCode.UNKNOWN)
    )

    interaction = InteractionFactory.admin_interaction()
    campaign_name = "info_test"

    await cog.info.callback(cog, interaction, campaign_name)
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.UNKNOWN.player_message in args[0]
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_campaign_info_404_error(cog):
    """Test campaign info command when campaign is not found."""
    from packages.shared.exceptions import NotFoundError as ApiNotFoundError

    interaction = InteractionFactory.admin_interaction()
    campaign_name = "nonexistent_campaign"

    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_exception_override(
        "get_campaign_details",
        ApiNotFoundError(ErrorCode.CAMPAIGN_NOT_FOUND, campaign_name=campaign_name),
    )

    await cog.info.callback(cog, interaction, campaign_name)

    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "nonexistent_campaign" in args[0]
    assert kwargs.get("ephemeral") is True


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
