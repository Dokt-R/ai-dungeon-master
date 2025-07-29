import pytest
import pytest_asyncio
import asyncio
import os

import discord
from discord.ext import commands
from packages.bot.cogs.admin_cog import AdminCog

import sys
import importlib

# Import the bot and cog loading from main.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
main = importlib.import_module("main")


class MockInteraction:
    def __init__(self, user_perms=None, guild_id="123"):
        self.response = self
        self.user = type(
            "User",
            (),
            {
                "guild_permissions": user_perms
                or type("Perms", (), {"administrator": True, "manage_guild": True})()
            },
        )()
        self.guild_id = guild_id
        self.message = None
        self.ephemeral = None

    async def send_message(self, message, ephemeral=False):
        self.message = message
        self.ephemeral = ephemeral


@pytest_asyncio.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def client():
    # Create a new bot instance for testing
    intents = discord.Intents.default()
    intents.messages = True
    intents.guilds = True
    intents.message_content = True
    bot = commands.Bot(command_prefix="/", intents=intents, application_id=123)
    await bot.load_extension("packages.bot.cogs.utility_cog")
    await bot.load_extension("packages.bot.cogs.admin_cog")
    return bot


def test_bot_startup(client):
    """Test that the bot starts up without errors."""
    assert client is not None  # Ensure the bot client is initialized


@pytest.mark.asyncio
async def test_ping_command(client):
    """Test the /ping command response."""
    interaction = MockInteraction()
    cmd = None
    for command in client.tree.get_commands():
        if command.name == "ping":
            cmd = command
            break
    assert cmd is not None
    await cmd.callback(cmd, interaction)
    expected_response = "Pong!"
    assert interaction.message == expected_response


@pytest.mark.asyncio
async def test_server_setup_permissions(client):
    class Perms:
        administrator = False
        manage_guild = False

    interaction = MockInteraction(user_perms=Perms())
    cmd = None
    for command in client.tree.get_commands():
        if command.name == "server-setup":
            cmd = command
            break
    assert cmd is not None
    await cmd.callback(cmd, interaction)
    assert "You need Administrator or Manage Server permissions" in interaction.message
    assert interaction.ephemeral is True


@pytest.mark.asyncio
async def test_server_setkey_permissions(client):
    class Perms:
        administrator = False
        manage_guild = False

    interaction = MockInteraction(user_perms=Perms())
    cmd = None
    for command in client.tree.get_commands():
        if command.name == "server-setkey":
            cmd = command
            break
    assert cmd is not None
    cog = client.get_cog("AdminCog")
    assert cog is not None
    await cog.server_setkey.callback(cog, interaction, "dummy_key")
    assert "You need Administrator or Manage Server permissions" in interaction.message
    assert interaction.ephemeral is True


@pytest.mark.asyncio
async def test_server_setkey_success(client):
    class Perms:
        administrator = True
        manage_guild = True

    interaction = MockInteraction(user_perms=Perms())
    cmd = None
    for command in client.tree.get_commands():
        if command.name == "server-setkey":
            cmd = command
            break
    assert cmd is not None
    cog = client.get_cog("AdminCog")
    assert cog is not None
    # Patch httpx.AsyncClient.put to simulate backend success
    import httpx
    from unittest.mock import patch

    class MockResponse:
        status_code = 200
        text = "OK"

    async def mock_put(*args, **kwargs):
        return MockResponse()

    with patch("httpx.AsyncClient.put", new=mock_put):
        await cog.server_setkey.callback(cog, interaction, "dummy_key")
        assert "API key securely stored" in interaction.message
    assert interaction.ephemeral is True
