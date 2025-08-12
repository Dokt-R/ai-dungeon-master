import pytest
import pytest_asyncio
import uuid
import asyncio
from collections import namedtuple
from sqlmodel import Session, SQLModel
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
import discord
from discord.ext import commands

from packages.backend.main import app
from packages.backend.components.campaign_manager import CampaignManager
from packages.backend.components.character_manager import CharacterManager
from packages.backend.components.player_manager import PlayerManager
from packages.backend.components.server_manager import ServerSettingsManager
from packages.shared.db import get_engine, initialize_schema, get_session
from packages.shared.models import Player, Character


Managers = namedtuple("Managers", ["settings", "character", "player", "campaign"])


@pytest.fixture(scope="session")
def shared_mem_uri():
    """
    Shared in-memory SQLite DB URI
    """
    db_id = uuid.uuid4().hex
    shared_mem_uri = f"file:{db_id}?mode=memory&cache=shared"
    return shared_mem_uri


@pytest.fixture(scope="session")
def engine(shared_mem_uri):
    """
    Creates a single, session-scoped SQLAlchemy Engine and initializes the schema.
    """
    db_engine = get_engine(shared_mem_uri)
    initialize_schema(db_engine)
    return db_engine


@pytest.fixture(autouse=True)
def clear_db_tables(engine):
    """
    Ensures a clean database state for each test by dropping and recreating all tables.
    """
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


@pytest.fixture
def session(engine):
    """
    Provides a clean database session for each test.
    Rolls back any changes after the test completes.
    """
    with Session(engine) as db_session:
        yield db_session
        db_session.rollback()  # Ensures test isolation


@pytest.fixture
def client(engine):
    """
    Provides a TestClient that is configured to use the test database.
    """

    def get_test_engine():
        yield engine

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def managers(session):
    """
    Initializes all manager instances with the session-scoped session.
    """
    ssm = ServerSettingsManager(session=session)
    cm = CharacterManager(session=session)
    pm = PlayerManager(session=session)
    cmpm = CampaignManager(session=session)
    return Managers(ssm, cm, pm, cmpm)


@pytest.fixture
def insert_player(session):
    """
    Fixture to insert a predefined player for use in tests.
    """

    def _insert(player_id: str = "user-id-1", username: str = "Alice"):
        player = Player(player_id=player_id, username=username)
        session.add(player)
        session.commit()
        return player

    return _insert


@pytest.fixture
def select_character(session):
    """
    Fixture to fetch a character row by ID.
    """

    def _select_char(char_id: int):
        return session.get(Character, char_id)

    return _select_char


@pytest.fixture
def select_player(session):
    """
    Fixture to fetch a player row by player_id.
    """

    def _select_player(player_id: str = "user-id-1"):
        return session.get(Player, player_id)

    return _select_player


# region ----------------- [ Discord Specific Fixtures ] -----------------
@pytest.fixture
def mock_bot():
    """Fixture that provides a mocked bot instance."""
    return MagicMock()


@pytest.fixture
def mock_interaction():
    """Fixture that provides a mocked Discord interaction."""
    interaction = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()
    interaction.guild_id = 123
    return interaction


@pytest.fixture
def mock_member():
    """Fixture that provides a MockMember class for testing."""

    class MockMember:
        def __init__(
            self, member_id: int = 12345, name: str = "TestUser", bot: bool = True
        ):
            self.id = member_id
            self.name = name
            self.bot = bot

    return MockMember


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


# endregion
