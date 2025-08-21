from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog

from packages.bot.main import correlation_id_context


@pytest.mark.asyncio
async def test_correlation_id_context():
    with correlation_id_context():
        # Context should be bound within the block
        assert structlog.contextvars.get_contextvars().get("correlation_id") is not None

    # Context should be cleared after the block
    assert structlog.contextvars.get_contextvars() == {}

@pytest.mark.asyncio
async def test_correlation_id_in_logs():
    with correlation_id_context():
        with structlog.testing.capture_logs() as cap_logs:
            structlog.get_logger().info("Test log")
            
        assert any(
            "correlation_id" in log
            for log in cap_logs
        )

@pytest.mark.asyncio
async def test_on_ready_logs_correlation_id():
    mock_bot = MagicMock()
    mock_bot.user = "TestBot"
    mock_bot.tree.sync = AsyncMock(return_value=[1,2,3])
    
    # Patch the on_ready function to capture logs
    with patch('packages.bot.main.logger') as mock_logger:
        from packages.bot.main import on_ready
        await on_ready()
        
        # Verify correlation ID was logged
        mock_logger.info.assert_any_call("Bot logged in", bot_user="TestBot")
        assert "correlation_id" in mock_logger.info.call_args[1]