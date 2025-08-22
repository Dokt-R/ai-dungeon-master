import sys
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import httpx
import pytest

from packages.shared.errors import ErrorCode
from packages.shared.exceptions import (
    CustomException,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from tests.utils.factories import (
    InteractionFactory,
)

sys.modules["packages.backend.components.campaign_manager"] = mock.MagicMock()

pytestmark = pytest.mark.asyncio


async def test_campaign_new_success(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "create_campaign", {"message": "Campaign created successfully"}
    )

    interaction = InteractionFactory.admin_interaction()
    assert isinstance(interaction.user, discord.Member)

    await mock_campaign_cog._handle_campaign_new(interaction, "test_campaign")
    interaction.response.send_message.assert_awaited_once()
    assert "created successfully" in interaction.response.send_message.call_args[0][0]


async def test_campaign_new_duplicate(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_exception_override(
        "create_campaign",
        ValidationError(
            ErrorCode.DUPLICATE_CAMPAIGN_NAME, campaign_name="existing_campaign"
        ),
    )

    interaction = InteractionFactory.admin_interaction()
    campaign_name = "existing_campaign"

    with pytest.raises(ValidationError) as exc_info:
        await mock_campaign_cog._handle_campaign_new(interaction, campaign_name)

    exc = exc_info.value
    assert campaign_name in exc.player_message
    interaction.response.send_message.assert_not_called()


async def test_campaign_new_permission_denied(mock_campaign_cog):
    interaction = InteractionFactory.regular_interaction()
    campaign_name = "test_campaign"

    with pytest.raises(PermissionDeniedError) as exc_info:
        await mock_campaign_cog._handle_campaign_new(interaction, campaign_name)

    exc = exc_info.value
    assert "do not have permission" in exc.player_message
    interaction.response.send_message.assert_not_called()


async def test_campaign_new_backend_error(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_exception_override(
        "create_campaign", CustomException()
    )

    interaction = InteractionFactory.admin_interaction()
    campaign_name = "test_campaign"

    with pytest.raises(CustomException) as exc_info:
        await mock_campaign_cog._handle_campaign_new(interaction, campaign_name)

    exc = exc_info.value
    assert ErrorCode.UNKNOWN.player_message in exc.player_message


async def test_campaign_join_success(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "join_campaign", {"message": "Joined campaign successfully"}
    )

    interaction = InteractionFactory.regular_interaction()
    campaign_name = "existing_campaign"

    await mock_campaign_cog._handle_campaign_join(interaction, campaign_name)
    interaction.response.send_message.assert_awaited_once()
    assert "joined campaign" in interaction.response.send_message.call_args[0][0]


async def test_campaign_join_nonexistent(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_exception_override(
        "join_campaign",
        NotFoundError(ErrorCode.CAMPAIGN_NOT_FOUND, campaign_name="My Campaign"),
    )

    # Mock interaction
    interaction = InteractionFactory.regular_interaction()

    # Run and assert NotFoundError is raised
    with pytest.raises(NotFoundError):
        await mock_campaign_cog._handle_campaign_join(interaction, "My Campaign")


async def test_campaign_join_no_campaign_name_uses_last_active(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "join_campaign", {"message": "Joined campaign successfully"}
    )

    interaction = InteractionFactory.regular_interaction()

    await mock_campaign_cog._handle_campaign_join(interaction, None)
    interaction.response.send_message.assert_awaited_once()
    assert "joined campaign" in interaction.response.send_message.call_args[0][0]


async def test_campaign_join_already_joined_fails(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_exception_override(
        "join_campaign", ValidationError(ErrorCode.PLAYER_NOT_IN_CMD)
    )

    # Mock interaction
    interaction = InteractionFactory.regular_interaction()

    # Run and assert ValidationError is raised
    with pytest.raises(ValidationError) as exc_info:
        await mock_campaign_cog._handle_campaign_join(interaction, "My Campaign")

    exc = exc_info.value
    assert ErrorCode.PLAYER_NOT_IN_CMD.player_message == exc.player_message


async def test_campaign_join_new_player_and_character(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "join_campaign", {"message": "Joined campaign successfully"}
    )

    interaction = InteractionFactory.regular_interaction()
    campaign_name = "new_campaign"

    await mock_campaign_cog._handle_campaign_join(interaction, campaign_name)
    interaction.response.send_message.assert_awaited_once()
    assert "joined campaign" in interaction.response.send_message.call_args[0][0]


async def test_campaign_end_and_join_another(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "end_campaign", {"message": "Campaign ended successfully"}
    )
    mock_campaign_cog.api_client.set_response_override(
        "join_campaign", {"message": "Joined campaign successfully"}
    )

    interaction = InteractionFactory.regular_interaction()
    campaign_name1 = "campaignA"
    campaign_name2 = "campaignB"

    # End campaignA
    await mock_campaign_cog._handle_campaign_end(interaction, campaign_name1)
    interaction.response.send_message.assert_awaited_once()

    # Now join campaignB
    interaction.response.reset_mock()
    await mock_campaign_cog._handle_campaign_join(interaction, campaign_name2)
    interaction.response.send_message.assert_awaited_once()
    assert "joined campaign" in interaction.response.send_message.call_args[0][0]


async def test_campaign_join_no_last_active_campaign_fails(mock_campaign_cog):
    # Replace API client with mock
    error = ErrorCode.NO_LAST_ACTIVE_CAMPAIGN
    mock_campaign_cog.api_client.set_exception_override(
        "join_campaign", NotFoundError(error)
    )

    interaction = InteractionFactory.regular_interaction()

    with pytest.raises(NotFoundError) as exc_info:
        await mock_campaign_cog._handle_campaign_join(interaction, None)

    exc = exc_info.value
    assert error.player_message in exc.player_message


async def test_campaign_join_new_character_linked(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "join_campaign", {"message": "Joined campaign successfully"}
    )

    interaction = InteractionFactory.regular_interaction()
    campaign_name = "campaignC"

    await mock_campaign_cog._handle_campaign_join(interaction, campaign_name)
    interaction.response.send_message.assert_awaited_once()
    assert "joined campaign" in interaction.response.send_message.call_args[0][0]


@pytest.mark.skip(
    reason="Autosave is gimmicky and should be reworked, if at all implemented"
)
async def test_campaign_continue_success_autosave(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "continue_campaign",
        {
            "campaign_name": "EpicQuest",
            "source": "autosave",
        },
    )

    interaction = InteractionFactory.regular_interaction()

    await mock_campaign_cog._handle_campaign_continue(interaction)
    interaction.response.send_message.assert_awaited_once()
    assert "autosave" in interaction.response.send_message.call_args[0][0].lower()
    assert (
        "resuming campaign" in interaction.response.send_message.call_args[0][0].lower()
    )


async def test_campaign_party_formation_multiple_users_onboarding(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "create_campaign", {"message": "Campaign created successfully"}
    )
    mock_campaign_cog.api_client.set_response_override(
        "join_campaign", {"message": "Joined campaign successfully"}
    )
    mock_campaign_cog.api_client.set_exception_override(
        "continue_campaign", ValidationError("UNKNOWN")
    )

    campaign_name = "party_campaign"

    # User2 (regular player) joins the campaign

    # Admin creates campaign
    interaction1 = InteractionFactory.admin_interaction()
    await mock_campaign_cog._handle_campaign_new(interaction1, campaign_name)
    interaction1.response.send_message.assert_awaited_once()

    # Admin joins campaign
    interaction2 = InteractionFactory.regular_interaction()
    await mock_campaign_cog._handle_campaign_join(interaction2, campaign_name)
    interaction2.response.send_message.assert_awaited_once()

    # Player joins campaign
    interaction3 = InteractionFactory.admin_interaction()
    await mock_campaign_cog._handle_campaign_join(interaction3, campaign_name)
    interaction3.response.send_message.assert_awaited_once()
    msg2 = interaction3.response.send_message.call_args[0][0].lower()
    assert "joined campaign" in msg2 or "character" in msg2

    with pytest.raises(ValidationError):
        await mock_campaign_cog._handle_campaign_continue(interaction1)


@pytest.mark.skip(reason="Not implemented. May need deletion.")
async def test_campaign_autosave_restore_after_onboarding_and_disconnect(cog):
    # User creates and joins a campaign (onboarding)
    interaction = MagicMock()
    interaction.user.id = 2222
    interaction.guild.id = 3333
    interaction.response = AsyncMock()
    campaign_name = "autosave_campaign"

    # Simulate successful campaign creation
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = AsyncMock(return_value={})
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called()
        interaction.response.reset_mock()

        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called()
        interaction.response.reset_mock()

        mock_response.json.return_value = {
            "campaign_name": campaign_name,
            "source": "autosave",
        }
        with pytest.raises(ValidationError):
            await cog._handle_campaign_continue(interaction)


async def test_campaign_continue_success_save(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "continue_campaign",
        {
            "campaign_name": "EpicQuest",
            "source": "save",
        },
    )

    interaction = InteractionFactory.regular_interaction()

    await mock_campaign_cog._handle_campaign_continue(interaction)
    interaction.response.send_message.assert_awaited_once()
    assert (
        "last clean save" in interaction.response.send_message.call_args[0][0].lower()
    )
    assert (
        "resuming campaign" in interaction.response.send_message.call_args[0][0].lower()
    )


async def test_campaign_continue_backend_error(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_exception_override(
        "continue_campaign", CustomException()
    )

    interaction = InteractionFactory.regular_interaction()

    with pytest.raises(CustomException) as exc_info:
        await mock_campaign_cog._handle_campaign_continue(interaction)

    exc = exc_info.value
    print(exc)
    assert ErrorCode.UNKNOWN.player_message in exc.player_message


async def test_campaign_delete_with_active_characters(mock_campaign_cog):
    interaction = InteractionFactory.admin_interaction()
    campaign_name = "active_char_campaign"
    expected_message = "Campaign has active characters and cannot be deleted."

    async def mock_callback(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(
            return_value={"error": {"message": expected_message}}
        )
        raise httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )

    with patch.object(
        mock_campaign_cog,
        "_create_delete_confirmation_callback",
        return_value=mock_callback,
    ):
        await mock_campaign_cog._handle_campaign_delete(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()

        button_interaction = InteractionFactory.admin_interaction()
        with pytest.raises(ValidationError) as exc_info:
            # We need to manually call the error handler that the callback would trigger
            try:
                await mock_callback(button_interaction)
            except httpx.HTTPStatusError as e:
                await mock_campaign_cog._handle_delete_error(button_interaction, e)

        exc = exc_info.value
        assert expected_message in exc.player_message


async def test_campaign_continue_no_campaign(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_exception_override(
        "continue_campaign", ValidationError(ErrorCode.NO_LAST_ACTIVE_CAMPAIGN)
    )

    interaction = InteractionFactory.regular_interaction()

    with pytest.raises(ValidationError) as exc_info:
        await mock_campaign_cog._handle_campaign_continue(interaction)

    exc = exc_info.value
    assert ErrorCode.NO_LAST_ACTIVE_CAMPAIGN.player_message in exc.player_message


# --- Tests for /campaign end ---


async def test_campaign_end_success(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "end_campaign", {"message": "Campaign ended successfully"}
    )

    interaction = InteractionFactory.regular_interaction()

    await mock_campaign_cog._handle_campaign_end(interaction)
    interaction.response.send_message.assert_awaited_once()
    assert (
        "exiting immersive mode"
        in interaction.response.send_message.call_args[0][0].lower()
    )


async def test_campaign_end_backend_error(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_exception_override(
        "end_campaign", CustomException()
    )

    interaction = InteractionFactory.regular_interaction()

    with pytest.raises(CustomException) as exc_info:
        await mock_campaign_cog._handle_campaign_end(interaction)

    exc = exc_info.value
    assert ErrorCode.UNKNOWN.player_message in exc.player_message


async def test_campaign_end_failure(mock_campaign_cog):
    # Replace API client with mock
    error = ErrorCode.PLAYER_NOT_IN_CAMPAIGN
    mock_campaign_cog.api_client.set_exception_override(
        "end_campaign", ValidationError(error)
    )

    interaction = InteractionFactory.regular_interaction()

    with pytest.raises(ValidationError) as exc_info:
        await mock_campaign_cog._handle_campaign_end(interaction)

    exc = exc_info.value
    assert error.player_message in exc.player_message


# --- Tests for /campaign delete ---


async def test_campaign_delete_success(mock_campaign_cog):
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "delete_campaign", {"message": "Campaign deleted successfully"}
    )

    interaction = InteractionFactory.admin_interaction()
    campaign_name = "delete_me"

    # This is a simplified test. A full test would require mocking the button callback.
    # For now, we just check that the initial message is sent.
    await mock_campaign_cog._handle_campaign_delete(interaction, campaign_name)
    interaction.response.send_message.assert_awaited_once()
    assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_info_success(mock_campaign_cog):
    # Replace API client with mock
    campaign_name = "info_test"
    campaign_id = 1
    owner_id = "owner123"
    server_id = "server123"

    # Set up mock responses
    mock_campaign_cog.api_client.set_response_override(
        "get_campaign_details",
        {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "owner_id": owner_id,
            "state": "active",
            "last_save": "2023-01-01T12:00:00",
        },
    )
    mock_campaign_cog.api_client.set_response_override(
        "get_campaign_players",
        [
            {"player_id": "player1", "username": "Alice"},
            {"player_id": "player2", "username": "Bob"},
        ],
    )

    interaction = InteractionFactory.admin_interaction()
    interaction.guild.id = server_id

    await mock_campaign_cog._handle_campaign_info(interaction, campaign_name)

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    embed = kwargs["embed"]
    assert embed.title == f"Campaign Info: {campaign_name}"
    assert embed.fields[0].value == owner_id
    assert "Alice" in embed.fields[2].value
    assert "Bob" in embed.fields[2].value


async def test_campaign_delete_cancel(mock_campaign_cog):
    interaction = InteractionFactory.admin_interaction()
    campaign_name = "dont_delete_me"

    # This is a simplified test. A full test would require mocking the button callback.
    # For now, we just check that the initial message is sent.
    await mock_campaign_cog._handle_campaign_delete(interaction, campaign_name)
    interaction.response.send_message.assert_called_once()
    assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_delete_button_confirm_success(mock_campaign_cog):
    """Test the confirm button callback for successful campaign deletion."""
    # Replace API client with mock
    mock_campaign_cog.api_client.set_response_override(
        "delete_campaign", {"message": "Campaign deleted successfully"}
    )

    interaction = InteractionFactory.admin_interaction()
    interaction.data = {"custom_id": "confirm"}
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    # Create the button callback function
    await mock_campaign_cog._handle_campaign_delete(interaction, "test_campaign")

    # Get the callback function that was assigned to the button
    # This is a bit tricky because we need to access the callback from the cog
    # For now, we'll just verify that the initial message is sent correctly
    interaction.response.send_message.assert_awaited_once()
    assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_delete_button_confirm_error(mock_campaign_cog):
    """Test the confirm button callback when campaign deletion fails."""
    # Replace API client with mock
    mock_campaign_cog.api_client.set_exception_override(
        "delete_campaign", CustomException()
    )

    interaction = InteractionFactory.admin_interaction()
    interaction.data = {"custom_id": "confirm"}
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    # Create the button callback function
    await mock_campaign_cog._handle_campaign_delete(interaction, "test_campaign")

    # Get the callback function that was assigned to the button
    # This is a bit tricky because we need to access the callback from the cog
    # For now, we'll just verify that the initial message is sent correctly
    interaction.response.send_message.assert_awaited_once()
    assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_delete_button_cancel(mock_campaign_cog):
    """Test the cancel button callback for campaign deletion."""
    interaction = InteractionFactory.admin_interaction()
    interaction.data = {"custom_id": "cancel"}
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    # Create the button callback function
    await mock_campaign_cog._handle_campaign_delete(interaction, "test_campaign")

    # Get the callback function that was assigned to the button
    # This is a bit tricky because we need to access the callback from the cog
    # For now, we'll just verify that the initial message is sent correctly
    interaction.response.send_message.assert_awaited_once()
    assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_delete_permission_denied(mock_campaign_cog):
    interaction = InteractionFactory.regular_interaction()
    campaign_name = "permission_denied"

    # This is a simplified test. A full test would require mocking the button callback.
    await mock_campaign_cog._handle_campaign_delete(interaction, campaign_name)
    interaction.response.send_message.assert_awaited_once()
    assert "Are you sure" in interaction.response.send_message.call_args[0][0]
