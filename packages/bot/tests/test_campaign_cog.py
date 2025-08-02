import discord
from discord.ext import commands
import pytest
import os
import sys
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch
from packages.bot.cogs import campaign_cog

sys.modules["packages.backend.components.campaign_manager"] = mock.MagicMock()


@pytest.fixture
def bot():
    return MagicMock(spec=commands.Bot)


@pytest.fixture
def cog(bot):
    return campaign_cog.CampaignCog(bot)


@pytest.mark.asyncio
async def test_campaign_new_success(tmp_path, cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    interaction.response = AsyncMock()
    campaign_name = "test_campaign"
    campaign_dir = tmp_path / "data" / "campaigns" / campaign_name

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "created successfully" in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_new_duplicate(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={
                "detail": "A campaign named 'existing_campaign' already exists."
            }
        )
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to create campaign"
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_new_permission_denied(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = False
    interaction.user.guild_permissions.manage_guild = False
    interaction.response = AsyncMock()
    campaign_name = "test_campaign"

    await cog._handle_campaign_new(interaction, campaign_name)
    interaction.response.send_message.assert_called_once()
    assert "do not have permission" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_new_backend_error(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    interaction.response = AsyncMock()
    campaign_name = "test_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("backend error")
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to create campaign"
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_join_success(cog):
    interaction = MagicMock()
    interaction.user.id = 789
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_join_nonexistent(cog):
    interaction = MagicMock()
    interaction.user.id = 789
    interaction.response = AsyncMock()
    campaign_name = "nonexistent_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={"detail": "No campaign named 'nonexistent_campaign' exists."}
        )
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to join campaign"
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_join_backend_error(cog):
    interaction = MagicMock()
    interaction.user.id = 789
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("backend error")
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to join campaign"
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_continue_success(cog):
    interaction = MagicMock()
    interaction.user.id = 123
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(
            return_value={"narrative": "Resumed narrative"}
        )
        await cog._handle_campaign_continue(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "Resumed narrative" in interaction.response.send_message.call_args[0][0]


@pytest.mark.asyncio
async def test_campaign_continue_nonexistent(cog):
    interaction = MagicMock()
    interaction.user.id = 123
    interaction.response = AsyncMock()
    campaign_name = "nonexistent_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = AsyncMock(
            return_value={"detail": "Campaign does not exist"}
        )
        await cog._handle_campaign_continue(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to continue campaign"
            in interaction.response.send_message.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_campaign_continue_unexpected_error(cog):
    interaction = MagicMock()
    interaction.user.id = 123
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("unexpected error")
        await cog._handle_campaign_continue(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "Failed to continue campaign"
            in interaction.response.send_message.call_args[0][0]
        )
