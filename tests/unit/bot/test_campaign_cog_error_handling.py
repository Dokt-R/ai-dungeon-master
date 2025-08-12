import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.bot.cogs import campaign_cog


@pytest.fixture
def bot():
    return MagicMock()


@pytest.fixture
def cog(bot):
    return campaign_cog.CampaignCog(bot)


@pytest.mark.asyncio
async def test_campaign_new_http_error(cog):
    """Test campaign new command when HTTP request fails."""
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    interaction.response = AsyncMock()
    campaign_name = "test_campaign"

    with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "unexpected error" in interaction.response.send_message.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_campaign_join_http_error(cog):
    """Test campaign join command when HTTP request fails."""
    interaction = MagicMock()
    interaction.user.id = 789
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "failed to join campaign" in interaction.response.send_message.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_campaign_continue_http_error(cog):
    """Test campaign continue command when HTTP request fails."""
    interaction = MagicMock()
    interaction.user.id = 1113
    interaction.guild.id = 2224
    interaction.response = AsyncMock()
    
    with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
        await cog._handle_campaign_continue(interaction)
        interaction.response.send_message.assert_called_once()
        assert "failed to continue campaign" in interaction.response.send_message.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_campaign_end_http_error(cog):
    """Test campaign end command when HTTP request fails."""
    interaction = MagicMock()
    interaction.user.id = 2002
    interaction.guild.id = 3002
    interaction.response = AsyncMock()
    
    with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
        await cog._handle_campaign_end(interaction)
        interaction.response.send_message.assert_called_once()
        assert "failed to exit campaign" in interaction.response.send_message.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_campaign_info_http_error(cog):
    """Test campaign info command when HTTP request fails."""
    interaction = AsyncMock()
    campaign_name = "info_test"
    interaction.guild.id = "server123"

    with patch("httpx.AsyncClient.get", side_effect=Exception("Network error")):
        await cog._handle_campaign_info(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "unexpected error" in interaction.response.send_message.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_campaign_info_404_error(cog):
    """Test campaign info command when campaign is not found."""
    interaction = AsyncMock()
    campaign_name = "nonexistent_campaign"
    interaction.guild.id = "server123"

    # Mock HTTP 404 response
    from httpx import HTTPStatusError
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    
    with patch("httpx.AsyncClient.get", side_effect=HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)):
        await cog._handle_campaign_info(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "not found" in interaction.response.send_message.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_campaign_delete_http_error(cog):
    """Test campaign delete command when HTTP request fails."""
    interaction = AsyncMock()
    interaction.user.guild_permissions.administrator = True
    campaign_name = "delete_me"

    with patch("httpx.AsyncClient.request", side_effect=Exception("Network error")):
        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "are you sure" in interaction.response.send_message.call_args[0][0].lower()