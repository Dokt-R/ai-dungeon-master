from unittest.mock import AsyncMock, MagicMock

import pytest
from structlog.testing import capture_logs

from packages.shared.error_handler import _safe_send_message, discord_error_handler
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import (
    AIAPIError,
    CustomException,
    NotFoundError,
    ValidationError,
)


def test_custom_exception_creation():
    """Test that CustomException can be created with all parameters."""
    # Test with all parameters
    error = ErrorCode.UNKNOWN
    exc = CustomException(error, details={"key": "value"})
    assert exc.message == error.message
    assert exc.error_code == "UNKNOWN"
    assert exc.details is not None


def test_validation_error_creation():
    """Test that ValidationError can be created with all parameters."""
    # Test with all parameters
    error = ErrorCode.VALIDATION_ERROR
    exc = ValidationError(error, details={"field": "required"})
    assert exc.message == error.message
    assert exc.error_code == "VALIDATION_ERROR"
    assert exc.details == {"field": "required"}


def test_not_found_error_creation():
    """Test that NotFoundError can be created with all parameters."""
    # Test with all parameters
    error = ErrorCode.NOT_FOUND
    exc = NotFoundError(error, details={"resource": "campaign"})
    assert exc.message == error.message
    assert exc.error_code == "NOT_FOUND"
    assert exc.details == {"resource": "campaign"}


def test_ai_api_error_creation():
    """Test that AIAPIError can be created with all parameters."""
    # Test with all parameters
    error = ErrorCode.AI_API_ERROR
    exc = AIAPIError(error, details={"status": 500})
    assert exc.message == error.message
    assert exc.error_code == "AI_API_ERROR"
    assert exc.details == {"status": 500}


@pytest.mark.asyncio
async def test_discord_error_handler_decorator():
    """Test the discord_error_handler decorator with new exception classes."""
    mock_interaction = MagicMock()
    mock_interaction.response.send_message = AsyncMock()

    @discord_error_handler()
    async def command_that_raises_validation_error(self, interaction):
        raise ValidationError(ErrorCode.VALIDATION_ERROR, details={"field": "required"})

    @discord_error_handler()
    async def command_that_raises_not_found_error(self, interaction):
        raise NotFoundError(ErrorCode.NOT_FOUND, details={"resource": "campaign"})

    @discord_error_handler()
    async def command_that_raises_ai_api_error(self, interaction):
        raise AIAPIError(ErrorCode.AI_API_ERROR, details={"status": 500})

    @discord_error_handler()
    async def command_that_raises_generic_error(self, interaction):
        raise Exception("Generic error")

    # Test ValidationError
    with capture_logs() as cap_logs:
        await command_that_raises_validation_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            ErrorCode.VALIDATION_ERROR.message, ephemeral=True
        )
        # Verify warning log with stack trace
        print(cap_logs)
        assert any(
            log["event"] == "Custom exception occurred"
            and log["exception_type"] == "ValidationError"
            for log in cap_logs
        )
        assert any(log.get("exc_info") is True for log in cap_logs)

    # Reset mock for next test
    mock_interaction.response.send_message.reset_mock()

    # Test NotFoundError
    with capture_logs() as cap_logs:
        await command_that_raises_not_found_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            ErrorCode.NOT_FOUND.message, ephemeral=True
        )
        # Verify warning log with stack trace
        assert any(
            log["event"] == "Custom exception occurred"
            and log["exception_type"] == "NotFoundError"
            for log in cap_logs
        )
        assert any(log.get("exc_info") is True for log in cap_logs)

    # Reset mock for next test
    mock_interaction.response.send_message.reset_mock()

    # Test AIAPIError
    with capture_logs() as cap_logs:
        await command_that_raises_ai_api_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            ErrorCode.AI_API_ERROR.message, ephemeral=True
        )
        # Verify warning log with stack trace
        assert any(
            log["event"] == "Custom exception occurred"
            and log["exception_type"] == "AIAPIError"
            for log in cap_logs
        )
        assert any(log.get("exc_info") is True for log in cap_logs)

    # Reset mock for next test
    mock_interaction.response.send_message.reset_mock()

    # Test generic Exception
    with capture_logs() as cap_logs:
        await command_that_raises_generic_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            "An unexpected error occurred. Please contact an administrator.",
            ephemeral=True,
        )
        # Verify error log
        # The actual log message format may vary, so check for the key components
        error_logs = [log for log in cap_logs if log.get("log_level") == "error"]
        assert len(error_logs) > 0, (
            f"Expected error log not found. Captured logs: {cap_logs}"
        )
        error_log = error_logs[0]
        assert "command_that_raises_generic_error" in str(error_log.get("command", ""))
        assert "Generic error" in str(error_log.get("error", ""))
        assert error_log.get("exc_info") is True


@pytest.mark.asyncio
async def test_safe_send_message_normal_case():
    """Test _safe_send_message with normal case where response.send_message succeeds."""
    mock_interaction = MagicMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.followup.send = AsyncMock()

    await _safe_send_message(mock_interaction, "Test message", ephemeral=True)

    # Verify that send_message was called
    mock_interaction.response.send_message.assert_awaited_with(
        "Test message", ephemeral=True
    )
    # Verify that followup.send was not called
    mock_interaction.followup.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_safe_send_message_fallback_to_followup():
    """Test _safe_send_message falls back to followup.send when response.send_message fails."""
    mock_interaction = MagicMock()
    mock_interaction.response.send_message = AsyncMock(
        side_effect=Exception("Response failed")
    )
    mock_interaction.followup.send = AsyncMock()

    with capture_logs() as cap_logs:
        await _safe_send_message(mock_interaction, "Test message", ephemeral=True)

        # Verify that both methods were called
        mock_interaction.response.send_message.assert_awaited_with(
            "Test message", ephemeral=True
        )
        mock_interaction.followup.send.assert_awaited_with(
            "Test message", ephemeral=True
        )

        # Verify warning log for the first failure
        assert any(
            "Failed to send message via interaction.response.send_message: Response failed"
            in log["event"]
            for log in cap_logs
        )


@pytest.mark.asyncio
async def test_safe_send_message_both_fail_logs_and_raises_runtimeerror():
    """
    Test _safe_send_message logs warnings for each failure and a final error,
    and raises RuntimeError when both response.send_message and followup.send fail.
    """
    mock_interaction = MagicMock()
    mock_interaction.response.send_message = AsyncMock(
        side_effect=Exception("Response failed")
    )
    mock_interaction.followup = MagicMock()
    mock_interaction.followup.send = AsyncMock(side_effect=Exception("Followup failed"))

    with capture_logs() as cap_logs:
        with pytest.raises(
            RuntimeError, match="Failed to send error message to Discord interaction"
        ):
            await _safe_send_message(mock_interaction, "Test message", ephemeral=True)

        # Verify warning logs for each attempt
        assert any(
            "Failed to send message via interaction.response.send_message: Response failed"
            in log["event"]
            for log in cap_logs
        )
        assert any(
            "Failed to send message via interaction.followup.send: Followup failed"
            in log["event"]
            for log in cap_logs
        )

        # Verify the final error log
        assert any(
            "Failed to send message via both response.send_message and followup.send"
            in log["event"]
            for log in cap_logs
        )
