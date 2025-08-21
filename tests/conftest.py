import asyncio
import uuid
from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
import pytest_asyncio
from discord.ext import commands
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from packages.backend.components.campaign_manager import CampaignManager
from packages.backend.components.character_manager import CharacterManager
from packages.backend.components.player_manager import PlayerManager
from packages.backend.components.server_manager import ServerSettingsManager
from packages.backend.main import app
from packages.shared.db import get_async_engine, get_async_session, initialize_schema
from packages.shared.models import Character, Player

asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

Managers = namedtuple("Managers", ["settings", "character", "player", "campaign"])


@pytest.fixture(scope="session")
def shared_mem_uri():
    """
    Shared in-memory SQLite DB URI
    """
    db_id = uuid.uuid4().hex
    # Correct format for shared in-memory SQLite database with async support
    shared_mem_uri = f"file:memdb{db_id}?mode=memory&cache=shared&uri=true"
    return shared_mem_uri


@pytest_asyncio.fixture(scope="session")
async def engine(shared_mem_uri):
    """
    Creates a single, session-scoped SQLAlchemy AsyncEngine and initializes the schema.
    """
    db_engine = get_async_engine(shared_mem_uri)
    await initialize_schema(db_engine)
    return db_engine


@pytest_asyncio.fixture(autouse=True)
async def clear_db_tables(engine):
    """
    Ensures a clean database state for each test by dropping and recreating all tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


@pytest_asyncio.fixture
async def session(engine):
    """
    Provides a clean database session for each test.
    Rolls back any changes after the test completes.
    """
    async with AsyncSession(engine) as db_session:
        yield db_session
        await db_session.rollback()  # Ensures test isolation


@pytest_asyncio.fixture
async def client(engine):
    """
    Provides an AsyncClient that is configured to use the test database.
    """

    async def get_test_session():
        async with AsyncSession(engine) as session:
            yield session

    app.dependency_overrides[get_async_session] = get_test_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def managers(session):
    """
    Initializes all manager instances with the async session.
    """
    ssm = ServerSettingsManager(session=session)
    cm = CharacterManager(session=session)
    pm = PlayerManager(session=session)
    cmpm = CampaignManager(session=session)
    return Managers(ssm, cm, pm, cmpm)


@pytest_asyncio.fixture
async def insert_player(session):
    """
    Fixture to insert a predefined player for use in tests.
    """

    async def _insert(player_id: str = "user-id-1", username: str = "Alice"):
        player = Player(player_id=player_id, username=username)
        session.add(player)
        await session.commit()
        await session.refresh(player)
        return player

    # player = await _insert
    return _insert


@pytest.fixture
def select_character(session):
    """
    Fixture to fetch a character row by ID.
    """

    async def _select_char(char_id: int):
        return await session.get(Character, char_id)

    return _select_char


@pytest.fixture
def select_player(session):
    """
    Fixture to fetch a player row by player_id.
    """

    async def _select_player(player_id: str = "user-id-1"):
        return await session.get(Player, player_id)

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
