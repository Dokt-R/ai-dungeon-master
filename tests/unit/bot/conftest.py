import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
import pytest_asyncio
from discord.ext import commands

from tests.utils.factories import MemberFactory
from tests.utils.mock_api_client import MockApiClient


@pytest.fixture
def mock_bot():
    """Fixture that provides a mocked bot instance."""
    bot = MagicMock(spec=commands.Bot, autospec=True)
    bot.user = MemberFactory.bot(name="TestBot", id=99999)
    return bot


@pytest.fixture
def mock_admin_cog(mock_bot):
    """Pre-built AdminCog with mocked API client - avoids expensive httpx.AsyncClient creation"""
    # Mock the ApiClient class before AdminCog creation
    with patch("packages.bot.cogs.admin_cog.ApiClient") as mock_api_class:
        # Make ApiClient.__init__ return a lightweight mock
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance

        # Now create AdminCog without the expensive httpx client
        from packages.bot.cogs.admin_cog import AdminCog

        cog = AdminCog(mock_bot)

        # Replace with your actual MockApiClient
        cog.api_client = MockApiClient()

        return cog


@pytest.fixture
def mock_character_cog(mock_bot):
    """Pre-built CharacterCog with mocked API client - avoids expensive httpx.AsyncClient creation"""
    # Mock the ApiClient class before CharacterCog creation
    with patch("packages.bot.cogs.character_cog.ApiClient") as mock_api_class:
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance

        from packages.bot.cogs.character_cog import CharacterCog

        cog = CharacterCog(mock_bot)

        cog.api_client = MockApiClient()
        return cog


@pytest.fixture
def mock_campaign_cog(mock_bot):
    """Pre-built CampaignCog with mocked API client - avoids expensive httpx.AsyncClient creation"""
    # Mock the ApiClient class before CampaignCog creation
    with patch("packages.bot.cogs.campaign_cog.ApiClient") as mock_api_class:
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance

        from packages.bot.cogs.campaign_cog import CampaignCog

        cog = CampaignCog(mock_bot)

        cog.api_client = MockApiClient()
        return cog


@pytest.fixture
def mock_utility_cog(mock_bot):
    """Pre-built UtilityCog with mocked API client - avoids expensive httpx.AsyncClient creation"""
    # Mock the ApiClient class before UtilityCog creation
    with patch("packages.bot.cogs.utility_cog.ApiClient") as mock_api_class:
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance
        from packages.bot.cogs.utility_cog import UtilityCog

        cog = UtilityCog(mock_bot)
        cog.api_client = MockApiClient()
        return cog


@pytest.fixture
def mock_health_cog(mock_bot):
    """Pre-built HealthCog with mocked API client - avoids expensive httpx.AsyncClient creation"""
    # Mock the ApiClient class before HealthCog creation
    with patch("packages.bot.cogs.health_cog.ApiClient") as mock_api_class:
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance

        from packages.bot.cogs.health_cog import HealthCog

        cog = HealthCog(mock_bot)
        cog.api_client = MockApiClient()
        return cog


@pytest.fixture
def mock_action_cog(mock_bot):
    """Pre-built ActionCog with mocked API client - avoids expensive httpx.AsyncClient creation"""
    # Mock the ApiClient class before ActionCog creation
    with patch("packages.bot.cogs.action_cog.ApiClient") as mock_api_class:
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance

        from packages.bot.cogs.action_cog import ActionCog

        cog = ActionCog(mock_bot)
        cog.api_client = MockApiClient()
        return cog


@pytest.fixture
def mock_voice_cog(mock_bot):
    """Pre-built VoiceCog with mocked dependencies - follows established pattern"""
    with patch("packages.bot.cogs.voice_cog.ApiClient") as mock_api_class:
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance

        from packages.bot.cogs.voice_cog import VoiceCog

        cog = VoiceCog(mock_bot)
        cog.api_client = MockApiClient()
        return cog


@pytest.fixture
def mock_member():
    """Alternative that modifies your existing approach"""

    class MockMember:
        def __init__(
            self,
            member_id: int = 12345,
            name: str = "TestUser",
            bot: bool = False,
            **kwargs,
        ):
            # Your existing attributes
            self.id = member_id
            self.name = name
            self.bot = bot

            # Add missing Discord.Member attributes
            self.discriminator = kwargs.get("discriminator", "0001")
            self.nick = kwargs.get("nick", None)
            self.display_name = self.nick or self.name
            self.mention = f"<@{self.id}>"
            self.avatar = kwargs.get("avatar", None)
            self.joined_at = kwargs.get("joined_at", datetime.now(timezone.utc))

            # Guild setup
            self.guild = MagicMock(spec=discord.Guild)
            self.guild.id = kwargs.get("guild_id", 67890)
            self.guild.name = kwargs.get("guild_name", "Test Server")

            # Permissions
            self.guild_permissions = MagicMock()
            self.guild_permissions.administrator = kwargs.get("is_admin", False)
            self.guild_permissions.manage_guild = kwargs.get("can_manage_server", True)

            # Mock methods
            self.send = AsyncMock()
            self.add_roles = AsyncMock()
            self.kick = AsyncMock()
            self.ban = AsyncMock()

        # Override __class__ property to make isinstance work
        @property
        def __class__(self):
            return discord.Member

    return MockMember


# Convenience fixtures for common member types
@pytest.fixture
def regular_member(mock_member):
    """Regular member with basic permissions"""
    return mock_member(name="RegularUser", bot=False, can_manage_server=False)


@pytest.fixture
def admin_member(mock_member):
    """Admin member with full permissions"""
    return mock_member(name="AdminUser", bot=False, is_admin=True)


@pytest.fixture
def bot_member(mock_member):
    """Bot member"""
    return mock_member(name="TestBot", bot=True)


# Updated interaction fixture using your enhanced MockMember
@pytest.fixture
def mock_interaction(mock_member):
    """Fixture that provides a mocked Discord interaction with proper Member."""
    interaction = MagicMock(spec=discord.Interaction)

    # Create member using your MockMember class
    member = mock_member(member_id=123, name="TestUser", can_manage_server=True)

    # Set interaction properties
    interaction.user = member
    interaction.guild = member.guild
    interaction.guild_id = member.guild.id

    # Mock async methods
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    return interaction


@pytest.fixture
def mock_interaction_member():
    """Simpler version - everything in one fixture"""
    interaction = MagicMock(spec=discord.Interaction)

    # Create the member that passes isinstance check
    member = MagicMock(spec=discord.Member)
    member.__class__ = discord.Member  # Key line!
    member.id = 123
    member.name = "TestUser"
    member.display_name = "TestUser"
    member.mention = "<@123>"

    # Create guild
    guild = MagicMock(spec=discord.Guild)
    guild.id = 456
    guild.name = "Test Server"

    # Connect member to guild
    member.guild = guild
    member.guild_permissions = MagicMock()
    member.guild_permissions.manage_guild = True

    # Set interaction properties
    interaction.user = member
    interaction.guild = guild
    interaction.guild_id = guild.id

    # Mock async methods
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    return interaction


# For different permission levels
@pytest.fixture
def mock_interaction_admin(mock_interaction):
    """Interaction with admin member"""
    interaction = mock_interaction
    interaction.user.guild_permissions.administrator = True
    return interaction


@pytest.fixture
def mock_interaction_no_perms(mock_interaction):
    """Interaction with member that has no permissions"""
    interaction = mock_interaction
    interaction.user.guild_permissions.administrator = False
    interaction.user.guild_permissions.manage_guild = False
    return interaction


@pytest.fixture
def mock_response():
    """Fixture that provides a MockResponse class for testing."""

    class MockResponse:
        def __init__(self, status_code=200, text="OK", json_data=None):
            self.status_code = status_code
            self.text = text
            self._json_data = json_data or {}

        async def raise_for_status(self):
            pass

        def json(self):
            return self._json_data

    return MockResponse


@pytest_asyncio.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def bot_client():
    """Create a Discord bot client for testing."""
    intents = discord.Intents.default()
    intents.messages = True
    intents.guilds = True
    intents.message_content = True
    bot = commands.Bot(command_prefix="/", intents=intents, application_id=123)
    await bot.load_extension("packages.bot.cogs.admin_cog")
    await bot.load_extension("packages.bot.cogs.character_cog")
    await bot.load_extension("packages.bot.cogs.campaign_cog")
    await bot.load_extension("packages.bot.cogs.utility_cog")
    return bot
