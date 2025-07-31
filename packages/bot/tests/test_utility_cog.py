import pytest
from unittest.mock import AsyncMock, MagicMock
from packages.bot.cogs.utility_cog import UtilityCog

@pytest.mark.asyncio
async def test_getting_started_command():
    bot = MagicMock()
    cog = UtilityCog(bot)
    interaction = AsyncMock()
    await cog.getting_started.callback(cog, interaction)
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "getting started" in args[0].lower()
    assert kwargs.get("ephemeral") is True

@pytest.mark.asyncio
async def test_cost_command():
    bot = MagicMock()
    cog = UtilityCog(bot)
    interaction = AsyncMock()
    await cog.cost.callback(cog, interaction)
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "cost" in args[0].lower()
    assert kwargs.get("ephemeral") is True

@pytest.mark.asyncio
async def test_help_command():
    bot = MagicMock()
    cog = UtilityCog(bot)
    interaction = AsyncMock()
    await cog.help.callback(cog, interaction)
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "available commands" in args[0].lower()
    assert kwargs.get("ephemeral") is True