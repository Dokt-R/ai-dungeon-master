import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import HTTPException
from packages.shared.error_handler import (
    handle_error,
    NotFoundError,
    ValidationError,
    fastapi_error_handler,
    discord_error_handler,
)


def test_handle_error_fastapi_context():
    with pytest.raises(HTTPException) as exc_info:
        handle_error(ValidationError("Validation error"), context="fastapi")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Validation error"

    with pytest.raises(HTTPException) as exc_info:
        handle_error(NotFoundError("Not found"), context="fastapi")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Not found"

    with pytest.raises(HTTPException) as exc_info:
        handle_error(Exception("Generic error"), context="fastapi")
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Generic error"


def test_handle_error_discord_context(caplog):
    # In discord context, it should only log and not raise
    handle_error(ValidationError("Validation error"), context="discord")
    assert "Validation error" in caplog.text

    handle_error(NotFoundError("Not found"), context="discord")
    assert "Not found" in caplog.text

    handle_error(Exception("Generic error"), context="discord")
    assert "Generic error" in caplog.text


def test_fastapi_error_handler_decorator():
    @fastapi_error_handler
    def function_that_raises(error):
        raise error

    with pytest.raises(HTTPException) as exc_info:
        function_that_raises(ValidationError("Test"))
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        function_that_raises(NotFoundError("Test"))
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        function_that_raises(Exception("Test"))
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_discord_error_handler_decorator():
    mock_interaction = MagicMock()
    mock_interaction.response.send_message = AsyncMock()

    @discord_error_handler()
    async def command_that_raises(interaction, error):
        raise error

    # Test ValidationError
    await command_that_raises(mock_interaction, ValidationError("Validation failed"))
    mock_interaction.response.send_message.assert_awaited_with(
        "Validation failed", ephemeral=True
    )

    # Test NotFoundError
    await command_that_raises(mock_interaction, NotFoundError("Not found"))
    mock_interaction.response.send_message.assert_awaited_with(
        "Not found", ephemeral=True
    )

    # Test generic Exception
    await command_that_raises(mock_interaction, Exception("Generic error"))
    mock_interaction.response.send_message.assert_awaited_with(
        "An unexpected error occurred. Please contact an administrator.",
        ephemeral=True,
    )