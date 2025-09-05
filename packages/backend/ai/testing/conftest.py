import asyncio
import uuid
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from packages.backend.ai.testing.factories import create_test_character
from packages.backend.components.game_state_manager import GameStateService
from packages.shared.db import get_async_engine, initialize_schema
from packages.shared.models.langgraph_state_models import MinimalGameState


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for our test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

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

@pytest_asyncio.fixture
async def session(engine):
    """
    Provides a clean database session for each test.
    Rolls back any changes after the test completes.
    """
    async with AsyncSession(engine) as db_session:
        yield db_session
        await db_session.rollback()  # Ensures test isolation


@pytest.fixture
def minimal_game_state() -> MinimalGameState:
    """Provides a basic MinimalGameState for testing."""
    return MinimalGameState(
        campaign_id=1,
        character_id=None,
        discord_user_id="test_user",
        discord_channel_id="test_channel",
        correlation_id="test_correlation",
        player_action="",
        parsed_intent=None,
        action_result=None,
        dice_results=None,
        exit_early=False,
        error=None,
    )


@pytest_asyncio.fixture
async def mock_game_state_service(session) -> MagicMock:
    """Provides a mock GameStateService."""
    game_service = GameStateService(session=session)
    return game_service

@pytest_asyncio.fixture
async def mock_populated_state(mock_game_state_service, minimal_game_state):
    game_service = mock_game_state_service
    player_char = create_test_character(character_id=1, name="Tester")
    await game_service.create_character(character=player_char)
    await game_service.add_combat_participant(state=minimal_game_state,character=player_char)
    # enemy_char = create_test_character(character_id=2, name="goblin_1", is_hostile=True)
    # final_state = await game_service.create_character(enemy_char)
    # return final_state