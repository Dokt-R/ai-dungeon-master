from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from packages.bot.cogs.campaign_cog import CampaignCog
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import NotFoundError, ValidationError

pytestmark = pytest.mark.skip(reason="Edge cases that need fixing to run properly")


@pytest.fixture
def bot():
    return MagicMock()


@pytest.fixture
def cog(bot):
    return CampaignCog(bot)


@pytest.mark.asyncio
async def test_campaign_create_duplicate(cog):
    """Test creating a duplicate campaign (Edge Case 1)."""
    interaction = AsyncMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(
            return_value={"detail": "Campaign already exists"}
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_new(interaction, campaign_name)

        assert "Campaign already exists" in str(excinfo.value)


@pytest.mark.asyncio
async def test_campaign_join_nonexistent(cog):
    """Test joining a non-existent campaign (Edge Case 4)."""
    interaction = AsyncMock()
    interaction.user.id = 123
    interaction.guild.id = 456
    campaign_name = "nonexistent_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json = AsyncMock(return_value={"detail": "Campaign not found"})
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(NotFoundError) as excinfo:
            await cog._handle_campaign_join(interaction, campaign_name)

        assert "Campaign not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_campaign_continue_no_active(cog):
    """Test continuing without an active campaign (Edge Case 6)."""
    interaction = AsyncMock()
    interaction.user.id = 123
    interaction.guild.id = 456

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json = AsyncMock(
            return_value={"detail": "No active campaign found"}
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(NotFoundError) as excinfo:
            await cog._handle_campaign_continue(interaction)

        assert "No active campaign found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_campaign_delete_active(cog):
    """Test deleting an active campaign (Edge Case 9)."""
    interaction = AsyncMock()
    interaction.user.guild_permissions.administrator = True
    interaction.guild.id = 456
    campaign_name = "active_campaign"

    # Mock the button callback
    async def mock_callback(interaction: AsyncMock):
        await interaction.response.defer(ephemeral=True)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(
            return_value={"detail": "Cannot delete active campaign"}
        )
        raise httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )

    with patch.object(
        cog, "_create_delete_confirmation_callback", return_value=mock_callback
    ):
        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()

        # Simulate button click
        button_interaction = AsyncMock()
        with pytest.raises(ValidationError) as excinfo:
            try:
                await mock_callback(button_interaction)
            except httpx.HTTPStatusError as e:
                await cog._handle_delete_error(button_interaction, e)

        assert "Cannot delete active campaign" in str(excinfo.value)


@pytest.mark.asyncio
async def test_campaign_info_invalid_id(cog):
    """Test requesting info for invalid campaign ID (Edge Case 10)."""
    interaction = AsyncMock()
    campaign_name = "invalid_id"
    interaction.guild.id = "server123"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(return_value={"detail": "Invalid campaign ID"})
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_info(interaction, campaign_name)

        assert "Invalid campaign ID" in str(excinfo.value)


@pytest.mark.asyncio
async def test_discord_generic_exception_fallback(cog):
    """Test Discord generic exception fallback (Edge Case 12)."""
    interaction = AsyncMock()
    interaction.user.id = 123
    interaction.guild.id = 456
    campaign_name = "test_campaign"

    # Test with _handle_campaign_new
    with patch("httpx.AsyncClient.post", side_effect=Exception("Generic error")):
        # Since the decorator handles the exception, we check the message sent
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            ErrorCode.UNKNOWN.player_message
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_join_user_already_joined(cog):
    """Test user already in campaign (Edge Case 5)."""
    interaction = AsyncMock()
    interaction.user.id = 123
    interaction.guild.id = 456
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(
            return_value={"detail": "User already in campaign"}
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_join(interaction, campaign_name)

        assert "User already in campaign" in str(excinfo.value)
