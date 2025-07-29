import pytest
from bot import bot


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


@pytest.fixture
def client():
    """Fixture to create a test client for the bot."""
    return bot  # Replace with actual bot initialization if needed


def test_bot_startup(client):
    """Test that the bot starts up without errors."""
    assert client is not None  # Ensure the bot client is initialized


@pytest.mark.asyncio
async def test_ping_command(client):
    """Test the /ping command response."""
    interaction = MockInteraction()
    await client.tree.get_command("ping").callback(interaction)
    expected_response = "Pong!"
    assert interaction.message == expected_response


@pytest.mark.asyncio
async def test_server_setup_permissions():
    class Perms:
        administrator = False
        manage_guild = False

    interaction = test_ping_command.__globals__["MockInteraction"](user_perms=Perms())
    await bot.tree.get_command("server-setup").callback(interaction)
    assert "You need Administrator or Manage Server permissions" in interaction.message
    assert interaction.ephemeral is True


@pytest.mark.asyncio
async def test_server_setkey_permissions():
    class Perms:
        administrator = False
        manage_guild = False

    interaction = test_ping_command.__globals__["MockInteraction"](user_perms=Perms())
    await bot.tree.get_command("server-setkey").callback(interaction, "dummy_key")
    assert "You need Administrator or Manage Server permissions" in interaction.message
    assert interaction.ephemeral is True


@pytest.mark.asyncio
async def test_server_setkey_success():
    class Perms:
        administrator = True
        manage_guild = True

    interaction = test_ping_command.__globals__["MockInteraction"](user_perms=Perms())
    await bot.tree.get_command("server-setkey").callback(interaction, "dummy_key")
    assert "API key securely stored" in interaction.message
    assert interaction.ephemeral is True
