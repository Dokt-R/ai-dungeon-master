import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.shared.error_handler import discord_error_handler
from packages.shared.exceptions import (
    AIAPIError,
    CustomException,
    NotFoundError,
    ValidationError,
)


def test_custom_exception_creation():
    """Test that CustomException can be created with all parameters."""
    # Test with all parameters
    exc = CustomException("Test message", "TEST_CODE", {"key": "value"})
    assert str(exc) == "Test message"
    assert exc.message == "Test message"
    assert exc.error_code == "TEST_CODE"
    assert exc.details == {"key": "value"}

    # Test with only message
    exc = CustomException("Test message")
    assert str(exc) == "Test message"
    assert exc.message == "Test message"
    assert exc.error_code is None  # Default value for CustomException
    assert exc.details is not None


def test_validation_error_creation():
    """Test that ValidationError can be created with all parameters."""
    # Test with all parameters
    exc = ValidationError(
        "Validation failed", "VALIDATION_ERROR", {"field": "required"}
    )
    assert str(exc) == "Validation failed"
    assert exc.message == "Validation failed"
    assert exc.error_code == "VALIDATION_ERROR"
    assert exc.details == {"field": "required"}

    # Test with only message
    exc = ValidationError("Validation failed")
    assert str(exc) == "Validation failed"
    assert exc.message == "Validation failed"
    assert exc.error_code == "VALIDATION_ERROR"
    assert exc.details is not None


def test_not_found_error_creation():
    """Test that NotFoundError can be created with all parameters."""
    # Test with all parameters
    exc = NotFoundError("Resource not found", "NOT_FOUND", {"resource": "campaign"})
    assert str(exc) == "Resource not found"
    assert exc.message == "Resource not found"
    assert exc.error_code == "NOT_FOUND"
    assert exc.details == {"resource": "campaign"}

    # Test with only message
    exc = NotFoundError("Resource not found")
    assert str(exc) == "Resource not found"
    assert exc.message == "Resource not found"
    assert exc.error_code == "NOT_FOUND"  # Default value
    assert exc.details is not None


def test_ai_api_error_creation():
    """Test that AIAPIError can be created with all parameters."""
    # Test with all parameters
    exc = AIAPIError("AI API call failed", "AI_API_ERROR", {"status": 500})
    assert str(exc) == "AI API call failed"
    assert exc.message == "AI API call failed"
    assert exc.error_code == "AI_API_ERROR"
    assert exc.details == {"status": 500}

    # Test with only message
    exc = AIAPIError("AI API call failed")
    assert str(exc) == "AI API call failed"
    assert exc.message == "AI API call failed"
    assert exc.error_code == "AI_API_ERROR"  # Default value
    assert exc.details is not None


@pytest.mark.asyncio
async def test_discord_error_handler_decorator(caplog):
    """Test the discord_error_handler decorator with new exception classes."""
    mock_interaction = MagicMock()
    mock_interaction.response.send_message = AsyncMock()

    @discord_error_handler()
    async def command_that_raises_validation_error(self, interaction):
        raise ValidationError(
            "Validation failed", "VALIDATION_ERROR", {"field": "required"}
        )

    @discord_error_handler()
    async def command_that_raises_not_found_error(self, interaction):
        raise NotFoundError("Not found", "NOT_FOUND", {"resource": "campaign"})

    @discord_error_handler()
    async def command_that_raises_ai_api_error(self, interaction):
        raise AIAPIError("AI API call failed", "AI_API_ERROR", {"status": 500})

    @discord_error_handler()
    async def command_that_raises_generic_error(self, interaction):
        raise Exception("Generic error")

    # Test ValidationError
    with caplog.at_level(logging.WARNING):
        await command_that_raises_validation_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            "Validation failed", ephemeral=True
        )
        # Verify warning log with stack trace
        assert "Validation failed" in caplog.text
        assert "Traceback" in caplog.text
        assert "ValidationError" in caplog.text

    # Reset mock for next test
    mock_interaction.response.send_message.reset_mock()

    # Test NotFoundError
    with caplog.at_level(logging.WARNING):
        await command_that_raises_not_found_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            "Not found", ephemeral=True
        )
        # Verify warning log with stack trace
        assert "Not found" in caplog.text
        assert "Traceback" in caplog.text
        assert "NotFoundError" in caplog.text

    # Reset mock for next test
    mock_interaction.response.send_message.reset_mock()

    # Test AIAPIError
    with caplog.at_level(logging.WARNING):
        await command_that_raises_ai_api_error(None, mock_interaction)
        mock_interaction.response.send_message.assert_awaited_with(
            "AI API call failed", ephemeral=True
        )
        # Verify warning log with stack trace
        assert "AI API call failed" in caplog.text
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
