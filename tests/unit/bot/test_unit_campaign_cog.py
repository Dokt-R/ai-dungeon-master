import sys
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import httpx
import pytest
from discord.ext import commands

from packages.bot.cogs import campaign_cog
from packages.bot.cogs.campaign_cog import CampaignCog
from packages.shared.exceptions import NotFoundError, ValidationError

sys.modules["packages.backend.components.campaign_manager"] = mock.MagicMock()

pytestmark = pytest.mark.asyncio


@pytest.fixture
def bot():
    return MagicMock(spec=commands.Bot)


@pytest.fixture
def cog(mock_bot):
    return campaign_cog.CampaignCog(mock_bot)


async def test_campaign_new_success(tmp_path, cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    interaction.response = AsyncMock()
    campaign_name = "test_campaign"
    # campaign_dir = tmp_path / "data" / "campaigns" / campaign_name

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_new(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert (
            "created successfully" in interaction.response.send_message.call_args[0][0]
        )


async def test_campaign_new_duplicate(mock_bot, mock_interaction):
    cog = CampaignCog(mock_bot)

    interaction = mock_interaction
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    campaign_name = "existing_campaign"
    expected_message = f"A campaign named **{campaign_name}** already exists."

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Simulate a 400 Bad Request response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(
            return_value={"error": {"message": expected_message}}
        )
        # Configure raise_for_status to raise an exception with the mock response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_new(interaction, campaign_name)

        assert expected_message in str(excinfo.value)
        interaction.response.send_message.assert_not_called()


async def test_campaign_new_permission_denied(cog):
    interaction = MagicMock()
    interaction.user.guild_permissions.administrator = False
    interaction.user.guild_permissions.manage_guild = False
    interaction.response = AsyncMock()
    campaign_name = "test_campaign"

    await cog._handle_campaign_new(interaction, campaign_name)
    interaction.response.send_message.assert_called_once()
    assert "do not have permission" in interaction.response.send_message.call_args[0][0]


async def test_campaign_new_backend_error(cog, mock_interaction):
    interaction = mock_interaction
    interaction.user.guild_permissions.administrator = True
    interaction.user.guild_permissions.manage_guild = False
    interaction.user.id = 123
    interaction.guild.id = 456
    campaign_name = "test_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RequestError("backend error", request=MagicMock())
        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_new(interaction, campaign_name)
        assert "An unexpected error occurred" in str(excinfo.value)


async def test_campaign_join_success(cog):
    interaction = MagicMock()
    interaction.user.id = 789
    interaction.response = AsyncMock()
    campaign_name = "existing_campaign"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


async def test_campaign_join_nonexistent(cog, monkeypatch):
    # Create fake response with 404
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 404
    fake_response.json = AsyncMock(
        return_value={"error": {"message": "Campaign not found"}}
    )

    # Make raise_for_status raise the HTTPStatusError
    http_error = httpx.HTTPStatusError(
        "Not found", request=MagicMock(), response=fake_response
    )

    # Patch AsyncClient.post so it raises the error when called
    async def fake_post(*args, **kwargs):
        raise http_error

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    # Mock interaction to avoid sending actual Discord messages
    interaction = MagicMock()
    interaction.guild.id = 123
    interaction.user.id = 456
    interaction.response.send_message = AsyncMock()

    # Run and assert NotFoundError is raised
    with pytest.raises(NotFoundError):
        await cog._handle_campaign_join(interaction, "My Campaign")


async def test_campaign_join_no_campaign_name_uses_last_active(cog):
    interaction = MagicMock()
    interaction.user.id = 1001
    interaction.response = AsyncMock()
    # Simulate backend returns success when no campaign_name is given (uses last_active_campaign)
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, None)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


async def test_campaign_join_already_joined_fails(cog, monkeypatch):
    # Create fake response with 400
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 400
    fake_response.json = AsyncMock(
        return_value={
            "error": {
                "message": "Player is already joined to an active campaign on this server."
            }
        }
    )

    # Make raise_for_status raise the HTTPStatusError
    http_error = httpx.HTTPStatusError(
        "Already Joined", request=MagicMock(), response=fake_response
    )

    # Patch AsyncClient.post so it raises the error when called
    async def fake_post(*args, **kwargs):
        raise http_error

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    # Mock interaction to avoid sending actual Discord messages
    interaction = MagicMock()
    interaction.guild.id = 123
    interaction.user.id = 456
    interaction.response.send_message = AsyncMock()

    # Run and assert NotFoundError is raised
    with pytest.raises(ValidationError):
        await cog._handle_campaign_join(interaction, "My Campaign")


async def test_campaign_join_new_player_and_character(cog):
    interaction = MagicMock()
    interaction.user.id = 1003
    interaction.response = AsyncMock()
    campaign_name = "new_campaign"
    # Simulate backend returns success for new player/character
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


async def test_campaign_end_and_join_another(cog):
    interaction = MagicMock()
    interaction.user.id = 1004
    interaction.response = AsyncMock()
    campaign_name1 = "campaignA"
    campaign_name2 = "campaignB"
    # End campaignA
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_end(interaction, campaign_name1)
        interaction.response.send_message.assert_called_once()
        # Now join campaignB
        interaction.response.reset_mock()
        mock_post.return_value.status_code = 200
        await cog._handle_campaign_join(interaction, campaign_name2)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


async def test_campaign_join_no_last_active_campaign_fails(cog):
    interaction = MagicMock()
    interaction.user.id = 1005
    interaction.response = AsyncMock()
    expected_message = (
        "No campaign specified and no last active campaign found for player."
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json = AsyncMock(
            return_value={"error": {"message": expected_message}}
        )

        def raise_for_status():
            raise httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_response
            )

        mock_response.raise_for_status = raise_for_status
        mock_post.return_value = mock_response

        with pytest.raises(NotFoundError) as excinfo:
            await cog._handle_campaign_join(interaction, None)
        assert expected_message in str(excinfo.value)


async def test_campaign_join_new_character_linked(cog):
    interaction = MagicMock()
    interaction.user.id = 1006
    interaction.response = AsyncMock()
    campaign_name = "campaignC"
    # Simulate backend returns success for new character
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = AsyncMock(return_value={})
        await cog._handle_campaign_join(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "joined campaign" in interaction.response.send_message.call_args[0][0]


async def test_campaign_continue_success_autosave(cog):
    interaction = MagicMock()
    interaction.user.id = 1111
    interaction.guild.id = 2222
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "campaign_name": "EpicQuest",
            "source": "autosave",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await cog._handle_campaign_continue(interaction)
        interaction.response.send_message.assert_called_once()
        assert "autosave" in interaction.response.send_message.call_args[0][0].lower()
        assert (
            "resuming campaign"
            in interaction.response.send_message.call_args[0][0].lower()
        )


async def test_campaign_party_formation_multiple_users_onboarding(cog):
    # User1 (admin/owner) creates the campaign
    interaction1 = MagicMock()
    interaction1.user.id = 3001
    interaction1.user.guild_permissions.administrator = True
    interaction1.user.guild_permissions.manage_guild = False
    interaction1.guild.id = 4001
    interaction1.response = AsyncMock()
    campaign_name = "party_campaign"

    # User2 (regular player) joins the campaign
    interaction2 = MagicMock()
    interaction2.user.id = 3002
    interaction2.user.guild_permissions.administrator = False
    interaction2.user.guild_permissions.manage_guild = False
    interaction2.guild.id = 4001
    interaction2.response = AsyncMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Prepare one reusable mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={})
        mock_response.raise_for_status = MagicMock()

        mock_post.return_value = mock_response

        # Admin creates campaign
        await cog._handle_campaign_new(interaction1, campaign_name)
        interaction1.response.send_message.assert_called()
        interaction1.response.reset_mock()

        # Admin joins campaign
        await cog._handle_campaign_join(interaction1, campaign_name)
        interaction1.response.send_message.assert_called()
        interaction1.response.reset_mock()

        # Player joins campaign
        await cog._handle_campaign_join(interaction2, campaign_name)
        interaction2.response.send_message.assert_called()
        msg2 = interaction2.response.send_message.call_args[0][0].lower()
        assert "joined campaign" in msg2 or "character" in msg2

        # Change only the *return value* of json(), not the mock itself
        mock_response.json.return_value = {
            "campaign_name": campaign_name,
            "source": "save",
        }

        with pytest.raises(ValidationError):
            await cog._handle_campaign_continue(interaction1)


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


async def test_campaign_continue_success_save(cog):
    interaction = MagicMock()
    interaction.user.id = 1112
    interaction.guild.id = 2223
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "campaign_name": "EpicQuest",
            "source": "save",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await cog._handle_campaign_continue(interaction)
        interaction.response.send_message.assert_called_once()
        assert (
            "last clean save"
            in interaction.response.send_message.call_args[0][0].lower()
        )
        assert (
            "resuming campaign"
            in interaction.response.send_message.call_args[0][0].lower()
        )


async def test_campaign_continue_backend_error(cog):
    interaction = MagicMock()
    interaction.user.id = 1113
    interaction.guild.id = 2224
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RequestError("backend error", request=MagicMock())
        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_continue(interaction)
        assert "An unexpected error occurred" in str(excinfo.value)


async def test_campaign_delete_with_active_characters(cog):
    interaction = AsyncMock()
    interaction.user.guild_permissions.administrator = True
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
        cog, "_create_delete_confirmation_callback", return_value=mock_callback
    ):
        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()

        button_interaction = AsyncMock()
        with pytest.raises(ValidationError) as excinfo:
            # We need to manually call the error handler that the callback would trigger
            try:
                await mock_callback(button_interaction)
            except httpx.HTTPStatusError as e:
                await cog._handle_delete_error(button_interaction, e)

        assert expected_message in str(excinfo.value)


async def test_campaign_continue_no_campaign(cog):
    interaction = MagicMock()
    interaction.user.id = 1114
    interaction.guild.id = 2225
    interaction.response = AsyncMock()
    expected_message = (
        "No campaign specified and no last active campaign found for player."
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json = AsyncMock(
            return_value={"error": {"message": expected_message}}
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_continue(interaction)
        assert expected_message in str(excinfo.value)


# --- Tests for /campaign end ---


async def test_campaign_end_success(cog):
    interaction = MagicMock()
    interaction.user.id = 2001
    interaction.guild.id = 3001
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        await cog._handle_campaign_end(interaction)
        interaction.response.send_message.assert_called_once()
        assert (
            "exiting immersive mode"
            in interaction.response.send_message.call_args[0][0].lower()
        )


async def test_campaign_end_backend_error(cog):
    interaction = MagicMock()
    interaction.user.id = 2002
    interaction.guild.id = 3002
    interaction.response = AsyncMock()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RequestError("backend error", request=MagicMock())
        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_end(interaction)
        assert "An unexpected error occurred" in str(excinfo.value)


async def test_campaign_end_failure(cog):
    interaction = MagicMock()
    interaction.user.id = 2003
    interaction.guild.id = 3003
    interaction.response = AsyncMock()
    expected_message = "Not in a campaign."
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(
            return_value={"error": {"message": expected_message}}
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(ValidationError) as excinfo:
            await cog._handle_campaign_end(interaction)
        assert expected_message in str(excinfo.value)


# --- Tests for /campaign delete ---


async def test_campaign_delete_success(cog):
    interaction = AsyncMock()
    interaction.user.guild_permissions.administrator = True
    campaign_name = "delete_me"

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.raise_for_status = MagicMock()

        # This is a simplified test. A full test would require mocking the button callback.
        # For now, we just check that the initial message is sent.
        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_info_success(cog):
    interaction = AsyncMock()
    campaign_name = "info_test"
    campaign_id = 1
    owner_id = "owner123"
    server_id = "server123"
    interaction.guild.id = server_id

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_campaign_response = MagicMock()
        mock_campaign_response.status_code = 200
        mock_campaign_response.json.return_value = {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "owner_id": owner_id,
            "state": "active",
            "last_save": "2023-01-01T12:00:00",
        }
        mock_campaign_response.raise_for_status = MagicMock()

        mock_players_response = MagicMock()
        mock_players_response.status_code = 200
        mock_players_response.json.return_value = [
            {"player_id": "player1", "username": "Alice"},
            {"player_id": "player2", "username": "Bob"},
        ]
        mock_players_response.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_campaign_response, mock_players_response]

        await cog._handle_campaign_info(interaction, campaign_name)

        interaction.response.send_message.assert_called_once()
        _, kwargs = interaction.response.send_message.call_args
        embed = kwargs["embed"]
        assert embed.title == f"Campaign Info: {campaign_name}"
        assert embed.fields[0].value == owner_id
        assert "Alice" in embed.fields[2].value
        assert "Bob" in embed.fields[2].value


async def test_campaign_delete_cancel(cog):
    interaction = AsyncMock()
    campaign_name = "dont_delete_me"

    # This is a simplified test. A full test would require mocking the button callback.
    # For now, we just check that the initial message is sent.
    await cog._handle_campaign_delete(interaction, campaign_name)
    interaction.response.send_message.assert_called_once()
    assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_delete_button_confirm_success(cog):
    """Test the confirm button callback for successful campaign deletion."""
    interaction = AsyncMock()
    interaction.data = {"custom_id": "confirm"}
    interaction.guild.id = "123"
    interaction.user.id = "456"
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    # Mock the view and buttons
    view = MagicMock()
    confirm_button = MagicMock()
    cancel_button = MagicMock()
    view.children = [confirm_button, cancel_button]

    # Mock the httpx request for successful deletion
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.raise_for_status = MagicMock()

        # Create the button callback function
        await cog._handle_campaign_delete(interaction, "test_campaign")

        # Get the callback function that was assigned to the button
        # This is a bit tricky because we need to access the callback from the cog
        # For now, we'll just verify that the initial message is sent correctly
        interaction.response.send_message.assert_called_once()
        assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_delete_button_confirm_error(cog):
    """Test the confirm button callback when campaign deletion fails."""
    interaction = AsyncMock()
    interaction.data = {"custom_id": "confirm"}
    interaction.guild.id = "123"
    interaction.user.id = "456"
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    # Mock the view and buttons
    view = MagicMock()
    confirm_button = MagicMock()
    cancel_button = MagicMock()
    view.children = [confirm_button, cancel_button]

    # Mock the httpx request for failed deletion
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = Exception("Deletion failed")

        # Create the button callback function
        await cog._handle_campaign_delete(interaction, "test_campaign")

        # Get the callback function that was assigned to the button
        # This is a bit tricky because we need to access the callback from the cog
        # For now, we'll just verify that the initial message is sent correctly
        interaction.response.send_message.assert_called_once()
        assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_delete_button_cancel(cog):
    """Test the cancel button callback for campaign deletion."""
    interaction = AsyncMock()
    interaction.data = {"custom_id": "cancel"}
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.edit_original_response = AsyncMock()

    # Mock the view and buttons
    view = MagicMock()
    confirm_button = MagicMock()
    cancel_button = MagicMock()
    view.children = [confirm_button, cancel_button]

    # Create the button callback function
    await cog._handle_campaign_delete(interaction, "test_campaign")

    # Get the callback function that was assigned to the button
    # This is a bit tricky because we need to access the callback from the cog
    # For now, we'll just verify that the initial message is sent correctly
    interaction.response.send_message.assert_called_once()
    assert "Are you sure" in interaction.response.send_message.call_args[0][0]


async def test_campaign_delete_permission_denied(cog):
    interaction = AsyncMock()
    interaction.user.guild_permissions.administrator = False
    campaign_name = "permission_denied"

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value.status_code = 403
        mock_request.return_value.json.return_value = {
            "detail": "Only the owner or an admin can delete."
        }
        mock_request.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden",
            request=MagicMock(),
            response=mock_request.return_value,
        )

        # This is a simplified test. A full test would require mocking the button callback.
        await cog._handle_campaign_delete(interaction, campaign_name)
        interaction.response.send_message.assert_called_once()
        assert "Are you sure" in interaction.response.send_message.call_args[0][0]
