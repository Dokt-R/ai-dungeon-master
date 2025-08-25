import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from httpx import HTTPStatusError

from packages.shared.models import Campaign, Character, Player

# Optional: if you're using SQLModel for these, adjust imports accordingly


def make_player(player_id: str = None, username: str = None, **overrides) -> Player:
    """Factory for Player objects (not persisted)."""
    return Player(
        player_id=player_id or str(uuid.uuid4()),
        username=username or f"user_{uuid.uuid4().hex[:6]}",
        created_at=datetime.utcnow(),
        campaigns=[],
        characters=[],
        **overrides,
    )


def make_campaign(
    campaign_id: str = None, campaign_name: str = None, **overrides
) -> Campaign:
    """Factory for Campaign objects (not persisted)."""
    return Campaign(
        campaign_id=campaign_id or str(uuid.uuid4()),
        campaign_name=campaign_name or f"campaign_{uuid.uuid4().hex[:6]}",
        created_at=datetime.utcnow(),
        **overrides,
    )


# Discord-related factories
def make_discord_interaction(
    user_id=None, guild_id=None, is_admin=False, is_manage_guild=False, **overrides
):
    """Factory for Discord interaction objects (not persisted)."""
    import uuid
    from unittest.mock import MagicMock

    interaction = MagicMock()
    interaction.user.id = user_id or str(uuid.uuid4())
    interaction.guild.id = guild_id or str(uuid.uuid4())
    interaction.user.guild_permissions.administrator = is_admin
    interaction.user.guild_permissions.manage_guild = is_manage_guild
    interaction.response = MagicMock()
    interaction.followup = MagicMock()
    interaction.channel = MagicMock()
    interaction.data = {}

    # Add any overrides
    for key, value in overrides.items():
        setattr(interaction, key, value)

    return interaction


def make_discord_member(user_id=None, display_name=None, bot=False, **overrides):
    """Factory for Discord member objects (not persisted)."""
    import uuid
    from unittest.mock import MagicMock

    member = MagicMock()
    member.id = user_id or str(uuid.uuid4())
    member.display_name = display_name or f"user_{uuid.uuid4().hex[:6]}"
    member.bot = bot

    # Add any overrides
    for key, value in overrides.items():
        setattr(member, key, value)

    return member


def make_discord_cog(bot=None, **overrides):
    """Factory for Discord cog objects (not persisted)."""
    import uuid
    from unittest.mock import MagicMock

    cog = MagicMock()
    cog.bot = bot or MagicMock()
    cog.qualified_name = f"Cog_{uuid.uuid4().hex[:6]}"

    # Add any overrides
    for key, value in overrides.items():
        setattr(cog, key, value)

    return cog


def make_character(
    character_id: str = None, name: str = None, **overrides
) -> Character:
    """Factory for Character objects (not persisted)."""
    return Character(
        character_id=character_id or str(uuid.uuid4()),
        name=name or f"char_{uuid.uuid4().hex[:6]}",
        created_at=datetime.utcnow(),
        **overrides,
    )


# ---------- Discord Test Specific Factories ----------


class MockInteraction:
    """Mock Discord interaction for testing."""

    def __init__(self, guild_id="123", is_admin=True):
        from unittest.mock import AsyncMock

        self.response = AsyncMock()
        self.response.send_message = AsyncMock()
        self.followup = AsyncMock()
        self.followup.send = AsyncMock()
        self.user = MockMember(user_id="123", is_admin=is_admin)
        self.guild = type("Guild", (), {"id": guild_id})()
        self.guild_id = guild_id
        self.message = None
        self.ephemeral = None
        self.data = {}


class MockMember:
    """Mock Discord member for testing."""

    def __init__(
        self, user_id="123", display_name="TestUser", is_admin=True, bot=False
    ):
        self.id = user_id
        self.display_name = display_name
        self.bot = bot
        self.guild_permissions = type(
            "Perms", (), {"administrator": is_admin, "manage_guild": is_admin}
        )()

    @property
    def __class__(self):
        return discord.Member


def patch_isinstance_for_testing():
    """Patch isinstance to make MockMember pass as discord.Member for testing."""
    from unittest.mock import patch

    import discord

    original_isinstance = isinstance

    def mock_isinstance(obj, cls):
        if cls == discord.Member and isinstance(obj, MockMember):
            return True
        return original_isinstance(obj, cls)

    return patch("builtins.isinstance", side_effect=mock_isinstance)


class MemberFactory:
    """Factory for creating Discord Members - USE THIS for most tests"""

    @staticmethod
    def create(**kwargs):
        """Create a Member that passes isinstance checks"""

        class MockMember:
            def __init__(self, **attrs):
                # Default values
                defaults = {
                    "id": "12345",
                    "name": "TestUser",
                    "bot": False,
                    "discriminator": "0001",
                    "nick": None,
                    "avatar": None,
                    "joined_at": datetime.now(timezone.utc),
                    "guild_id": "67890",
                    "guild_name": "Test Server",
                    "is_admin": False,
                    "can_manage_server": True,
                    "can_manage_messages": False,
                }
                defaults.update(attrs)

                # Set basic attributes
                self.id = defaults["id"]
                self.name = defaults["name"]
                self.bot = defaults["bot"]
                self.discriminator = defaults["discriminator"]
                self.nick = defaults["nick"]
                self.avatar = defaults["avatar"]
                self.joined_at = defaults["joined_at"]

                # Computed properties
                self.display_name = self.nick or self.name
                self.mention = f"<@{self.id}>"

                # Guild setup
                self.guild = MagicMock(spec=discord.Guild)
                self.guild.id = defaults["guild_id"]
                self.guild.name = defaults["guild_name"]

                # Permissions
                self.guild_permissions = MagicMock()
                self.guild_permissions.administrator = defaults["is_admin"]
                self.guild_permissions.manage_guild = defaults["can_manage_server"]
                self.guild_permissions.manage_messages = defaults["can_manage_messages"]

                # Mock async methods
                self.send = AsyncMock()
                self.add_roles = AsyncMock()
                self.kick = AsyncMock()
                self.ban = AsyncMock()

            @property
            def __class__(self):
                return discord.Member

        return MockMember(**kwargs)

    @staticmethod
    def admin(**kwargs):
        """Shortcut for admin member"""
        defaults = {"is_admin": True, "name": "AdminUser"}
        defaults.update(kwargs)
        return MemberFactory.create(**defaults)

    @staticmethod
    def regular(**kwargs):
        """Shortcut for regular member"""
        defaults = {
            "is_admin": False,
            "can_manage_server": False,
            "name": "RegularUser",
        }
        defaults.update(kwargs)
        return MemberFactory.create(**defaults)

    @staticmethod
    def bot(**kwargs):
        """Shortcut for bot member"""
        defaults = {"bot": True, "name": "BotUser"}
        defaults.update(kwargs)
        return MemberFactory.create(**defaults)


class InteractionFactory:
    """Factory for creating Discord Interactions"""

    @staticmethod
    def create(member=None, **kwargs):
        """Create an interaction with a member"""
        if member is None:
            member = MemberFactory.create()

        interaction = MagicMock(spec=discord.Interaction)
        interaction.user = member
        interaction.guild = member.guild
        interaction.guild_id = member.guild.id

        # Mock response methods
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.edit_original_response = AsyncMock()

        # Override with kwargs
        for key, value in kwargs.items():
            setattr(interaction, key, value)

        return interaction

    @staticmethod
    def admin_interaction(**kwargs):
        """Interaction with admin member"""
        admin = MemberFactory.admin()
        return InteractionFactory.create(member=admin, **kwargs)

    @staticmethod
    def regular_interaction(**kwargs):
        """Interaction with regular member"""
        regular = MemberFactory.regular()
        return InteractionFactory.create(member=regular, **kwargs)


class HttpMockFactory:
    """Factory for creating different HTTP mock scenarios"""

    @staticmethod
    @contextmanager
    def mock_status_code(status_code, response_text="", response_json=None):
        """Mock specific HTTP status codes"""
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.text = response_text
        mock_response.headers = {}

        if response_json:
            mock_response.json.return_value = response_json

        if status_code >= 400:
            # Create HTTP error for error status codes
            error = HTTPStatusError(
                message=response_text or f"HTTP {status_code}",
                request=MagicMock(),
                response=mock_response,
            )
            with patch("httpx.AsyncClient.request", side_effect=error):
                yield mock_response
        else:
            # Success response
            with patch("httpx.AsyncClient.request", return_value=mock_response):
                yield mock_response

    @staticmethod
    @contextmanager
    def mock_success(json_data=None, text_data="OK"):
        """Mock successful HTTP response"""
        with HttpMockFactory.mock_status_code(200, text_data, json_data) as response:
            yield response

    @staticmethod
    @contextmanager
    def mock_not_found(message="Not Found"):
        """Mock 404 Not Found"""
        with HttpMockFactory.mock_status_code(404, message) as response:
            yield response

    @staticmethod
    @contextmanager
    def mock_server_error(message="Internal Server Error"):
        """Mock 500 Server Error"""
        with HttpMockFactory.mock_status_code(500, message) as response:
            yield response

    @staticmethod
    @contextmanager
    def mock_custom_exception(exception_class, *args, **kwargs):
        """Mock custom exceptions"""
        with patch(
            "httpx.AsyncClient.request", side_effect=exception_class(*args, **kwargs)
        ):
            yield
