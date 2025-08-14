import os

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.shared.models import *  # noqa: F403

DEFAULT_DB_PATH = os.environ.get("DB_PATH", "server_settings.db")


def get_db_path():
    return DEFAULT_DB_PATH


def get_async_engine(db_path=None):
    """
    Creates and returns a SQLAlchemy AsyncEngine.
    For in-memory SQLite, uses a specific URI to ensure it's shared across threads.
    """
    path = db_path or get_db_path()
    if "mode=memory" in path:
        # For async, we use a specific connect_args setup for shared in-memory DB
        return create_async_engine(
            f"sqlite+aiosqlite:///{path}",
            connect_args={"check_same_thread": False, "uri": True},
        )
    return create_async_engine(f"sqlite+aiosqlite:///{path}")


async def initialize_schema(engine):
    """
    Initializes the database schema using SQLModel and a SQLAlchemy AsyncEngine.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_async_session():
    async with AsyncSession(get_async_engine()) as session:
        yield session
