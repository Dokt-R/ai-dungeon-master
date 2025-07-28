import pytest

# Removed unused import
from unittest.mock import AsyncMock, patch, PropertyMock

# Assuming the bot is defined in bot.py
from bot.bot import bot


@pytest.fixture
def mock_message():
    """Create a mock message object for testing."""
    message = AsyncMock()
    message.content = "/ping"
    message.author.id = 123
    return message


@pytest.mark.asyncio
async def test_bot_startup():
    """Test that the bot starts up without errors."""
    assert bot is not None  # Ensure the bot instance is created


@pytest.mark.asyncio
async def test_ping_command(mock_message):
    """Test ping command"""
    # Patch the bot.user property to a mock with a different ID
    with patch.object(type(bot), "user", new_callable=PropertyMock) as mock_user:
        mock_user.return_value.id = 999

        # Get the context
        ctx = await bot.get_context(mock_message)

        # Patch ctx.send with a mock so we can inspect it
        ctx.send = AsyncMock()

        # Invoke the command
        await bot.invoke(ctx)

        # Assert the "pong" response was sent
        ctx.send.assert_called_once_with("pong")
