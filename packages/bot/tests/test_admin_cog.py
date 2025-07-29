import pytest
import discord
from unittest.mock import AsyncMock, patch, MagicMock
from packages.bot.cogs.admin_cog import AdminCog

@pytest.mark.asyncio
async def test_server_setkey_success(monkeypatch):
    bot = MagicMock()
    cog = AdminCog(bot)
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.guild_id = 123
    interaction.response.send_message = AsyncMock()

    # Patch httpx.AsyncClient
    class MockResponse:
        status_code = 200
        text = "OK"
    async def mock_put(*args, **kwargs):
        return MockResponse()
    with patch("httpx.AsyncClient.put", new=mock_put):
        await cog.server_setkey(interaction, "testkey")
        interaction.response.send_message.assert_awaited_with(
            "API key securely stored for this server.", ephemeral=True
        )

@pytest.mark.asyncio
async def test_server_setkey_failure(monkeypatch):
    bot = MagicMock()
    cog = AdminCog(bot)
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.guild_id = 123
    interaction.response.send_message = AsyncMock()

    class MockResponse:
        status_code = 500
        text = "Internal Server Error"
    async def mock_put(*args, **kwargs):
        return MockResponse()
    with patch("httpx.AsyncClient.put", new=mock_put):
        await cog.server_setkey(interaction, "testkey")
        interaction.response.send_message.assert_awaited_with(
            "Failed to store API key: Internal Server Error", ephemeral=True
        )