from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from packages.shared.errors import ErrorCode
from packages.shared.exceptions import CustomException
from tests.utils.factories import InteractionFactory


@pytest.mark.asyncio
async def test_character_add_command_validation_error(mock_character_cog):
    """Test character add command when backend returns validation error."""
    interaction = InteractionFactory.regular_interaction()

    cog = mock_character_cog

    from packages.shared.exceptions import ValidationError as ApiValidationError

    cog.api_client.set_exception_override(
        "add_character", ApiValidationError(ErrorCode.VALIDATION_ERROR)
    )

    await cog.add.callback(cog, interaction, name="Hero", character_url=None)
    interaction.response.send_message.assert_awaited_once_with(
        ErrorCode.VALIDATION_ERROR.player_message, ephemeral=True
    )


@pytest.mark.asyncio
async def test_character_update_command_validation_error(mock_character_cog):
    """Test character update command when backend returns validation error."""
    interaction = InteractionFactory.regular_interaction()

    cog = mock_character_cog

    from packages.shared.exceptions import ValidationError as ApiValidationError

    cog.api_client.set_exception_override(
        "update_character", ApiValidationError(ErrorCode.UNKNOWN)
    )

    await cog.update.callback(
        cog, interaction, character_id=1, name="NewName", character_url=None
    )
    interaction.response.send_message.assert_awaited_once_with(
        ErrorCode.UNKNOWN.player_message,
        ephemeral=True,
    )


@pytest.mark.asyncio
async def test_character_remove_command_not_found_error(mock_character_cog):
    """Test character remove command when character is not found."""
    interaction = InteractionFactory.regular_interaction()

    mock_character_cog
    from packages.shared.exceptions import NotFoundError as ApiNotFoundError

    mock_character_cog.api_client.set_exception_override(
        "remove_character", ApiNotFoundError(ErrorCode.CHARACTER_NOT_FOUND)
    )

    await mock_character_cog.remove.callback(
        mock_character_cog, interaction, character_id=999
    )
    interaction.response.send_message.assert_awaited_once_with(
        ErrorCode.CHARACTER_NOT_FOUND.player_message, ephemeral=True
    )


@pytest.mark.asyncio
async def test_character_list_command_validation_error(mock_character_cog):
    """Test character list command when backend returns validation error."""
    interaction = InteractionFactory.admin_interaction()

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json = AsyncMock(
        return_value={"message": ErrorCode.VALIDATION_ERROR.player_message}
    )
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=mock_response
    )
    mock_character_cog.api_client.return_value.__aenter__.return_value.post.return_value = mock_response

    await mock_character_cog.list.callback(mock_character_cog, interaction)
    interaction.response.send_message.assert_awaited_once_with(
        ErrorCode.VALIDATION_ERROR.player_message, ephemeral=True
    )


@pytest.mark.asyncio
async def test_character_add_command_http_error(mock_character_cog):
    """Test character add command when HTTP request fails."""
    interaction = InteractionFactory.regular_interaction()

    mock_character_cog
    mock_character_cog.api_client.set_exception_override(
        "add_character", Exception("Network error")
    )

    await mock_character_cog.add.callback(
        mock_character_cog, interaction, name="Hero", character_url=None
    )
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.UNKNOWN.player_message.lower() == args[0].lower()
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_update_command_http_error(mock_character_cog):
    """Test character update command when HTTP request fails."""
    interaction = InteractionFactory.admin_interaction()

    mock_character_cog.api_client.set_exception_override(
        "set_server_config", CustomException()
    )

    await mock_character_cog.update.callback(
        mock_character_cog,
        interaction,
        character_id=1,
        name="NewName",
        character_url=None,
    )
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.UNKNOWN.player_message.lower() == args[0].lower()
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_remove_command_http_error(mock_character_cog):
    """Test character remove command when HTTP request fails."""
    interaction = InteractionFactory.admin_interaction()

    await mock_character_cog.remove.callback(
        mock_character_cog, interaction, character_id=1
    )
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.UNKNOWN.player_message.lower() == args[0].lower()
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_list_command_http_error(mock_character_cog):
    """Test character list command when HTTP request fails."""
    interaction = InteractionFactory.admin_interaction()

    await mock_character_cog.list.callback(mock_character_cog, interaction)
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.UNKNOWN.player_message.lower() == args[0].lower()
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_add_command_internal_server_error(mock_character_cog):
    """Test character add command when backend returns a 500 error."""
    interaction = InteractionFactory.admin_interaction()

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json = AsyncMock(
        return_value={"error": {"message": ErrorCode.UNKNOWN.player_message}}
    )
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error", request=MagicMock(), response=mock_response
    )
    mock_character_cog.api_client.return_value.__aenter__.return_value.post.return_value = mock_response

    await mock_character_cog.add.callback(
        mock_character_cog, interaction, name="Hero", character_url=None
    )
    interaction.response.send_message.assert_awaited_once_with(
        ErrorCode.UNKNOWN.player_message,
        ephemeral=True,
    )
