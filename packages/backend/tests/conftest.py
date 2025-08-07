import pytest
from collections import namedtuple
from sqlmodel import Session, SQLModel

from packages.backend.components.campaign_manager import CampaignManager
from packages.backend.components.character_manager import CharacterManager
from packages.backend.components.player_manager import PlayerManager
from packages.backend.components.server_settings_manager import ServerSettingsManager
from packages.shared.db import get_engine
from packages.backend.db.init_db import initialize_schema
from packages.shared.models import Player, Character

# Shared in-memory SQLite DB URI
SHARED_MEM_URI = "file:memdb1?mode=memory&cache=shared"

Managers = namedtuple("Managers", ["settings", "character", "player", "campaign"])


@pytest.fixture(scope="session")
def engine():
    """
    Creates a single, session-scoped SQLAlchemy Engine and initializes the schema.
    """
    db_engine = get_engine(SHARED_MEM_URI)
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
def managers(engine):
    """
    Initializes all manager instances with the session-scoped engine.
    """
    ssm = ServerSettingsManager(engine=engine)
    cm = CharacterManager(engine=engine)
    pm = PlayerManager(engine=engine)
    cmpm = CampaignManager(engine=engine)
    return Managers(ssm, cm, pm, cmpm)


@pytest.fixture
def insert_player(session):
    """
    Fixture to insert a predefined player for use in tests.
    """

    def _insert(user_id: str = "user-id-1", username: str = "Alice"):
        player = Player(user_id=user_id, username=username)
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
    Fixture to fetch a player row by user_id.
    """

    def _select_player(user_id: str = "user-id-1"):
        return session.get(Player, user_id)

    return _select_player
