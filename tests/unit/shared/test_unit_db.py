import pytest
from sqlalchemy.engine import Engine
from packages.shared.db import get_engine


def test_get_engine():
    # Arrange
    db_uri = "sqlite:///:memory:"

    # Act
    engine = get_engine(db_uri)

    # Assert
    assert isinstance(engine, Engine)
