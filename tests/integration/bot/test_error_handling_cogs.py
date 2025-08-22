from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.shared.error_handler import discord_error_handler
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import AIAPIError, NotFoundError, ValidationError


@pytest.mark.asyncio
async def test_discord_validation_error_handler():
    """Test that ValidationError is properly handled and sends player message."""

    async def command_that_raises_validation_error(self, interaction):
        raise ValidationError(ErrorCode.VALIDATION_ERROR)

    test_command = discord_error_handler()(command_that_raises_validation_error)

    # Mock interaction object
    mock_interaction = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.followup.send = AsyncMock()

    # Call the decorated command
    mock_cog = MagicMock()
    await test_command(mock_cog, mock_interaction)

    # Verify the correct message was sent
    mock_interaction.response.send_message.assert_called_once_with(
        "A validation error occurred.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_discord_not_found_error_handler():
    """Test that NotFoundError is properly handled and sends player message."""

    async def command_that_raises_not_found_error(self, interaction):
        raise NotFoundError(ErrorCode.NOT_FOUND)

    test_command = discord_error_handler()(command_that_raises_not_found_error)

    # Mock interaction object
    mock_interaction = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.followup.send = AsyncMock()

    # Call the decorated command
    mock_cog = MagicMock()
    await test_command(mock_cog, mock_interaction)

    # Verify the correct message was sent
    mock_interaction.response.send_message.assert_called_once_with(
        "Resource not found.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_discord_ai_api_error_handler():
    """Test that AIAPIError is properly handled and sends player message."""

    async def command_that_raises_ai_api_error(self, interaction):
        raise AIAPIError(ErrorCode.AI_API_ERROR)

    test_command = discord_error_handler()(command_that_raises_ai_api_error)

    # Mock interaction object
    mock_interaction = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.followup.send = AsyncMock()

    # Call the decorated command
    mock_cog = MagicMock()
    await test_command(mock_cog, mock_interaction)

    # Verify the correct message was sent
    mock_interaction.response.send_message.assert_called_once_with(
        "A request to the AI service failed.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_discord_generic_error_handler():
    """Test that generic Exception is properly handled and sends fallback message."""

    async def command_that_raises_generic_error(self, interaction):
        raise Exception("Test generic error")

    test_command = discord_error_handler()(command_that_raises_generic_error)

    # Mock interaction object
    mock_interaction = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.followup.send = AsyncMock()

    # Call the decorated command
    mock_cog = MagicMock()
    await test_command(mock_cog, mock_interaction)

    # Verify the fallback message was sent
    mock_interaction.response.send_message.assert_called_once_with(
        "An unexpected error occurred. Please contact an administrator.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_discord_error_handler_custom_fallback_message():
    """Test that custom fallback message is used for generic exceptions."""

    custom_fallback = "Custom error message for this command"

    async def command_with_custom_fallback(self, interaction):
        raise Exception("Test generic error")

    test_command = discord_error_handler(fallback_message=custom_fallback)(
        command_with_custom_fallback
    )

    # Mock interaction object
    mock_interaction = AsyncMock()
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.followup.send = AsyncMock()

    # Call the decorated command
    mock_cog = MagicMock()
    await test_command(mock_cog, mock_interaction)

    # Verify the custom fallback message was sent
    mock_interaction.response.send_message.assert_called_once_with(
        custom_fallback, ephemeral=True
    )


@pytest.mark.asyncio
async def test_discord_error_handler_fallback_send():
    """Test that followup.send is used when response.send_message fails."""

    async def command_that_raises_validation_error(self, interaction):
        raise ValidationError(ErrorCode.VALIDATION_ERROR)

    test_command = discord_error_handler()(command_that_raises_validation_error)

    # Mock interaction object where response.send_message fails
    mock_interaction = AsyncMock()
    mock_interaction.response.send_message = AsyncMock(
        side_effect=Exception("Already responded")
    )
    mock_interaction.followup.send = AsyncMock()

    # Call the decorated command
    mock_cog = MagicMock()
    await test_command(mock_cog, mock_interaction)

    # Verify followup.send was called as fallback
    mock_interaction.followup.send.assert_called_once_with(
        "A validation error occurred.", ephemeral=True
    )
