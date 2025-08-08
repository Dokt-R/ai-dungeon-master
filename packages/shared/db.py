import os
from sqlmodel import SQLModel, Session, create_engine
from packages.shared.models import *  # Import all models


DEFAULT_DB_PATH = os.environ.get("DB_PATH", "server_settings.db")


def get_db_path():
    return DEFAULT_DB_PATH


def get_engine(db_path=None):
    """
    Creates and returns a SQLAlchemy Engine.
    For in-memory SQLite, uses a specific URI to ensure it's shared across threads.
    """
    path = db_path or get_db_path()
    if "mode=memory" in path:
        # Use a specific connect_args setup for shared in-memory DB
        return create_engine(
            f"sqlite:///{path}", connect_args={"check_same_thread": False}
        )
    return create_engine(f"sqlite:///{path}")


def initialize_schema(engine):
    """
    Initializes the database schema using SQLModel and a SQLAlchemy Engine.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(get_engine()) as session:
        yield session
