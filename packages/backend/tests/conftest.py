import pytest
import uuid
from collections import namedtuple
from sqlmodel import Session, SQLModel
from fastapi.testclient import TestClient
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
