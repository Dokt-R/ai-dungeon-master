import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.shared.error_handler import discord_error_handler
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
    assert str(exc) == error.message
    assert exc.message == error.message
    assert exc.error_code == "UNKNOWN"
    assert exc.details is not None


def test_validation_error_creation():
    """Test that ValidationError can be created with all parameters."""
    # Test with all parameters
    error = ErrorCode.VALIDATION_ERROR
    exc = ValidationError(error, details={"field": "required"})
    assert str(exc) == error.message
    assert exc.message == error.message
    assert exc.error_code == "VALIDATION_ERROR"
    assert exc.details == {"field": "required"}


def test_not_found_error_creation():
    """Test that NotFoundError can be created with all parameters."""
    # Test with all parameters
    error = ErrorCode.NOT_FOUND
    exc = NotFoundError(error, details={"resource": "campaign"})
    assert str(exc) == error.message
    assert exc.message == error.message
    assert exc.error_code == "NOT_FOUND"
    assert exc.details == {"resource": "campaign"}


def test_ai_api_error_creation():
    """Test that AIAPIError can be created with all parameters."""
    # Test with all parameters
    error = ErrorCode.AI_API_ERROR
    exc = AIAPIError(error, details={"status": 500})
    assert str(exc) == error.message
    assert exc.message == error.message
    assert exc.error_code == "AI_API_ERROR"
    assert exc.details == {"status": 500}


@pytest.mark.asyncio
async def test_discord_error_handler_decorator(caplog):
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
    with caplog.at_level(logging.WARNING):
        await command_that_raises_validation_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            ErrorCode.VALIDATION_ERROR.message, ephemeral=True
        )
        # Verify warning log with stack trace
        assert ErrorCode.VALIDATION_ERROR.message in caplog.text
        assert "Traceback" in caplog.text
        assert "ValidationError" in caplog.text

    # Reset mock for next test
    mock_interaction.response.send_message.reset_mock()

    # Test NotFoundError
    with caplog.at_level(logging.WARNING):
        await command_that_raises_not_found_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            ErrorCode.NOT_FOUND.message, ephemeral=True
        )
        # Verify warning log with stack trace
        assert ErrorCode.NOT_FOUND.message in caplog.text
        assert "Traceback" in caplog.text
        assert "NotFoundError" in caplog.text

    # Reset mock for next test
    mock_interaction.response.send_message.reset_mock()

    # Test AIAPIError
    with caplog.at_level(logging.WARNING):
        await command_that_raises_ai_api_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            ErrorCode.AI_API_ERROR.message, ephemeral=True
        )
        # Verify warning log with stack trace
        assert ErrorCode.AI_API_ERROR.message in caplog.text
        assert "Traceback" in caplog.text
        assert "AIAPIError" in caplog.text

    # Reset mock for next test
    mock_interaction.response.send_message.reset_mock()

    # Test generic Exception
    with caplog.at_level(logging.ERROR):
        await command_that_raises_generic_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            "An unexpected error occurred. Please contact an administrator.",
            ephemeral=True,
        )
        # Verify error log with stack trace
        assert "Generic error" in caplog.text
        assert "Traceback" in caplog.text
