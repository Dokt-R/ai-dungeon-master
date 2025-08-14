import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from packages.shared.db import get_async_engine


@pytest.mark.asyncio
async def test_get_async_engine():
    # Arrange
    db_uri = "sqlite+aiosqlite:///:memory:"

    # Act
    engine = get_async_engine(db_uri)

    # Assert
    assert isinstance(engine, AsyncEngine)
