import pytest

from packages.shared.errors import ErrorCode
from packages.shared.exceptions import NotFoundError, ValidationError
from tests.utils.mock_api_client import MockApiClient


@pytest.mark.asyncio
async def test_character_add_command(mock_interaction, mock_character_cog):
    cog = mock_character_cog
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_response_override("add_character", {"character_id": 123})

    interaction = mock_interaction
    interaction.user.id = "12345"

    await cog.add.callback(cog, interaction, name="Hero", character_url=None)
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "added successfully" in args[0].lower()
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_update_command(mock_interaction, mock_character_cog):
    cog = mock_character_cog
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_response_override("update_character", {"character_id": 1})

    interaction = mock_interaction
    interaction.user.id = "12345"

    await cog.update.callback(
        cog, interaction, character_id=1, name="NewName", character_url=None
    )
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "updated successfully" in args[0].lower()
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_remove_command(mock_interaction, mock_character_cog):
    cog = mock_character_cog
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_response_override(
        "remove_character", {"message": "Character removed successfully"}
    )

    interaction = mock_interaction
    interaction.user.id = "12345"

    await cog.remove.callback(cog, interaction, character_id=1)
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "removed successfully" in args[0].lower()
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_list_command(mock_interaction, mock_character_cog):
    cog = mock_character_cog
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_response_override(
        "list_characters",
        {"characters": [{"character_id": 1, "name": "Hero", "character_url": "url"}]},
    )

    interaction = mock_interaction
    interaction.user.id = "12345"

    await cog.list.callback(cog, interaction)
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "your characters" in args[0].lower()
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_add_command_backend_error(
    mock_interaction, mock_character_cog
):
    cog = mock_character_cog
    # Replace API client with mock
    cog.api_client = MockApiClient()
    error = ErrorCode.DUPLICATE_CHARACTER
    cog.api_client.set_exception_override(
        "add_character", ValidationError(error, details={"name": "Hero"})
    )

    interaction = mock_interaction
    interaction.user.id = "12345"

    await cog.add.callback(cog, interaction, name="Hero", character_url=None)
    interaction.response.send_message.assert_awaited_once_with(
        error.player_message.format(name="Hero"), ephemeral=True
    )


@pytest.mark.asyncio
async def test_character_update_command_no_fields(mock_interaction, mock_character_cog):
    cog = mock_character_cog
    # Replace API client with mock
    cog.api_client = MockApiClient()

    interaction = mock_interaction
    interaction.user.id = "12345"

    await cog.update.callback(
        cog, interaction, character_id=1, name=None, character_url=None
    )
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert ErrorCode.CHARACTER_EMPTY_FIELDS.player_message in args[0]
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_remove_command_backend_error(
    mock_interaction, mock_character_cog
):
    cog = mock_character_cog
    # Replace API client with mock
    cog.api_client = MockApiClient()

    error = ErrorCode.CHARACTER_NOT_FOUND
    cog.api_client.set_exception_override(
        "remove_character",
        NotFoundError(error, details={"message": "Character not found"}),
    )

    interaction = mock_interaction
    interaction.user.id = "12345"

    await cog.remove.callback(cog, interaction, character_id=999)
    interaction.response.send_message.assert_awaited_once_with(
        error.player_message, ephemeral=True
    )


@pytest.mark.asyncio
async def test_character_list_command_empty(mock_interaction, mock_character_cog):
    cog = mock_character_cog
    # Replace API client with mock
    cog.api_client = MockApiClient()
    cog.api_client.set_response_override("list_characters", {"characters": []})

    interaction = mock_interaction
    interaction.user.id = "12345"

    await cog.list.callback(cog, interaction)
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "no characters" in args[0].lower()
    assert kwargs.get("ephemeral") is True
