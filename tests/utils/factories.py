import uuid
from datetime import datetime
from packages.shared.models import Player, Campaign, Character

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
    from unittest.mock import MagicMock
    import uuid

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


def make_discord_cog(bot=None, **overrides):
    """Factory for Discord cog objects (not persisted)."""
    from unittest.mock import MagicMock
    import uuid

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
        self.response = self
        self.user = type(
            "User",
            (),
            {
                "guild_permissions": type("Perms", (), {"administrator": is_admin, "manage_guild": is_admin})()
            },
        )()
        self.guild_id = guild_id
        self.message = None
        self.ephemeral = None

    async def send_message(self, message, ephemeral=False):
        self.message = message
        self.ephemeral = ephemeral
